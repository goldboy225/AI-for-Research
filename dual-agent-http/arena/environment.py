"""Loopback-only HTTP simulator with bounded, exact request construction."""
import http.client
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from .scenarios import policy, scenario

class Environment:
    def __init__(self, config):
        self.config = config
        self.current_policy = ()
        self.count = 0
        self.started = time.monotonic()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            timeout = 2
            def do_GET(self):
                # No arbitrary paths, URLs, bodies, files, shell, or upstream fetches.
                prefix = '/simulate/'
                try:
                    if not self.path.startswith(prefix):
                        raise ValueError('Unknown route')
                    item = scenario(self.path[len(prefix):])
                except ValueError:
                    self.send_error(404)
                    return
                blocked = item.feature in owner.current_policy
                body = json.dumps({'feature': item.feature, 'blocked': blocked,
                                   'outcome': 'denied' if blocked else 'served'}).encode()
                self.send_response(403 if blocked else 200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        # No configurable host or target: always use a newly bound loopback socket.
        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.server.timeout = 0.1
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def set_policy(self, selected):
        self.current_policy = policy(selected)

    def execute(self, identifier):
        item = scenario(identifier)  # Validate before any connection.
        if self.count >= self.config.max_requests:
            raise RuntimeError('Request quota exhausted')
        if time.monotonic() - self.started >= self.config.max_runtime_seconds:
            raise TimeoutError('Experiment runtime quota exhausted')
        self.count += 1
        remaining = self.config.max_runtime_seconds - (time.monotonic() - self.started)
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port,
            timeout=max(0.001, min(self.config.request_timeout_seconds, remaining)))
        begin = time.perf_counter()
        try:
            connection.request('GET', '/simulate/' + item.id)
            response = connection.getresponse()
            body = response.read(4097)
            if len(body) > 4096:
                raise RuntimeError('Response quota exceeded')
            observation = json.loads(body)
            observation['status'] = response.status
            observation['http_latency_ms'] = (time.perf_counter() - begin)*1000
            return observation
        finally:
            connection.close()

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
