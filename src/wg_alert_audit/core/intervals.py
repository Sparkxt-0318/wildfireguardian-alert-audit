"""Interval-censored time arithmetic over the extended reals.

Point event times are the exception in this audit, not the rule. A source that
says "11:24" has told us the minute, not the instant, and two sources that say
"11:24" and "11:25" have given us a conflict, not a mean of 11:24:30.

This module is the only place where times are combined. See
``docs/TIME_ONTOLOGY.md`` and failure modes FM-09, FM-20.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final

KST: Final = timezone(timedelta(hours=9))
UTC: Final = timezone.utc

NEG_INF: Final = -math.inf
POS_INF: Final = math.inf


class IntervalError(ValueError):
    """An interval operation that has no defined answer."""


@dataclass(frozen=True, slots=True)
class TimeInterval:
    """A closed interval of instants, with optionally infinite bounds.

    Bounds are POSIX seconds, or ``-inf`` / ``+inf``. ``unknown()`` is the
    unconstrained interval ``(-inf, +inf)``; it is *not* the empty set and
    carries no information.
    """

    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise IntervalError(
                f"lower bound {self.lower} exceeds upper bound {self.upper}"
            )

    # -- constructors ----------------------------------------------------

    @classmethod
    def unknown(cls) -> "TimeInterval":
        return cls(NEG_INF, POS_INF)

    @classmethod
    def at_instant(cls, dt: datetime) -> "TimeInterval":
        """A genuinely instantaneous time. Rare; prefer :meth:`at_minute`."""
        ts = _require_aware(dt).timestamp()
        return cls(ts, ts)

    @classmethod
    def at_minute(cls, dt: datetime) -> "TimeInterval":
        """Minute-resolution datum -> ``[mm:00, mm:59]`` (FM-20).

        A source printing ``11:24`` constrains the event to that minute. It does
        not assert that the event occurred at exactly ``11:24:00``.
        """
        base = _require_aware(dt).replace(second=0, microsecond=0)
        return cls(base.timestamp(), base.timestamp() + 59)

    @classmethod
    def at_second(cls, dt: datetime) -> "TimeInterval":
        """Second-resolution datum -> ``[ss, ss]``, e.g. a CBS record time."""
        base = _require_aware(dt).replace(microsecond=0)
        return cls(base.timestamp(), base.timestamp())

    @classmethod
    def before(cls, dt: datetime, *, inclusive: bool = True) -> "TimeInterval":
        """``(-inf, dt]`` — "by the time X happened, it had already happened"."""
        ts = _require_aware(dt).timestamp()
        return cls(NEG_INF, ts if inclusive else ts - 1)

    @classmethod
    def after(cls, dt: datetime, *, inclusive: bool = True) -> "TimeInterval":
        """``[dt, +inf)`` — "not before X"."""
        ts = _require_aware(dt).timestamp()
        return cls(ts if inclusive else ts + 1, POS_INF)

    @classmethod
    def between(cls, lo: datetime, hi: datetime) -> "TimeInterval":
        return cls(_require_aware(lo).timestamp(), _require_aware(hi).timestamp())

    # -- predicates ------------------------------------------------------

    @property
    def is_unknown(self) -> bool:
        return self.lower == NEG_INF and self.upper == POS_INF

    @property
    def is_bounded(self) -> bool:
        return math.isfinite(self.lower) and math.isfinite(self.upper)

    @property
    def is_point(self) -> bool:
        return self.is_bounded and self.lower == self.upper

    @property
    def width_seconds(self) -> float:
        """Width in seconds; ``inf`` if either bound is infinite."""
        if not self.is_bounded:
            return POS_INF
        return self.upper - self.lower

    def overlaps(self, other: "TimeInterval") -> bool:
        return self.lower <= other.upper and other.lower <= self.upper

    def contains(self, dt: datetime) -> bool:
        ts = _require_aware(dt).timestamp()
        return self.lower <= ts <= self.upper

    # -- combination -----------------------------------------------------

    def intersect(self, other: "TimeInterval") -> "TimeInterval | None":
        """Tighten by a second constraint. ``None`` when they are disjoint.

        Disjointness is a *contradiction*, surfaced to the caller rather than
        resolved here. Callers log it; they never average (FM-09).
        """
        lo, hi = max(self.lower, other.lower), min(self.upper, other.upper)
        if lo > hi:
            return None
        return TimeInterval(lo, hi)

    def hull(self, other: "TimeInterval") -> "TimeInterval":
        """Weakest interval containing both. Used to *retain* a conflict.

        This is the admissible way to summarise two conflicting sources: it
        widens to cover both, losing no possibility. It is not a reconciliation
        and it is not a mean.
        """
        return TimeInterval(min(self.lower, other.lower), max(self.upper, other.upper))

    def __sub__(self, other: "TimeInterval") -> "TimeInterval":
        """``F - A = [f_L - a_U, f_U - a_L]`` (docs/TIME_ONTOLOGY.md).

        This is the lead-time operation. Note the crossed bounds: the smallest
        possible lead pairs the earliest arrival with the latest alert.
        """
        lo = _sub_extended(self.lower, other.upper)
        hi = _sub_extended(self.upper, other.lower)
        if lo is None or hi is None:
            # inf - inf: no defined answer, so assert nothing.
            return TimeInterval.unknown()
        return TimeInterval(lo, hi)

    # -- rendering -------------------------------------------------------

    def format(self, tz: timezone = KST) -> str:
        """Render as an interval, never as a single collapsed time."""
        if self.is_unknown:
            return "unknown"
        lo = "-inf" if self.lower == NEG_INF else _fmt(self.lower, tz)
        hi = "+inf" if self.upper == POS_INF else _fmt(self.upper, tz)
        if self.lower == NEG_INF:
            return f"(-inf, {hi}]"
        if self.upper == POS_INF:
            return f"[{lo}, +inf)"
        if self.lower == self.upper:
            return f"[{lo}]"
        return f"[{lo}, {hi}]"

    def format_duration(self) -> str:
        """Render as a *duration* interval, for lead times."""
        if self.is_unknown:
            return "unknown"
        lo = "-inf" if self.lower == NEG_INF else _fmt_dur(self.lower)
        hi = "+inf" if self.upper == POS_INF else _fmt_dur(self.upper)
        return f"[{lo}, {hi}]"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"TimeInterval({self.format()})"


# -- helpers -------------------------------------------------------------


def _require_aware(dt: datetime) -> datetime:
    """Reject naive datetimes at the boundary.

    A naive datetime is the mechanism by which a UTC acquisition time silently
    becomes a KST wall-clock time (FM-02). There is no default timezone here.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise IntervalError(
            "naive datetime rejected: every instant needs an explicit timezone "
            "(FIRMS acq_time is UTC; Korean wall-clock sources are KST)"
        )
    return dt


