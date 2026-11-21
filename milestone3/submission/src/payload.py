import json


class Payload:
    def __init__(self, data: str, route: str):
        self.data = data

        self.route = route

    def advance(self):
        hop, _, remaining_route = self.route.partition("|")
        self.route = remaining_route
        return hop

    def serialize(self):
        return json.dumps({"data": self.data, "route": self.route}).encode("utf-8")

    @staticmethod
    def deserialize(body):
        message = json.loads(body)
        return Payload(message["data"], message["route"])