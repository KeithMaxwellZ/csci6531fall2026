from node import Node


class BaseClient(Node):
    def __init__(self, router_addr, host="127.0.0.1", port=0):
        super().__init__("/receive", host, port)
        self.router_addr = router_addr
        self.received_payloads = []

    def send_payload(self, payload):
        return self._forward(self.router_addr, payload)

    @property
    def send_address(self):
        return f"http://{self.host}:{self._http_server.server_port}/send"

    def on_request(self, path, payload):
        if path == "/send":
            return self.send_payload(payload)
        return self.on_receive(payload)

    def on_receive(self, payload):
        self.received_payloads.append(payload)
        return payload