def _sub_extended(a: float, b: float) -> float | None:
    """``a - b`` on the extended reals; ``None`` where undefined."""
    if math.isinf(a) and math.isinf(b) and (a > 0) == (b > 0):
        return None  # inf - inf
    return a - b


def _fmt(ts: float, tz: timezone) -> str:
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%dT%H:%M:%S%z")


def _fmt_dur(seconds: float) -> str:
    sign = "-" if seconds < 0 else ""
    s = int(abs(seconds))
    return f"{sign}{s // 3600:d}h{(s % 3600) // 60:02d}m"


_MINUTE_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_kst_minute(date_yyyymmdd: str, hhmm: str) -> TimeInterval:
    """Parse a Korean-source wall-clock minute into a KST minute interval.

    Used for news/official text that prints e.g. ``11:24``. The KST assumption
    is the caller's to record (``tz_assumed``); this function only refuses to
    invent a sub-minute precision the source never had.
    """
    m = _MINUTE_RE.match(hhmm.strip())
    if not m:
        raise IntervalError(f"not an HH:MM wall-clock time: {hhmm!r}")
    hh, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise IntervalError(f"out-of-range wall-clock time: {hhmm!r}")
    d = datetime.strptime(date_yyyymmdd, "%Y-%m-%d").replace(
        hour=hh, minute=mm, tzinfo=KST
    )
    return TimeInterval.at_minute(d)


def firms_acq_to_interval(acq_date: str, acq_time: str) -> TimeInterval:
    """Convert FIRMS ``acq_date`` + ``acq_time`` to a UTC minute interval.

    FIRMS reports acquisition in **UTC**, with ``acq_time`` as ``HHMM`` (often
    zero-stripped, e.g. ``"310"`` meaning 03:10). Reading these as KST is
    FM-02 and shifts every detection by nine hours, frequently across midnight.
    """
    raw = acq_time.strip()
    if not raw or not raw.isdigit():
        # "".zfill(4) is "0000", so a blank field silently became midnight UTC
        # in the one function whose whole purpose is timezone correctness.
        raise IntervalError(f"FIRMS acq_time is blank or non-numeric: {acq_time!r}")
    padded = raw.zfill(4)
    hh, mm = int(padded[:2]), int(padded[2:])
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise IntervalError(f"out-of-range FIRMS acq_time: {acq_time!r}")
    d = datetime.strptime(acq_date.strip(), "%Y-%m-%d").replace(
        hour=hh, minute=mm, tzinfo=UTC
    )
    return TimeInterval.at_minute(d)
