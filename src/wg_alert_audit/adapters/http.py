"""Thin HTTP client that records what actually happened.

Every request produces an :class:`Attempt`, which the classifier turns into an
:class:`AccessStatus`. Nothing here ever concludes that data is absent.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..core.access import Attempt, classify
from ..core.credentials import redact
from ..core.model import AccessStatus

USER_AGENT = (
    "wg-alert-audit/2.0 (historical wildfire evidence audit; contact via repository)"
)


@dataclass(slots=True)
class Response:
    attempt: Attempt
    status: AccessStatus
    reason: str
    body: bytes = b""
    content_type: str = ""

    @property
    def ok(self) -> bool:
        return self.status is AccessStatus.RETRIEVED

    @property
    def safe_url(self) -> str:
        """The URL with any credential stripped. Use this in all output."""
        return redact(self.attempt.url)


def fetch(
    url: str,
    *,
    source_id: str,
    timeout: float = 45.0,
    query_was_valid: bool = False,
    max_body: int = 8_000_000,
) -> Response:
    """Fetch a URL and classify the outcome honestly."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    attempt = Attempt(
        source_id=source_id, url=url, query_was_valid=query_was_valid
    )
    body = b""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_body)
            attempt.http_status = resp.status
            attempt.content_type = resp.headers.get("Content-Type", "")
            if resp.geturl() != url:
                attempt.redirect_to = resp.geturl()
    except urllib.error.HTTPError as e:
        attempt.http_status = e.code
        attempt.content_type = e.headers.get("Content-Type", "") if e.headers else ""
        try:
            body = e.read(max_body)
        except Exception:  # pragma: no cover - body may be unreadable
            body = b""
    except urllib.error.URLError as e:
        attempt.transport_error = str(e.reason)
    except (socket.timeout, TimeoutError):
        attempt.transport_error = "connection timed out"
    except Exception as e:  # pragma: no cover - defensive
        attempt.transport_error = f"{type(e).__name__}: {e}"

    attempt.body_sample = body[:4000].decode("utf-8", errors="replace")
    status, reason = classify(attempt)
    return Response(
        attempt=attempt,
        status=status,
        reason=reason,
        body=body,
        content_type=attempt.content_type,
    )
