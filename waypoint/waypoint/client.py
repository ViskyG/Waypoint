"""Small authenticated loopback client; retry callers reuse the same event IDs."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from .domain import ContractError, canonical
from .security import load_tokens


class Unavailable(ConnectionError):
    pass


class Client:
    def __init__(self, directory: Path, url: str | None = None, timeout: float = 1.5):
        self.directory = directory
        self.tokens = load_tokens(directory)
        if url is None:
            config = directory / "connection.json"
            url = json.loads(config.read_text())["url"] if config.exists() else "http://127.0.0.1:8769"
        parsed = urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("Only explicit local HTTP service addresses are allowed")
        self.url, self.timeout = url.rstrip("/"), timeout

    def call(self, method: str, path: str, body: dict | None = None):
        data = canonical(body).encode() if body is not None else None
        request = Request(self.url + path, data=data, method=method,
                          headers={"Authorization": "Bearer " + self.tokens["write" if method != "GET" else "read"], "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read(100_000))
            except ValueError:
                detail = {"error": "http_error", "message": str(exc.code)}
            raise ContractError(detail.get("error", "http_error"), detail.get("message", str(exc.code)), detail.get("detail")) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise Unavailable("Local Waypoint service is unavailable") from exc
