class Payload:
    def __init__(self, data: str, route: str):
        self.data = data

        self.route = route

    def advance(self):
        hop, _, remaining_route = self.route.partition("|")
        self.route = remaining_route
        return hop