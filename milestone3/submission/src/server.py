from node import Node
from payload import Payload
import json


class BaseServer(Node):
    def __init__(self, address_book=None, host="127.0.0.1", port=9961):
        super().__init__("/payload", host, port)
        self.address_book = address_book or {}
        self.received_payloads = []

    def on_receive(self, payload):
        if not payload.route:
            self.received_payloads.append(payload)
            return payload

        new_payload = self.process_payload(payload)
        try:
            router, new_payload.route = self.resolve_destination(new_payload)
        except (KeyError, TypeError, json.JSONDecodeError):
            return Payload(
                json.dumps({
                    "status_code": 400,
                    "message": "Payload does not contain a valid target",
                }),
                "",
            )
        return self._forward(router, new_payload)

    def resolve_destination(self, payload):
        message = json.loads(payload.data)
        return self.address_book[message["target"]]

    def register_client(self, target, router, client):
        """
        This method is for debug use only, it's not expected to be used in production. 
        It allows you to register a client with the server's address book for testing purposes.
        """
        self.address_book[target] = (router, client)

    def process_payload(self, payload):
        return Payload(payload.data, payload.route)