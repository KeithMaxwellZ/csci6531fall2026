from node import Node


class BaseRouter(Node):
    def __init__(self, host="127.0.0.1", port=0):
        super().__init__("/payload", host, port)

    def on_receive(self, payload):
        destination = payload.advance()
        payload = self.inspect_payload(payload)
        return self._forward(destination, payload)

    def inspect_payload(self, payload):
        print(f"{self.__class__.__name__} inspecting payload: {payload.data} with route: {payload.route}")
        return payload