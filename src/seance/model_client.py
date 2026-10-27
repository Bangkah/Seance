from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .errors import InputError, ModelError

LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})
CONTAINER = frozenset({"host.docker.internal", "ollama", "seance-ollama"})


@dataclass(frozen=True, slots=True)
class ModelConfig:
    endpoint: str = "http://127.0.0.1:11434"
    model: str = "qwen3:4b"
    num_ctx: int = 8192
    timeout: float = 240.0
    allow_container: bool = False

    def generate_url(self) -> str:
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"}:
            raise InputError("endpoint must start with http:// or https://")
        if parsed.username or parsed.password:
            raise InputError("endpoint must not contain credentials")
        if parsed.path not in {"", "/"}:
            raise InputError("endpoint must not contain a path")
        host = (parsed.hostname or "").lower()
        if not host:
            raise InputError("endpoint is missing a host")
        allowed = set(LOOPBACK)
        if self.allow_container:
            allowed |= CONTAINER
        if host not in allowed:
            raise InputError(
                "endpoint host must be loopback (localhost, 127.0.0.1, ::1); "
                f"got {host}. Container endpoints require --allow-container."
            )
        port = parsed.port or 11434
        rendered = f"[{host}]" if ":" in host else host
        return f"{parsed.scheme}://{rendered}:{port}/api/generate"


class ModelClient:
    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._url = config.generate_url()
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def url(self) -> str:
        return self._url

    @property
    def model(self) -> str:
        return self._config.model

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any] | None,
        temperature: float,
        seed: int,
    ) -> str:
        body: dict[str, Any] = {
            "model": self._config.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_ctx": self._config.num_ctx,
                "num_predict": 1400,
                "seed": seed,
            },
        }
        if schema is not None:
            body["format"] = schema
        request = urllib.request.Request(
            self._url,
            data=json.dumps(body, sort_keys=True).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self._config.timeout) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raise ModelError(f"Ollama returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ModelError(f"cannot reach Ollama at {self._url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ModelError(f"Ollama did not answer within {self._config.timeout:.0f}s") from exc
        except OSError as exc:
            raise ModelError(f"cannot reach Ollama at {self._url}: {exc}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelError("Ollama returned a non-JSON response") from exc
        if not isinstance(payload, dict):
            raise ModelError("Ollama returned an unexpected response")
        text = payload.get("response")
        if not isinstance(text, str) or not text.strip():
            raise ModelError("Ollama returned an empty response")
        return text
