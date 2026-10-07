import threading
from dataclasses import dataclass, field
from typing import Optional, Union

TIMEOUT = "timeout"


class RequestTimeout(Exception):
    pass


@dataclass
class Response:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class SentRequest:
    url: str
    body: str
    headers: dict[str, str]
    at: float


Scripted = Union[int, str, Response]


class FakeHttpClient:
    """Stand-in for a real HTTP client; nothing goes over the network.

    Each URL has a script of outcomes returned in order: an int status code,
    a Response (to set headers such as Retry-After) or TIMEOUT. Once a URL's
    script runs out, every further call to it returns 200.
    """

    def __init__(self, clock, responses: Optional[dict[str, list[Scripted]]] = None):
        self._clock = clock
        self._lock = threading.Lock()
        self._scripts = {url: list(items) for url, items in (responses or {}).items()}
        self.sent: list[SentRequest] = []

    def script(self, url: str, responses: list[Scripted]) -> None:
        with self._lock:
            self._scripts.setdefault(url, []).extend(responses)

    def send(self, url: str, body: str, headers: dict[str, str]) -> Response:
        with self._lock:
            self.sent.append(SentRequest(url, body, dict(headers), self._clock.now()))
            queue = self._scripts.get(url)
            outcome = queue.pop(0) if queue else 200
        if outcome == TIMEOUT:
            raise RequestTimeout(f"request to {url} timed out")
        if isinstance(outcome, Response):
            return outcome
        return Response(int(outcome))

    def sent_to(self, url: str) -> list[SentRequest]:
        return [r for r in self.sent if r.url == url]
