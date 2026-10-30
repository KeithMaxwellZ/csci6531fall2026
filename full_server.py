import hmac
import json
import secrets
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from payload import Payload
from server import BaseServer


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
CONFIG_DIRECTORY = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
SMTP_CONFIG_PATH = CONFIG_DIRECTORY / "info.json"
TWO_FACTOR_CODE_TTL_SECONDS = 300
TWO_FACTOR_MAX_ATTEMPTS = 5
# Demo-only shortcut; remove before production.
DEBUG_TWO_FACTOR_CODE = "666"
PASSWORD_HASHER = PasswordHasher()


class FullServer(BaseServer):
	def __init__(self, address_book=None, host="127.0.0.1", port=9961):
		super().__init__(address_book, host, port)
		self.users = {
			"alice": {"password": "$argon2id$v=19$m=65536,t=3,p=4$PGxmWmyrdjetgDznq9hJDg$avfcrT6pwddVJ6MCF9m/rDhnQeB0iKPW68WGgjfgDLg", "email": "keithzhang021@gmail.com", "is_admin": False},
			"bob": {"password": "$argon2id$v=19$m=65536,t=3,p=4$knNoCkQllttfaDZEzec41A$/UKzvekV2eM0eC8+bSJfMgzje5iBemaEU+BYyBCI+KI", "email": "keithzhang021@gmail.com", "is_admin": False},
			"charlie": {"password": "$argon2id$v=19$m=65536,t=3,p=4$/QR0gETQQPFVbSTP01xC7Q$Qcpso47nFVJdeX2bY4KJJx5HWHSwYEWa7lfHHY8YhpE", "email": "keithzhang021@gmail.com", "is_admin": False}
        }
		self.sessions = {}
		self.contacts = {}

	def _hash_password(self, password):
		return PASSWORD_HASHER.hash(password)

	def _password_matches(self, password_hash, password):
		try:
			return PASSWORD_HASHER.verify(password_hash, password)
		except (VerificationError, TypeError, ValueError):
			return False

	def on_receive(self, payload):
		try:
			request = json.loads(payload.data)
		except (TypeError, json.JSONDecodeError):
			return self._response(400, "Invalid request")

		handlers = {
			"register": self._register,
			"login": self._login,
			"2fa": self._verify_2fa,
			"initiate_session": self._initiate_session,
			"logout": self._logout,
			"message": self._send_message,
			"fetch_contacts": self._fetch_contacts,
		}
		request_type = request.get("type")
		handler = handlers.get(request_type)
		if handler is None:
			return self._response(400, "Unknown request type")

		try:
			return handler(request)
		except (KeyError, TypeError):
			return self._response(400, "Missing request field")

	def _response(self, status_code, message=None, **values):
		response = {"status_code": status_code}
		if message is not None:
			response["message"] = message
		response.update(values)
		return Payload(json.dumps(response), "")

	def _register(self, request):
		username = request["username"]
		if username in self.users:
			return self._response(409, "Username already exists")
		self.users[username] = {
			"password": self._hash_password(request["password"]),
			"email": request.get("email", ""),
			"is_admin": False,
		}
		self.contacts.setdefault(username, set())
		return self._response(200, "Registered")

	def _login(self, request):
		username = request["username"]
		user = self.users.get(username)
		if user is None or not self._password_matches(user["password"], request["password"]):
			return self._response(401, "Invalid credentials")
		code = f"{secrets.randbelow(1000000):06d}"
		try:
			self._send_2fa_code(user["email"], code)
		except (OSError, smtplib.SMTPException):
			return self._response(503, "Unable to send verification code")
		if request.get("router") and request.get("client"):
			self.register_client(username, request["router"], request["client"])
		self.sessions[username] = {
			"authenticated": False,
			"two_factor_code": code,
			"two_factor_expires_at": time.time() + TWO_FACTOR_CODE_TTL_SECONDS,
			"two_factor_attempts": 0,
		}
		return self._response(200, "Login accepted", is_admin=user.get("is_admin", False))

	def _send_2fa_code(self, recipient, code):
		try:
			with SMTP_CONFIG_PATH.open(encoding="utf-8") as config_file:
				config = json.load(config_file)
			sender = config["gm"]
			password = config["pw"]
		except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
			raise OSError("Unable to read SMTP credentials") from error
		if not isinstance(sender, str) or not sender or not isinstance(password, str) or not password:
			raise OSError("SMTP credentials are missing")

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
			return self._response(401, "Verification failed")
		if time.time() > session["two_factor_expires_at"]:
			return self._response(401, "Verification code expired")
		if session["two_factor_attempts"] >= TWO_FACTOR_MAX_ATTEMPTS:
			return self._response(401, "Too many verification attempts")
		session["two_factor_attempts"] += 1
		code = request["code"]
		if (
			not isinstance(code, str)
			or (
				code != DEBUG_TWO_FACTOR_CODE
				and not hmac.compare_digest(code, session["two_factor_code"])
			)
		):
			return self._response(401, "Verification failed")
		session["authenticated"] = True
		self._notify_clients_user_online(username)
		return self._response(200, "Verified")

	def _logout(self, request):
		username = request["username"]
		self.sessions.pop(username, None)
		self.address_book.pop(username, None)
		self._notify_clients_user_presence(username, "user_offline")
		return self._response(200, "Logged out")

	def _notify_clients_user_online(self, username):
		self._notify_clients_user_presence(username, "user_online")

	def _notify_clients_user_presence(self, username, event_type):
		payload_data = json.dumps({"type": event_type, "username": username})
		for target, destination in list(self.address_book.items()):
			if target == username:
				continue
			router, client = destination
			try:
				self._forward(router, Payload(payload_data, client))
			except (OSError, ValueError):
				continue

	def _initiate_session(self, request):
		username = request["username"]
		contact = request["contact"]
		if username not in self.users or contact not in self.users:
			return self._response(404, "Contact not found")
		self.contacts.setdefault(username, set()).add(contact)
		self.contacts.setdefault(contact, set()).add(username)
		return self._response(200, "Session initiated")

	def _send_message(self, request):
		sender = request["username"]
		target = request["target"]
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

	def _fetch_contacts(self, request):
		username = request["username"]
		return self._response(
			200,
			contacts=sorted(
				contact
				for contact in self.users
				if contact != username and contact in self.address_book
			),
		)
    