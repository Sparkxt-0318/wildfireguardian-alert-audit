"""Harvester for the public safetydata.go.kr 재난문자 archive.

This is the audit's most important discovery. The **API** for historical
emergency alerts is credential-gated, but the same MOIS platform also publishes
a server-rendered archive of the alerts themselves at
``/disaster-data/disasterNotification`` with **no credential at all**, carrying:

* the send timestamp to the **second**,
* the complete message text as transmitted,
* the issuing authority,
* a stable record id (``sn``).

That makes these ``PRIMARY_OPERATIONAL`` records: they are the operational
system's own output, not a report about it. It is the only route this audit
found to first-public-warning timing that does not require a credential the
agent must not obtain.

The gated API remains the better route - it supports structured region and date
filtering and returns typed fields - so it is still recorded as
``API_KEY_REQUIRED`` rather than being written off.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..core.intervals import TimeInterval
from ..core.model import AccessStatus
from .http import fetch

KST = timezone(timedelta(hours=9))

LIST_URL = "https://www.safetydata.go.kr/disaster-data/disasterNotification"
DETAIL_URL = "https://www.safetydata.go.kr/disaster-data/disasterNotificationDetail"

#: One table row of the archive listing.
_ROW = re.compile(
    r'<td class="cell-no">(?P<no>\d+)</td>.*?'
    r'href="/disaster-data/disasterNotificationDetail\?sn=(?P<sn>\d+)">'
    r'(?P<text>.*?)</a>.*?'
    r'<td class="cell-date">(?P<sent>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})</td>',
    re.S,
)

#: Issuing authority is appended to the message in square brackets.
_ISSUER = re.compile(r"\[([^\[\]]{1,40})\]\s*$")

#: Total record count, e.g. 전체 1,234 건.
_TOTAL = re.compile(r"전체\s*<[^>]*>?\s*([\d,]+)\s*<?[^>]*>?\s*건")


@dataclass(slots=True)
class ArchivedAlert:
    """One emergency-alert record as published by the operational platform."""

    sn: str
    sent_raw: str
    message_text: str
    issuing_authority: str
    source_url: str
    #: Send time at second resolution - this is a genuine ALERT_SEND_TIME.
    send_interval: TimeInterval = field(init=False)

    def __post_init__(self) -> None:
        dt = datetime.strptime(self.sent_raw, "%Y/%m/%d %H:%M:%S").replace(tzinfo=KST)
        self.send_interval = TimeInterval.at_second(dt)

    @property
    def sent_kst(self) -> datetime:
        return datetime.strptime(self.sent_raw, "%Y/%m/%d %H:%M:%S").replace(tzinfo=KST)

    def to_json(self) -> dict:
        return {
            "record_id": self.sn,
            "send_time_raw": self.sent_raw,
            "send_time_kst": self.sent_kst.isoformat(),
            "send_interval": self.send_interval.format(KST),
            "message_text": self.message_text,
            "issuing_authority": self.issuing_authority,
            "source_system": "safetydata.go.kr/disaster-data (public archive)",
            "retrieval_provenance": self.source_url,
            "evidence_class": "PRIMARY_OPERATIONAL",
            "time_role": "ALERT_SEND_TIME",
        }


def _clean(raw_html: str) -> str:
    """Strip markup and unescape, preserving the message text verbatim."""
    return html.unescape(re.sub(r"<[^>]+>", "", raw_html)).strip()


def parse_listing(page_html: str, source_url: str) -> list[ArchivedAlert]:
    out: list[ArchivedAlert] = []
    for m in _ROW.finditer(page_html):
        text = _clean(m.group("text"))
        issuer_match = _ISSUER.search(text)
        issuer = issuer_match.group(1) if issuer_match else ""
        out.append(
            ArchivedAlert(
                sn=m.group("sn"),
                sent_raw=m.group("sent"),
                message_text=text,
                issuing_authority=issuer,
                source_url=f"{DETAIL_URL}?sn={m.group('sn')}",
            )
        )
    return out


def total_records(page_html: str) -> int | None:
    m = _TOTAL.search(page_html)
    return int(m.group(1).replace(",", "")) if m else None


def page_url(start: str, end: str, page: int, per_page: int = 100) -> str:
    return (
        f"{LIST_URL}?searchStartDttm={start}&searchEndDttm={end}"
        f"&currentPage={page}&cntPerPage={per_page}"
    )


@dataclass(slots=True)
class HarvestResult:
    alerts: list[ArchivedAlert]
    pages_fetched: int
    status: AccessStatus
    reason: str
    total_reported: int | None = None


def harvest(
    start: str, end: str, *, per_page: int = 100, max_pages: int = 80
) -> HarvestResult:
    """Page through the archive for a date range.

    Stops on an empty page. A page that fails transport is retried once; a
    second failure stops the harvest with the real status rather than silently
    truncating the corpus and letting a short result look like a small event.
    """
    alerts: list[ArchivedAlert] = []
    seen: set[str] = set()
    total: int | None = None
    page = 1

    while page <= max_pages:
        url = page_url(start, end, page, per_page)
        resp = fetch(url, source_id="safetydata-archive", query_was_valid=True)
        if not resp.ok:
            resp = fetch(url, source_id="safetydata-archive", query_was_valid=True)
        if not resp.ok:
            return HarvestResult(
                alerts, page - 1, resp.status,
                f"stopped at page {page}: {resp.reason}", total,
            )

        body = resp.body.decode("utf-8", errors="replace")
        if total is None:
            total = total_records(body)
        rows = parse_listing(body, url)
        if not rows:
            return HarvestResult(
                alerts, page - 1, AccessStatus.RETRIEVED,
                f"harvest complete: page {page} returned no rows", total,
            )
        fresh = [a for a in rows if a.sn not in seen]
        if not fresh:
            return HarvestResult(
                alerts, page - 1, AccessStatus.RETRIEVED,
                f"harvest complete: page {page} repeated earlier rows", total,
            )
        for a in fresh:
            seen.add(a.sn)
        alerts.extend(fresh)
        page += 1

    return HarvestResult(
        alerts, page - 1, AccessStatus.RETRIEVED,
        f"stopped at the {max_pages}-page safety limit", total,
    )
