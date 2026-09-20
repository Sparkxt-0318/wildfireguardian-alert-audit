"""NASA FIRMS active-fire adapter (VIIRS / MODIS).

March 2025 is historical, and that changes which product to ask for. FIRMS
splits each sensor into a rolling **NRT** window and a contiguous **SP**
(standard processing, science quality) archive behind it, with roughly a
five-month lag. Querying ``VIIRS_SNPP_NRT`` for March 2025 therefore returns
nothing - not because no fire was observed, but because that date has moved out
of the NRT window into SP. Reading such an empty result as "no detections"
would be the exact error this repository exists to avoid.

The ``version`` column is retained on every row because it carries the SP/NRT
provenance in band (``"2.0"`` vs ``"2.0NRT"``).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from ..core import credentials
from ..core.intervals import TimeInterval, firms_acq_to_interval
from ..core.model import AccessStatus
from .http import Response, fetch

API_ROOT = "https://firms.modaps.eosdis.nasa.gov/api"

#: Max days per Area API call, per the official documentation.
MAX_DAY_RANGE = 5

#: Sources appropriate for a March 2025 query. SP is the science-quality
#: archive; NOAA-21 has no SP stream, so its NRT window reaches back further.
HISTORICAL_SOURCES: tuple[str, ...] = (
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
    "MODIS_SP",
    "VIIRS_NOAA21_NRT",
)

#: Sources whose rolling window will NOT contain March 2025 when queried now.
#: Listed so that an empty result from one of them is explained rather than
#: mistaken for an absence of fire.
ROLLING_NRT_SOURCES: tuple[str, ...] = (
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "MODIS_NRT",
)

#: Gyeongbuk bounding box, west,south,east,north as the Area API expects.
GYEONGBUK_BBOX = "128.5,36.0,129.6,37.0"


@dataclass(slots=True)
class Detection:
    """One active-fire pixel, with acquisition time kept distinct from retrieval."""

    latitude: float
    longitude: float
    acq_date: str
    acq_time: str
    satellite: str
    instrument: str
    confidence: str
    version: str
    frp: float | None
    daynight: str
    brightness: float | None
    source: str
    product: str
    #: UTC acquisition interval. Never a Korean wall-clock time.
    acquisition_interval: TimeInterval = field(init=False)

    def __post_init__(self) -> None:
        self.acquisition_interval = firms_acq_to_interval(self.acq_date, self.acq_time)

    @property
    def is_science_quality(self) -> bool:
        """SP rows carry a bare version; NRT rows are suffixed."""
        return not any(
            self.version.upper().endswith(s) for s in ("NRT", "RT", "URT")
        )


def area_url(
    map_key: str, source: str, bbox: str, day_range: int, start: date
) -> str:
    """Build an Area API URL.

    Note the coordinate order: the Area API takes a bounding box as
    ``west,south,east,north``, not the compass-named parameters used elsewhere
    on the FIRMS site.
    """
    if not 1 <= day_range <= MAX_DAY_RANGE:
        raise ValueError(f"day_range must be 1..{MAX_DAY_RANGE}, got {day_range}")
    return (
        f"{API_ROOT}/area/csv/{map_key}/{source}/{bbox}/{day_range}/{start:%Y-%m-%d}"
    )


def parse_csv(text: str, source: str) -> list[Detection]:
    """Parse an Area API CSV. VIIRS and MODIS differ in their brightness columns."""
    rows = list(csv.DictReader(io.StringIO(text)))
    out: list[Detection] = []
    for r in rows:
        if not r.get("latitude"):
            continue
        out.append(
            Detection(
                latitude=float(r["latitude"]),
                longitude=float(r["longitude"]),
                acq_date=r["acq_date"],
                acq_time=r["acq_time"],
                satellite=r.get("satellite", ""),
                instrument=r.get("instrument", ""),
                confidence=r.get("confidence", ""),
                version=r.get("version", ""),
                frp=_float_or_none(r.get("frp")),
                daynight=r.get("daynight", ""),
                # VIIRS: bright_ti4. MODIS: brightness.
                brightness=_float_or_none(
                    r.get("bright_ti4") or r.get("brightness")
                ),
                source=source,
                product=_product_for(source),
            )
        )
    return out


def _product_for(source: str) -> str:
    if source.startswith("VIIRS"):
        return "VIIRS 375 m active fire"
    if source.startswith("MODIS"):
        return "MODIS 1 km active fire (C6.1)"
    return source


def _float_or_none(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "", "nan") else None
    except ValueError:
        return None


@dataclass(slots=True)
class FetchResult:
    source: str
    url_redacted: str
    status: AccessStatus
    reason: str
    detections: list[Detection] = field(default_factory=list)
    note: str = ""


def retrieve(
    source: str, start: date, day_range: int = MAX_DAY_RANGE, bbox: str = GYEONGBUK_BBOX
) -> FetchResult:
    """Retrieve detections, or explain precisely why not.

    Without a MAP_KEY this returns ``API_KEY_REQUIRED`` - which means the data
    exists and is gated, and is recorded as a credential gap, never as absence.
    """
    key = credentials.get("firms")
    if not key:
        return FetchResult(
            source=source,
            url_redacted=area_url("<REDACTED>", source, bbox, day_range, start),
            status=AccessStatus.API_KEY_REQUIRED,
            reason=(
                "no FIRMS_MAP_KEY in the environment. The dataset exists and is "
                "gated; this is a credential gap, not data absence (FM-01)"
            ),
            note=(
                "Obtain a free key by email at "
                "https://firms.modaps.eosdis.nasa.gov/api/map_key/ and set "
                "FIRMS_MAP_KEY."
            ),
        )

    url = area_url(key, source, bbox, day_range, start)
    resp: Response = fetch(url, source_id=f"firms-{source}", query_was_valid=True)
    safe = resp.safe_url

    if not resp.ok:
        return FetchResult(source, safe, resp.status, resp.reason)

    text = resp.body.decode("utf-8", errors="replace")
    detections = parse_csv(text, source)
    if not detections:
        rolling = source in ROLLING_NRT_SOURCES
        return FetchResult(
            source=source,
            url_redacted=safe,
            status=(
                AccessStatus.UNKNOWN if rolling else AccessStatus.NO_RELEVANT_RECORD
            ),
            reason=(
                "empty result from a rolling NRT source, which is expected for a "
                "historical date and says nothing about whether fire was observed; "
                "query the SP archive instead"
                if rolling
                else "valid query against the SP archive returned zero rows"
            ),
            note="use one of: " + ", ".join(HISTORICAL_SOURCES) if rolling else "",
        )

    return FetchResult(source, safe, AccessStatus.RETRIEVED, resp.reason, detections)


def windows(start: date, end: date, day_range: int = MAX_DAY_RANGE) -> list[date]:
    """Split a date span into Area-API-sized windows.

    The caller should widen the span by a day at each end: FIRMS dates are UTC,
    so KST 00:00-08:59 falls on the previous UTC date and would otherwise be
    silently dropped.
    """
    out, d = [], start
    while d <= end:
        out.append(d)
        d += timedelta(days=day_range)
    return out
