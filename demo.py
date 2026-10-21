import json
from urllib.request import Request, urlopen

from client import BaseClient
from router import BaseRouter
from server import BaseServer


def send_demo_payload(client, data, route):
    body = json.dumps({"data": data, "route": route}).encode("utf-8")
    request = Request(client.send_address, data=body, method="POST")
    urlopen(request).close()


def main():
    router1 = BaseRouter().start()
    router2 = BaseRouter().start()
    server = BaseServer().start()
    bob = BaseClient(router2.address).start()
    alice = BaseClient(router1.address).start()

    nodes = {
        "Router 1": router1.address,
        "Router 2": router2.address,
        "Server": server.address,
        "Alice receive": alice.address,
        "Alice send": alice.send_address,
        "Bob receive": bob.address,
        "Bob send": bob.send_address,
    }

    try:
        for name, address in nodes.items():
            print(f"{name}: {address}")

        route = "|".join((server.address, router2.address, bob.address))
        send_demo_payload(alice, "demo ciphertext", route)
        print("Sent demo payload from Alice")
        print("Press Ctrl+C to stop")

        while True:
            input()
    except KeyboardInterrupt:
        print("Stopping nodes")
    finally:
        alice.stop()
        bob.stop()
        router1.stop()
        router2.stop()
        server.stop()


if __name__ == "__main__":
    main()
