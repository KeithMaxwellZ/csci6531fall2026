import json
import hmac
import sqlite3
import secrets
import smtplib
import threading
import time
from contextlib import closing
from email.message import EmailMessage
from pathlib import Path

from crypto_utils import generate_session_token, hash_password, verify_password
from payload import Payload
from server import BaseServer


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_CONFIG_PATH = Path(__file__).with_name("info.json")
DATABASE_PATH = Path(__file__).with_name("server.sqlite3")
TWO_FACTOR_CODE_TTL_SECONDS = 300
TWO_FACTOR_MAX_ATTEMPTS = 5
SESSION_TTL_SECONDS = 24 * 60 * 60
LOGIN_MAX_ATTEMPTS = 3
LOGIN_LOCKOUT_SECONDS = 30


class FullServer(BaseServer):
	def __init__(self, address_book=None, host="127.0.0.1", port=9961, database_path=DATABASE_PATH):
		super().__init__(address_book, host, port)
		self.database_path = Path(database_path)
		self.database_lock = threading.Lock()
		self.users = {
			"alice": {"password": hash_password("alice"), "email": "alice@example.com", "is_admin": True},
			"bob": {"password": hash_password("bob"), "email": "bob@example.com", "is_admin": False}
        }
		self.sessions = {}
		self.contacts = {}
		self.login_failures = {}
		self._initialize_database()
		self._load_users()
		self._load_contacts()

	def on_receive(self, payload):
		try:
			request = json.loads(payload.data)
		except (TypeError, json.JSONDecodeError):
			return self._response(400, "Invalid request")

		handlers = {
			"register": self._register,
			"login": self._login,
			"2fa": self._verify_2fa,
			"logout": self._logout,
			"initiate_session": self._initiate_session,
			"message": self._send_message,
			"fetch_contacts": self._fetch_contacts,
			"publish_keys": self._publish_keys,
			"fetch_keys": self._fetch_keys,
		}
		request_type = request.get("type")
		handler = handlers.get(request_type)
		if handler is None:
			return self._response(400, "Unknown request type")
		if request_type in {"logout", "initiate_session", "message", "fetch_contacts", "publish_keys", "fetch_keys"}:
			if self._authenticate(request) is None:
				return self._response(401, "Authentication required")

		try:
			return handler(request)
		except (KeyError, TypeError):
			return self._response(400, "Missing request field")

	def _authenticate(self, request):
		username = request.get("username")
		token = request.get("session_token")
		session = self.sessions.get(username)
		if not isinstance(username, str) or not isinstance(token, str) or session is None:
			return None
		stored_token = session.get("session_token")
		if not isinstance(stored_token, str) or not session.get("authenticated") or not hmac.compare_digest(token, stored_token):
			return None
		if time.time() >= session.get("session_expires_at", 0):
			session.clear()
			return None
		return username

	def _response(self, status_code, message=None, **values):
		response = {"status_code": status_code}
		if message is not None:
			response["message"] = message
		response.update(values)
		return Payload(json.dumps(response), "")

	def _initialize_database(self):
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			connection.execute(
				"""
				CREATE TABLE IF NOT EXISTS users (
					username TEXT PRIMARY KEY,
					password TEXT NOT NULL,
					email TEXT NOT NULL,
					is_admin INTEGER NOT NULL DEFAULT 0,
					created_at REAL NOT NULL,
					exchange_public_key TEXT NOT NULL DEFAULT '',
					identity_public_key TEXT NOT NULL DEFAULT ''
				)
				"""
			)
			columns = {row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
			if "exchange_public_key" not in columns:
				connection.execute("ALTER TABLE users ADD COLUMN exchange_public_key TEXT NOT NULL DEFAULT ''")
			if "identity_public_key" not in columns:
				connection.execute("ALTER TABLE users ADD COLUMN identity_public_key TEXT NOT NULL DEFAULT ''")
			connection.commit()
			connection.execute(
				"""
				CREATE TABLE IF NOT EXISTS audit_logs (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					timestamp REAL NOT NULL,
					username TEXT,
					event TEXT NOT NULL,
					success INTEGER NOT NULL,
					details TEXT NOT NULL DEFAULT ''
				)
				"""
			)
			connection.execute(
				"""
				CREATE TABLE IF NOT EXISTS contacts (
					username TEXT NOT NULL,
					contact TEXT NOT NULL,
					created_at REAL NOT NULL,
					PRIMARY KEY (username, contact)
				)
				"""
			)

	def _load_users(self):
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			rows = connection.execute(
				"SELECT username, password, email, is_admin, exchange_public_key, identity_public_key FROM users"
			).fetchall()
			if not rows:
				for username, user in self.users.items():
					connection.execute(
						"INSERT INTO users (username, password, email, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
						(username, user["password"], user["email"], int(user.get("is_admin", False)), time.time()),
					)
				connection.commit()
				return
			self.users = {}
			for username, password, email, is_admin, exchange_public_key, identity_public_key in rows:
				self.users[username] = {
					"password": password,
					"email": email,
					"is_admin": bool(is_admin),
					"exchange_public_key": exchange_public_key,
					"identity_public_key": identity_public_key,
				}
			connection.commit()

	def _save_user(self, username, user):
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			connection.execute(
				"INSERT INTO users (username, password, email, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
				(username, user["password"], user["email"], int(user.get("is_admin", False)), time.time()),
			)
			connection.commit()

	def _load_contacts(self):
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			for username, contact in connection.execute("SELECT username, contact FROM contacts"):
				self.contacts.setdefault(username, set()).add(contact)

	def _sync_contact_directory(self, username):
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			for contact in self.users:
				if contact == username:
					continue
				self.contacts.setdefault(username, set()).add(contact)
				self.contacts.setdefault(contact, set()).add(username)
				connection.executemany(
					"INSERT OR IGNORE INTO contacts (username, contact, created_at) VALUES (?, ?, ?)",
					[(username, contact, time.time()), (contact, username, time.time())],
				)
			connection.commit()

	def _log_event(self, username, event, success, details=""):
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			connection.execute(
				"INSERT INTO audit_logs (timestamp, username, event, success, details) VALUES (?, ?, ?, ?, ?)",
				(time.time(), username, event, int(success), details),
			)
			connection.commit()

	def _register(self, request):
		username = request["username"]
		if username in self.users:
			self._log_event(username, "register", False, "username already exists")
			return self._response(409, "Username already exists")
		user = {
			"password": hash_password(request["password"]),
			"email": request.get("email", ""),
		}
		self._save_user(username, user)
		self.users[username] = user
		self.contacts.setdefault(username, set())
		self._log_event(username, "register", True)
		return self._response(200, "Registered")

	def _login(self, request):
		username = request["username"]
		now = time.monotonic()
		failure = self.login_failures.get(username)
		if failure and now < failure["locked_until"]:
			return self._response(429, "Too many login attempts")
		user = self.users.get(username)
		if user is None or not verify_password(request["password"], user["password"]):
			failure = self.login_failures.setdefault(username, {"attempts": 0, "locked_until": 0})
			failure["attempts"] += 1
			if failure["attempts"] >= LOGIN_MAX_ATTEMPTS:
				failure["locked_until"] = now + LOGIN_LOCKOUT_SECONDS
			self._log_event(username, "login", False, "invalid credentials")
			return self._response(401, "Invalid credentials")
		self.login_failures.pop(username, None)
		self._sync_contact_directory(username)

		code = f"{secrets.randbelow(1000000):06d}"
		try:
			self._send_2fa_code(user["email"], code)
		except (OSError, smtplib.SMTPException) as error:
			return self._response(503, f"Unable to send verification code: {error}")

		if request.get("router") and request.get("client"):
			self.register_client(username, request["router"], request["client"])
		self.sessions[username] = {
			"authenticated": False,
			"two_factor_code": code,
			"two_factor_expires_at": time.time() + TWO_FACTOR_CODE_TTL_SECONDS,
			"two_factor_attempts": 0,
		}
		self._log_event(username, "login", True, "password accepted; 2FA pending")
		return self._response(200, "Login accepted", is_admin=user.get("is_admin", False))

	def _send_2fa_code(self, recipient, code):
		try:
			with SMTP_CONFIG_PATH.open(encoding="utf-8") as config_file:
				config = json.load(config_file)
			sender = config["gm"]
			password = config["pw"]
		except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
			raise OSError(f"Unable to read SMTP credentials from {SMTP_CONFIG_PATH.name}") from error
		if not isinstance(sender, str) or not sender or not isinstance(password, str) or not password:
			raise OSError(f"SMTP credentials are missing from {SMTP_CONFIG_PATH.name}")

		message = EmailMessage()
		message["From"] = sender
		message["To"] = recipient
		message["Subject"] = "Encrypted Messenger verification code"
		message.set_content(
			f"Your Encrypted Messenger verification code is {code}. "
			f"It expires in {TWO_FACTOR_CODE_TTL_SECONDS // 60} minutes."
		)

		with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
			smtp.starttls()
			smtp.login(sender, password)
			smtp.send_message(message)

	def _verify_2fa(self, request):
		username = request["username"]
		session = self.sessions.get(username)
		if session is None or session.get("authenticated"):
			self._log_event(username, "2fa", False, "no pending session")
			return self._response(401, "Verification failed")
		if time.time() > session["two_factor_expires_at"]:
			self._log_event(username, "2fa", False, "code expired")
			return self._response(401, "Verification code expired")
		if session["two_factor_attempts"] >= TWO_FACTOR_MAX_ATTEMPTS:
			self._log_event(username, "2fa", False, "too many attempts")
			return self._response(401, "Too many verification attempts")
		session["two_factor_attempts"] += 1
		# if request['code'] == '666': # DEBUG BYPASS
		# 	session["authenticated"] = True
		# 	session.pop("two_factor_code", None)
		# 	session["session_token"] = generate_session_token()
		# 	session["session_expires_at"] = time.time() + SESSION_TTL_SECONDS
		# 	session["reauth_token"] = generate_session_token()
		# 	self._log_event(username, "2fa", True, "bypass code used")
		# 	return self._response(
		# 		200,
		# 		"Verified",
		# 		session_token=session["session_token"],
		# 		expires_at=session["session_expires_at"],
		# 		reauth_token=session["reauth_token"],
		# 	)
		if not hmac.compare_digest(request["code"], session["two_factor_code"]):
			self._log_event(username, "2fa", False, "invalid code")
			return self._response(401, "Verification failed")
		session["authenticated"] = True
		session.pop("two_factor_code", None)
		session["session_token"] = generate_session_token()
		session["session_expires_at"] = time.time() + SESSION_TTL_SECONDS
		session["reauth_token"] = generate_session_token()
		self._log_event(username, "2fa", True)
		return self._response(
			200,
			"Verified",
			session_token=session["session_token"],
			expires_at=session["session_expires_at"],
			reauth_token=session["reauth_token"],
		)

	def _logout(self, request):
		username = self._authenticate(request)
		if username is None:
			return self._response(401, "Authentication required")
		self.sessions.pop(username, None)
		self.address_book.pop(username, None)
		self._log_event(username, "logout", True)
		return self._response(200, "Logged out")

	def _initiate_session(self, request):
		username = request["username"]
		contact = request["contact"]
		if username not in self.users or contact not in self.users:
			return self._response(404, "Contact not found")
		if username == contact:
			return self._response(400, "Cannot initiate a session with yourself")
		self.contacts.setdefault(username, set()).add(contact)
		self.contacts.setdefault(contact, set()).add(username)
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			connection.executemany(
				"INSERT OR IGNORE INTO contacts (username, contact, created_at) VALUES (?, ?, ?)",
				[(username, contact, time.time()), (contact, username, time.time())],
			)
			connection.commit()
		return self._response(200, "Session initiated")

	def _send_message(self, request):
		sender = request["username"]
		target = request["target"]
		if target not in self.contacts.get(sender, set()):
			return self._response(403, "Contact session required")
		destination = self.address_book.get(target)
		if destination is None:
			return self._response(404, "Recipient not found")

		router, client = destination
		message = Payload(
			json.dumps({
				"sender": sender,
				"message": request["message"],
			}),
			client,
		)
		self._forward(router, message)
		return self._response(200, "Message sent")

	def _publish_keys(self, request):
		username = request["username"]
		if username not in self.users:
			return self._response(404, "User not found")
		with self.database_lock, closing(sqlite3.connect(self.database_path)) as connection:
			connection.execute(
				"UPDATE users SET exchange_public_key = ?, identity_public_key = ? WHERE username = ?",
				(request["exchange_public_key"], request["identity_public_key"], username),
			)
			connection.commit()
		self.users[username]["exchange_public_key"] = request["exchange_public_key"]
		self.users[username]["identity_public_key"] = request["identity_public_key"]
		return self._response(200, "Public keys published")

	def _fetch_keys(self, request):
		username = request["username"]
		contact = self.users.get(username)
		if contact is None:
			return self._response(404, "User not found")
		target = self.users.get(request["contact"])
		if target is None:
			return self._response(404, "Contact not found")
		if request["contact"] not in self.contacts.get(username, set()):
			return self._response(403, "Contact session required")
		if not target.get("exchange_public_key") or not target.get("identity_public_key"):
			return self._response(409, "Contact keys unavailable")
		return self._response(
			200,
			exchange_public_key=target["exchange_public_key"],
			identity_public_key=target["identity_public_key"],
		)

	def _fetch_contacts(self, request):
		username = request["username"]
		return self._response(
			200,
			contacts=sorted(self.contacts.get(username, set())),
		)
    