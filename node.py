import asyncio
import inspect
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen

from payload import Payload


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = Payload.deserialize(self.rfile.read(length))
        logger.debug(
            "%s received: %s with route: %s",
            self.server.node.__class__.__name__,
            payload.data,
            payload.route,
        )
        response = self.server.node.on_request(self.path, payload)
        if inspect.isawaitable(response):
            response = asyncio.run(response)
        if not isinstance(response, Payload):
            response = payload
        body = response.serialize()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
        request = Request(destination, data=payload.serialize(), method="POST")
        with urlopen(request) as response:
            body = response.read()
        return Payload.deserialize(body) if body else payload

    async def _forward_async(self, destination, payload):
        return await asyncio.to_thread(self._forward, destination, payload)
