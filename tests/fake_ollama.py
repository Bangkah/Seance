from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeOllama:
    def __init__(self, mode: str = "good") -> None:
        self.mode = mode
        self.requests: list[dict[str, Any]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) or b"{}"
                body = json.loads(raw)
                owner.requests.append(body)
                text = owner._respond(body)
                payload = json.dumps({"response": text}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: object) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def __enter__(self) -> FakeOllama:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _respond(self, body: dict[str, Any]) -> str:
        if self.mode == "garbage":
            return "not json at all"
        prompt = json.loads(body.get("prompt", "{}"))
        ids = [str(item) for item in prompt.get("evidence_ids", [])]
        if not ids:
            ids = ["M:commits"]
        if self.mode == "unknown_ids":
            ids = ["C:deadbee"]
        first, last = ids[0], ids[-1]
        if "question" in prompt:
            return json.dumps(
                {
                    "answer": "The record only shows what the commits still say.",
                    "evidence_ids": [first],
                }
            )
        return json.dumps(
            {
                "summary": {
                    "text": "A small abandoned utility that the record still remembers.",
                    "evidence_ids": [first],
                },
                "purpose": {
                    "text": "It existed to handle one narrow job for one narrow team.",
                    "evidence_ids": [last],
                },
                "timeline": [
                    {"text": "Work begins and the first traces appear.", "evidence_ids": [first]},
                    {"text": "The last traces of work are recorded.", "evidence_ids": [last]},
                ],
                "death_hypotheses": [
                    {
                        "text": "Attention moved elsewhere and the work simply stopped.",
                        "evidence_ids": [last],
                        "confidence": "medium",
                    }
                ],
                "revival_steps": [
                    {
                        "text": "Read the last commits before deciding anything.",
                        "evidence_ids": [last],
                    }
                ],
            }
        )
