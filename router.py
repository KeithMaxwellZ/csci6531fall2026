from node import Node


class BaseRouter(Node):
    def __init__(self, server_addr, host="127.0.0.1", port=0):
        super().__init__("/", host, port)
        self.server_addr = server_addr

    async def on_request(self, path, payload):
        payload = self.inspect_payload(payload)
        return await self._forward_async(payload.route, payload)

    def inspect_payload(self, payload):
        print(f"{self.__class__.__name__} inspecting payload: {payload.data} with route: {payload.route}")
        return payload