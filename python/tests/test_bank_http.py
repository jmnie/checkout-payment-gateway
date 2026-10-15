"""Exercise HTTPX over a real socket, including response and timeout failures."""

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from payment_gateway_api.bank import BankClient, BankError
from payment_gateway_api.models import PaymentRequest


@pytest.mark.parametrize(
    "status,body,delay,expected",
    [
        (200, '{"authorized":true}', 0, True),
        (200, '{"authorized":false}', 0, False),
        (503, "{}", 0, 503),
        (500, "{}", 0, 502),
        (200, "broken", 0, 502),
        (200, '{"authorized":true}', 0.3, 504),
    ],
)
def test_actual_http_transport(payload, status, body, delay, expected):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            time.sleep(delay)
            self.send_response(status)
            self.end_headers()
            try:
                self.wfile.write(body.encode())
            except BrokenPipeError:
                pass  # The timeout case deliberately closes the client connection.

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def run():
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{server.server_port}", timeout=0.1
        ) as client:
            return await BankClient(client).authorize(PaymentRequest.model_validate(payload))

    try:
        if type(expected) is bool:
            assert asyncio.run(run()) is expected
        else:
            with pytest.raises(BankError) as error:
                asyncio.run(run())
            assert error.value.status_code == expected
        assert len(received) == 1
        assert received[0]["expiry_date"] == "12/2099"
        assert received[0]["cvv"] == "012"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
