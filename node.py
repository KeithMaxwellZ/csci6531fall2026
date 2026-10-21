import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen

from payload import Payload


class NodeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        payload = Payload(body["data"], body["route"])
        print(f"{self.server.node.__class__.__name__} received: {payload.data} with route: {payload.route}")
        self.server.node.on_request(self.path, payload)
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return  # Suppress logging to avoid cluttering the output


class NodeHTTPServer(ThreadingHTTPServer):
    def __init__(self, address, node):
        self.node = node
        super().__init__(address, NodeHandler)


class Node:
    def __init__(self, path, host="127.0.0.1", port=0):
        self.path = path
        self.host = host
        self.port = port
        self._http_server = None
        self._thread = None

    @property
    def address(self):
        return f"http://{self.host}:{self._http_server.server_port}{self.path}"

    def start(self):
        self._http_server = NodeHTTPServer((self.host, self.port), self)
        self._thread = Thread(target=self._http_server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None
            self._thread = None

    def on_receive(self, payload):
        raise NotImplementedError

    def on_request(self, path, payload):
        return self.on_receive(payload)

    def _forward(self, destination, payload):
        body = json.dumps({"data": payload.data, "route": payload.route}).encode("utf-8")
        request = Request(destination, data=body, method="POST")
        urlopen(request).close()
        return payload
