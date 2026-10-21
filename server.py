from node import Node
from payload import Payload


class BaseServer(Node):
    def __init__(self, host="127.0.0.1", port=0):
        super().__init__("/payload", host, port)
        self.received_payloads = []

    def on_receive(self, payload):
        if not payload.route:
            self.received_payloads.append(payload)
            return payload

        new_payload = self.process_payload(payload)
        destination = new_payload.advance()
        return self._forward(destination, new_payload)

    def process_payload(self, payload):
        return Payload(payload.data, payload.route)