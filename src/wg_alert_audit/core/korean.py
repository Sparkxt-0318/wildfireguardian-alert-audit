"""Korean wildfire/alert event-label extraction, with negative rules.

Korean compounds by prefixing, which makes naive substring matching actively
dangerous here:

    발화    ignition
    재발화  RE-ignition (a flare-up after the fire was declared out)

``재발화`` contains ``발화``. A substring matcher reads a flare-up at 18:00 as
an *ignition* at 18:00, which moves the apparent start of the fire by hours and
corrupts every downstream interval. The same trap holds for 진화/재진화, and for
대피 (evacuation, as a topic) against 대피명령 (an actual order).

Strategy: longest-match-first over an explicit lexicon, plus negative rules that
veto a short label when a longer one covers the same span. The original Korean
is always retained next to the normalised label (X-5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

from .model import Quantity


@dataclass(frozen=True, slots=True)
class LabelSpec:
    """One lexicon entry.

    ``context_required`` and ``context_forbidden`` exist because some surfaces
    are only events in the right company. 발생 ("occurrence") is the clearest
    case: 산불 발생 reports a fire, but 연기 다량 발생 reports smoke, 인명사고
    발생 reports casualties, 산불발생 위험 reports a *risk*, and 산불이 발생하지
    않도록 asks that fires NOT occur. Treating the bare surface as an event
    turns all four into ignition reports.
    """

    surface: str
    quantity: Quantity | None
    gloss: str
    #: Longer surfaces that must be preferred over this one at the same span.
    blocked_by: tuple[str, ...] = ()
    #: At least one must appear in the surrounding window, or the label is dropped.
    context_required: tuple[str, ...] = ()
    #: If any appears in the surrounding window, the label is dropped.
    context_forbidden: tuple[str, ...] = ()
    #: Characters of context inspected either side of the match.
    context_window: int = 18


#: Ordered longest-first at match time, not here.
LEXICON: Final[tuple[LabelSpec, ...]] = (
    # --- ignition family -------------------------------------------------
    LabelSpec("최초발화", Quantity.IGNITION, "initial ignition"),
    LabelSpec("재발화", Quantity.RE_IGNITION, "re-ignition / flare-up"),
    LabelSpec("발화", Quantity.IGNITION, "ignition",
              blocked_by=("재발화", "최초발화")),
    LabelSpec("최초신고", Quantity.REPORTED_IGNITION, "first report to authorities"),
    LabelSpec("신고접수", Quantity.REPORTED_IGNITION, "report received"),
    # 발화지점 is a LOCATION noun ("the ignition point"), not a report that an
    # ignition just occurred. It must not yield a bare ignition event.
    LabelSpec("발화지점", None, "ignition POINT - a location, not an event"),
    LabelSpec(
        "발생",
        Quantity.REPORTED_IGNITION,
        "occurrence of a fire, as reported",
        # Only an occurrence OF a fire counts.
        context_required=("산불", "화재"),
        # ...and not a risk of one, a prevention notice, a negated one, or the
        # occurrence of something else that merely mentions a fire nearby.
        context_forbidden=(
            "위험", "우려", "예방", "조심", "주의보", "경보 발령",
            "않도록", "않게", "없도록",
            "연기", "인명사고", "사고 발생", "정전", "단수", "피해 발생",
        ),
    ),
    # --- suppression family ----------------------------------------------
    LabelSpec("재진화", None, "re-suppression after a flare-up"),
    LabelSpec("주불진화", Quantity.CONTAINMENT, "main fire extinguished"),
    LabelSpec("진화완료", Quantity.CONTAINMENT, "suppression complete"),
    LabelSpec("완전진화", Quantity.CONTAINMENT, "fully extinguished"),
    LabelSpec(
        "진화",
        Quantity.CONTAINMENT,
        "suppression",
        blocked_by=("재진화", "주불진화", "진화완료", "완전진화", "진화율", "진화중"),
        # Suppression IN PROGRESS is the opposite of containment. The veto list
        # above only catches the unspaced 진화중; Korean writes 진화 중 and
        # 진화 작업 중 just as often, so the spaced forms are vetoed by context.
        context_forbidden=("진화 중", "진화중", "진화 작업", "진화작업", "진화율"),
    ),
    LabelSpec("진화율", None, "containment percentage (a rate, not an event)"),
    # --- evacuation family -----------------------------------------------
    LabelSpec("대피명령", Quantity.EVACUATION_ORDER, "evacuation ORDER"),
    LabelSpec("대피령", Quantity.EVACUATION_ORDER, "evacuation order"),
    LabelSpec("긴급대피", Quantity.EVACUATION_ORDER, "emergency evacuation"),
    LabelSpec("대피권고", None, "evacuation ADVISORY (not an order)"),
    LabelSpec("대피 권고", None, "evacuation ADVISORY (not an order)"),
    LabelSpec("대피소", None, "evacuation shelter (a place, not an event)"),
    LabelSpec("대피유도", None, "evacuation guidance"),
    LabelSpec("대피", None, "evacuation mentioned generically - NOT an order",
              blocked_by=("대피명령", "대피령", "긴급대피", "대피권고", "대피 권고",
                          "대피소", "대피유도")),
    # --- alerting ---------------------------------------------------------
    LabelSpec("긴급재난문자", Quantity.FIRST_PUBLIC_WARNING, "emergency alert message (CBS)"),
    LabelSpec("안전안내문자", Quantity.FIRST_PUBLIC_WARNING, "safety guidance message"),
    LabelSpec("위급재난문자", Quantity.FIRST_PUBLIC_WARNING, "critical emergency alert"),
    LabelSpec("재난문자", Quantity.FIRST_PUBLIC_WARNING, "disaster text message",
              blocked_by=("긴급재난문자", "안전안내문자", "위급재난문자")),
    LabelSpec("재난방송", None, "disaster broadcast"),
    # --- fire behaviour ---------------------------------------------------
    LabelSpec("산불확산", None, "wildfire spread"),
    LabelSpec("산불 확산", None, "wildfire spread"),
    LabelSpec("산불", None, "wildfire (topic)", blocked_by=("산불확산", "산불 확산")),
    LabelSpec("화선", None, "fire line"),
    LabelSpec("비화", None, "spotting (ember transport)"),
)

_BY_SURFACE: Final[dict[str, LabelSpec]] = {s.surface: s for s in LEXICON}
_SURFACES_LONGEST_FIRST: Final[tuple[str, ...]] = tuple(
    sorted((s.surface for s in LEXICON), key=len, reverse=True)
)


@dataclass(slots=True)
class LabelMatch:
    """One matched label. ``raw`` is the verbatim Korean, always."""

    raw: str
    start: int
    end: int
    quantity: Quantity | None
    gloss: str
    is_event: bool
    note: str = ""


@dataclass(slots=True)
class ParseResult:
    text: str
    labels: list[LabelMatch] = field(default_factory=list)

    @property
    def quantities(self) -> list[Quantity]:
        return [m.quantity for m in self.labels if m.quantity is not None]

    def has(self, q: Quantity) -> bool:
        return q in self.quantities


def parse(text: str) -> ParseResult:
    """Extract event labels, longest-match-first with negative rules.

    Once a span is consumed by a longer surface, no shorter surface may claim
    any part of it. That single rule is what keeps 재발화 from also reporting
    an 발화 and 대피명령 from also reporting a bare 대피.
    """
    consumed: list[tuple[int, int]] = []
    out: list[LabelMatch] = []

    for surface in _SURFACES_LONGEST_FIRST:
        spec = _BY_SURFACE[surface]
        for m in re.finditer(re.escape(surface), text):
            s, e = m.span()
            if any(s < ce and cs < e for cs, ce in consumed):
                continue  # covered by a longer surface already

            if spec.context_required or spec.context_forbidden:
                window = text[max(0, s - spec.context_window): e + spec.context_window]
                if spec.context_required and not any(
                    c in window for c in spec.context_required
                ):
                    continue
                if any(c in window for c in spec.context_forbidden):
                    continue

            consumed.append((s, e))
            note = ""
            if spec.blocked_by:
                note = (
                    "shorter form accepted only because none of "
                    f"{list(spec.blocked_by)} covers this span"
                )
            out.append(
                LabelMatch(
                    raw=text[s:e],
                    start=s,
                    end=e,
                    quantity=spec.quantity,
                    gloss=spec.gloss,
                    is_event=spec.quantity is not None,
                    note=note,
                )
            )

    out.sort(key=lambda m: m.start)
    return ParseResult(text=text, labels=out)


#: Imperative evacuation instructions. These are NOT formally-declared
#: 대피명령, but an alert saying "주민들께서는 즉시 ...으로 대피하시기 바랍니다"
#: plainly directs people to leave. Counting them as orders would overstate the
#: formal record; ignoring them entirely would understate what was communicated.
#: They are therefore a separate, reported category.
_DIRECTIVE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"대피\s*(하시기|하시길|바랍니다|바람|하십시오|하세요|하시어|해\s*주)"),
    re.compile(r"(으로|로)\s*대피"),
    re.compile(r"대피\s*(하여|해)\s*주시기"),
)


def is_evacuation_directive(text: str) -> bool:
    """True when the text instructs people to evacuate, order or not.

    A formal 대피명령 is also a directive, so this is a superset. Callers
    report the two counts separately (see ``reports/LEAD_TIME_RESULTS.md``).
    """
    return any(p.search(text) for p in _DIRECTIVE_PATTERNS)


#: Times printed in Korean prose: "오후 3시 30분", "15시30분", "15:30".
_TIME_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(오전|오후)\s*(\d{1,2})\s*시\s*(\d{1,2})?\s*분?"),
    re.compile(r"(?<!\d)(\d{1,2})\s*시\s*(\d{1,2})\s*분"),
    re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)"),
)


@dataclass(slots=True)
class TimeMention:
    raw: str
    start: int
    end: int
    hour: int
    minute: int
    #: True when the source wrote 오전/오후 rather than a 24-hour clock.
    meridiem_used: bool


def find_times(text: str) -> list[TimeMention]:
    """Find wall-clock time mentions, preserving the verbatim surface form.

    Returns hour/minute only. Attaching a *date*, a *timezone* and a *role* is
    the caller's job, because those are evidentiary decisions, not parsing ones.
    """
    found: list[TimeMention] = []
    taken: list[tuple[int, int]] = []

    for pat in _TIME_PATTERNS:
        for m in pat.finditer(text):
            s, e = m.span()
            if any(s < te and ts < e for ts, te in taken):
                continue
            g = m.groups()
            if g[0] in ("오전", "오후"):
                hour = int(g[1]) % 12
                if g[0] == "오후":
                    hour += 12
                minute = int(g[2]) if g[2] else 0
                meridiem = True
            else:
                hour, minute = int(g[0]), int(g[1])
                meridiem = False
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                continue
            taken.append((s, e))
            found.append(TimeMention(text[s:e], s, e, hour, minute, meridiem))

    found.sort(key=lambda t: t.start)
    return found
