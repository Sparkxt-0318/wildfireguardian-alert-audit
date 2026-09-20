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
from enum import Enum
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


#: Instructions to move that do not use the verb 대피: 집결 (assemble),
#: 피신 (take refuge), 이동 (move to).
_DIRECTIVE_ALT: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(집결|피신)\s*(하시기|하시길|바랍니다|바람|하십시오|하세요|해\s*주)"),
    re.compile(r"(으로|로)\s*(집결|피신)"),
)


def is_evacuation_directive(text: str) -> bool:
    """True when the text instructs people to leave, order or not.

    A formal 대피명령 **is** also a directive, so this must be a superset. It
    was not: three 의성군 orders tell people to 집결 (assemble at) a school
    rather than 대피, which produced the impossible published result of 58
    orders against 57 directives. The formal-order check is therefore folded in
    explicitly rather than relied upon to fall out of the patterns.
    """
    if Quantity.EVACUATION_ORDER in parse(text).quantities:
        return True
    return any(
        p.search(text) for p in (_DIRECTIVE_PATTERNS + _DIRECTIVE_ALT)
    )


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


# ---------------------------------------------------------------------------
# Alert purpose classification
# ---------------------------------------------------------------------------
#
# An adversarial audit found that selecting "the first alert about this fire"
# by testing `"산불" in text` picks up the wrong record for four counties out
# of five. Every routine burn-ban SMS in Korea contains 산불, and so does an
# expressway-closure notice. Three counties' "first alert" turned out to be the
# same province-wide prevention boilerplate, word for word, and a fourth was a
# road closure - about 서산영덕선, the very road this package's geography module
# exists to keep out of locality inference.
#
# The fix is to classify what an alert is FOR, rather than testing whether a
# word appears in it.

#: Generic prevention/burn-ban messaging. Not a warning about an incident.
_RISK_ADVISORY: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"산불\s*위험"),
    re.compile(r"산불발생\s*위험"),
    re.compile(r"소각\s*(을|행위)?\s*(금지|자제|삼가)"),
    re.compile(r"발생하지\s*않도록"),
    re.compile(r"입산\s*(을)?\s*(자제|금지)(?!.*대피)"),
    re.compile(r"화기물?\s*소지"),
    re.compile(r"영농부산물"),
)

#: Traffic/rail impact. A distinct quantity (ROAD_IMPACT), not a fire warning.
_ROAD_IMPACT: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(전면)?\s*(차단|통제)\s*(중|합니다|하오니|예정)"),
    re.compile(r"국도\s*우회"),
    re.compile(r"우회\s*(바랍니다|하시기)"),
    re.compile(r"(열차|철도)\s*운행\s*(중단|조정)"),
    re.compile(r"(IC|TG|나들목|분기점|톨게이트)"),
)

#: Utility/infrastructure consequences of a fire. Not a warning of the fire.
_INFRASTRUCTURE: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"단수"),
    re.compile(r"정전|단전"),
    re.compile(r"통신\s*(장애|두절)"),
    re.compile(r"수돗물"),
)

#: Positive evidence that the alert concerns an actual ongoing incident.
_INCIDENT_REFERENCE: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"산불\s*확산"),
    re.compile(r"확산\s*(중|되고|됨|으로)"),
    re.compile(r"(의성|안평|안계|금성)\s*(군|면)?\s*산불"),
    re.compile(r"산불이?\s*(접근|진행|번지)"),
    re.compile(r"발화지점"),
    # 산불 발생 reports a fire; 산불 발생 위험 reports a risk of one.
    re.compile(r"산불\s*발생(?!\s*(위험|우려|예방))"),
)


class AlertPurpose(str, Enum):
    """What an emergency alert is for.

    Ordered by how directly it warns a person about an ongoing fire.
    """

    EVACUATION_ORDER = "EVACUATION_ORDER"
    EVACUATION_DIRECTIVE = "EVACUATION_DIRECTIVE"
    INCIDENT_WARNING = "INCIDENT_WARNING"
    ROAD_IMPACT = "ROAD_IMPACT"
    INFRASTRUCTURE_NOTICE = "INFRASTRUCTURE_NOTICE"
    FIRE_RISK_ADVISORY = "FIRE_RISK_ADVISORY"
    OTHER = "OTHER"

    @property
    def warns_about_an_incident(self) -> bool:
        """Is this a public warning about a fire that is actually burning?

        Road closures and utility notices are consequences of a fire and
        genuinely inform people, but they are not warnings *of* it, and a
        burn-ban advisory is not about any particular fire at all.
        """
        return self in (
            AlertPurpose.EVACUATION_ORDER,
            AlertPurpose.EVACUATION_DIRECTIVE,
            AlertPurpose.INCIDENT_WARNING,
        )


def classify_alert_purpose(text: str) -> AlertPurpose:
    """Classify an emergency alert by what it is for.

    Order matters. An evacuation order that also mentions a road closure is an
    evacuation order; a road closure that mentions a fire is not a warning.
    """
    quantities = parse(text).quantities
    if Quantity.EVACUATION_ORDER in quantities and not re.search(
        r"(해제|종료|미발령)", text
    ):
        return AlertPurpose.EVACUATION_ORDER
    if is_evacuation_directive(text) and not re.search(r"(해제|종료)", text):
        return AlertPurpose.EVACUATION_DIRECTIVE

    # Infrastructure and road consequences first: these name a fire but warn
    # about something else, and a closure notice is a ROAD_IMPACT record even
    # though it mentions 산불.
    if any(p.search(text) for p in _INFRASTRUCTURE):
        return AlertPurpose.INFRASTRUCTURE_NOTICE
    if any(p.search(text) for p in _ROAD_IMPACT):
        return AlertPurpose.ROAD_IMPACT

    # A concrete incident reference outranks generic advisory language. The
    # genuine 의성군청 warning of 15:16:22 names the ignition point AND tells
    # people to stay out of the hills; the 입산 금지 must not demote it to a
    # burn-ban notice.
    if any(p.search(text) for p in _INCIDENT_REFERENCE):
        return AlertPurpose.INCIDENT_WARNING
    if any(p.search(text) for p in _RISK_ADVISORY):
        return AlertPurpose.FIRE_RISK_ADVISORY
    return AlertPurpose.OTHER
