"""Thin HTTP client that records what actually happened.

Every request produces an :class:`Attempt`, which the classifier turns into an
:class:`AccessStatus`. Nothing here ever concludes that data is absent.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..core.access import Attempt, classify
from ..core.credentials import redact
from ..core.model import AccessStatus

#: Several Korean government hosts reset a meaningful fraction of connections
#: regardless of client or User-Agent - measured at roughly one request in four
#: against safetydata.go.kr. A single failed attempt therefore carries almost no
#: information, which is exactly why :func:`fetch` retries before reporting.
USER_AGENT = "Mozilla/5.0 (compatible; wg-alert-audit/2.0; wildfire evidence audit)"

#: Backoff schedule, in seconds, between transport retries.
RETRY_BACKOFF: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0)


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
    retries: int = len(RETRY_BACKOFF),
) -> Response:
    """Fetch a URL and classify the outcome honestly.

    Transport failures are retried with backoff before being reported, because
    on these hosts a lone connection reset is noise rather than a finding.
    HTTP-level outcomes are **not** retried: a 401 or a 404 is an answer from
    the application, and asking again does not make it more true.
    """
    last: Response | None = None
    for i in range(retries + 1):
        resp = _fetch_once(url, source_id, timeout, query_was_valid, max_body)
        if resp.attempt.transport_error is None:
            if i:
                resp.reason += f" (succeeded on attempt {i + 1})"
            return resp
        last = resp
        if i < retries:
            time.sleep(RETRY_BACKOFF[min(i, len(RETRY_BACKOFF) - 1)])

    assert last is not None
    last.reason += f" (after {retries + 1} attempts)"
    return last


def _fetch_once(
    url: str,
    source_id: str,
    timeout: float,
    query_was_valid: bool,
    max_body: int,
) -> Response:
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
