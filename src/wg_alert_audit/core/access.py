"""Classify what actually happened when we tried to fetch something.

This module exists because of one recurring error: concluding that data does
not exist because a request failed. The classifier never emits "absent". The
strongest thing it can say is ``NO_RELEVANT_RECORD``, and only when handed
proof that a query succeeded and returned nothing.

See ``docs/ACCESS_STATUS_MODEL.md``, FM-01 / FM-19.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .model import AccessStatus

# Bodies that mean "the dataset is there, your key is not".
_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"invalid\s+map[_\s-]?key", re.I),
    re.compile(r"\bmap[_\s-]?key\b.*\b(missing|required|invalid|expired)\b", re.I),
    re.compile(r"service\s*key\s*is\s*not\s*registered", re.I),
    re.compile(r"\bSERVICE_KEY_IS_NOT_REGISTERED_ERROR\b"),
    re.compile(r"등록되지\s*않은\s*(인증키|서비스키)"),
    re.compile(r"인증키가?\s*(유효하지|올바르지)\s*않", re.I),
    re.compile(r"\b(api[_\s-]?key|apikey|authKey|serviceKey)\b.*\b(invalid|required|missing)\b", re.I),
    re.compile(r"\bunauthorized\b.*\bkey\b", re.I),
)

# Bodies that mean "log in as a person".
_AUTH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<form[^>]*\b(login|signin|로그인)\b", re.I),
    re.compile(r"\b(please\s+log\s?in|login\s+required|sign\s+in\s+to\s+continue)\b", re.I),
    re.compile(r"로그인\s*(이|후|해야|필요)"),
    re.compile(r"\bEarthdata\s+Login\b", re.I),
)

# Bodies that mean "apply for access first".
_REGISTRATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"활용\s*신청"),
    re.compile(r"신청\s*후\s*(이용|사용)"),
    re.compile(r"\b(request|apply\s+for)\s+access\b", re.I),
    re.compile(r"\bregistration\s+(is\s+)?required\b", re.I),
)

# Bodies/headers that mean "we moved".
_MIGRATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Allow an intervening particle: 서비스"는" 종료되었습니다.
    re.compile(r"서비스[가-힣]{0,2}\s*(종료|중단|이전|이관)"),
    re.compile(r"(이전|이관)\s*안내"),
    re.compile(r"페이지가?\s*(이동|변경)되었"),
    re.compile(r"\b(this\s+service\s+has\s+)?(moved|relocated|been\s+migrated)\b", re.I),
    re.compile(r"\bhas\s+been\s+(discontinued|retired)\b.*\buse\b", re.I),
)

# Bodies that mean "a human can download this, a script cannot".
_MANUAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(download\s+request|request\s+form|order\s+form)\b", re.I),
    re.compile(r"다운로드\s*신청"),
    re.compile(r"\b(javascript|JS)\s+(is\s+)?required\b", re.I),
    re.compile(r"<noscript>", re.I),
)

_RATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(rate\s*limit|too\s+many\s+requests|quota\s+exceeded)\b", re.I),
    re.compile(r"(일일|요청)\s*(호출)?\s*한도\s*초과"),
    re.compile(r"\bLIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR\b"),
)


@dataclass(slots=True)
class Attempt:
    """One acquisition attempt, with everything needed to justify its status."""

    source_id: str
    url: str
    method: str = "GET"
    http_status: int | None = None
    body_sample: str = ""
    content_type: str = ""
    transport_error: str | None = None
    redirect_to: str | None = None
    #: Set True only when the response was parsed and contained zero records.
    parsed_empty_result: bool = False
    #: Set True when the request was well-formed against the correct dataset.
    query_was_valid: bool = False
    attempted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notes: str = ""

    @property
    def redirect_is_cross_host(self) -> bool:
        if not self.redirect_to:
            return False
        return urlsplit(self.url).netloc.lower() != urlsplit(self.redirect_to).netloc.lower()


def classify(attempt: Attempt) -> tuple[AccessStatus, str]:
    """Return ``(status, reason)``. The reason is recorded with the status.

    Order matters: body signals are checked before bare status codes, because
    Korean and NASA services routinely return **200 OK** with an error document
    in the body. Trusting the status code alone is how a gated dataset gets
    mistaken for an empty one.
    """
    body = attempt.body_sample or ""

    # 1. Transport never reached the application.
    if attempt.transport_error:
        err = attempt.transport_error.lower()
        if any(k in err for k in ("timed out", "timeout", "reset", "refused",
                                  "unreachable", "name resolution", "dns",
                                  "connection aborted", "eof occurred")):
            return (
                AccessStatus.TEMPORARY_NETWORK_FAILURE,
                f"transport failure, application never reached: {attempt.transport_error}",
            )
        return (
            AccessStatus.UNKNOWN,
            f"unclassified transport error: {attempt.transport_error}",
        )

    # 2. Body signals, which can accompany any status code including 200.
    if _any(_KEY_PATTERNS, body):
        return (
            AccessStatus.API_KEY_REQUIRED,
            "response body states the key is missing/invalid: the dataset "
            "exists and is gated, which is not data absence (FM-01)",
        )
    if _any(_RATE_PATTERNS, body):
        return (AccessStatus.RATE_LIMITED, "response body indicates quota/rate limiting")
    if _any(_MIGRATION_PATTERNS, body):
        return (AccessStatus.ENDPOINT_MIGRATED, "response body carries a migration/termination notice")
    if _any(_REGISTRATION_PATTERNS, body):
        return (AccessStatus.REGISTRATION_REQUIRED, "response body requires an access application")
    if _any(_AUTH_PATTERNS, body):
        return (AccessStatus.AUTHENTICATION_REQUIRED, "response body presents a login requirement")

    # 3. Redirects.
    if attempt.http_status in (301, 302, 303, 307, 308):
        if attempt.redirect_is_cross_host:
            return (
                AccessStatus.ENDPOINT_MIGRATED,
                f"cross-host redirect to {attempt.redirect_to}",
            )
        return (AccessStatus.UNKNOWN, "same-host redirect; follow it and re-classify")

    # 4. Status codes.
    s = attempt.http_status
    if s == 429:
        return (AccessStatus.RATE_LIMITED, "HTTP 429")
    if s == 401:
        return (
            AccessStatus.API_KEY_REQUIRED if _looks_key_based(attempt.url)
            else AccessStatus.AUTHENTICATION_REQUIRED,
            "HTTP 401",
        )
    if s == 403:
        return (AccessStatus.ACCESS_DENIED, "HTTP 403 without a login affordance")
    if s == 404:
        # A 404 is only a statement about a resource if the service is alive and
        # the request was well-formed. Otherwise it is a migration symptom.
        if attempt.query_was_valid:
            return (AccessStatus.NOT_FOUND, "HTTP 404 on a well-formed request to a live service")
        return (
            AccessStatus.ENDPOINT_MIGRATED,
            "HTTP 404 on an unverified path: treated as a migration symptom, "
            "not as a statement about the resource (docs/ACCESS_STATUS_MODEL.md rule 2)",
        )
    if s is not None and 500 <= s < 600:
        return (AccessStatus.SERVER_ERROR, f"HTTP {s}")

    # 5. Success.
    if s is not None and 200 <= s < 300:
        if _any(_MANUAL_PATTERNS, body):
            return (
                AccessStatus.MANUAL_DOWNLOAD_AVAILABLE,
                "page served, but obtaining the data needs a human through the UI",
            )
        if attempt.parsed_empty_result:
            if not attempt.query_was_valid:
                return (
                    AccessStatus.UNKNOWN,
                    "empty result, but the query was not confirmed valid against "
                    "the correct dataset; NO_RELEVANT_RECORD withheld (FM-19)",
                )
            return (
                AccessStatus.NO_RELEVANT_RECORD,
                "valid query against the correct dataset returned zero records",
            )
        return (AccessStatus.RETRIEVED, f"HTTP {s} with usable body")

    return (AccessStatus.UNKNOWN, "no status and no transport error recorded")


def _any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(p.search(text) for p in patterns)


def _looks_key_based(url: str) -> bool:
    return bool(
        re.search(r"(MAP_KEY|map_key|serviceKey|service_key|authKey|apikey|api_key)", url)
    )
