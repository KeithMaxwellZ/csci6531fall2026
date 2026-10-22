import json

from payload import Payload
from server import BaseServer


class FullServer(BaseServer):
	def __init__(self, address_book=None, host="127.0.0.1", port=9961):
		super().__init__(address_book, host, port)
		self.users = {
			"alice": {"password": "alice", "email": "alice@example.com"},
			"bob": {"password": "bob", "email": "bob@example.com"}
        }
		self.sessions = {}
		self.contacts = {}

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
			"password": request["password"],
			"email": request.get("email", ""),
		}
		self.contacts.setdefault(username, set())
		return self._response(200, "Registered")

	def _login(self, request):
		username = request["username"]
		user = self.users.get(username)
		if user is None or user["password"] != request["password"]:
			return self._response(401, "Invalid credentials")
		if request.get("router") and request.get("client"):
			self.register_client(username, request["router"], request["client"])
		self.sessions[username] = {"authenticated": False}
		return self._response(200, "Login accepted")

	def _verify_2fa(self, request):
		username = request["username"]
		session = self.sessions.get(username)
		if session is None or request["code"] != "666":
			return self._response(401, "Verification failed")
		session["authenticated"] = True
		return self._response(200, "Verified")

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
			contacts=sorted(contact for contact in self.users if contact != username),
		)
    