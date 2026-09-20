"""Warning lead-time computation, with the gates that make it defensible.

A lead time is a difference of two intervals, which is arithmetically trivial.
Everything hard is in deciding whether the two intervals may be subtracted at
all. This module refuses far more pairings than it accepts, and every refusal
carries its reason so that ``reports/LEAD_TIME_RESULTS.md`` can explain an
empty table.

Two quantities, never interchangeable (docs/CLAIM_RULES.md C-4):

    ALERT -> FIRST SENSOR DETECTION LEAD
    ALERT -> PHYSICAL FIRE ARRIVAL LEAD

A satellite saw smoke; that is not the fire reaching a village. The kind is
carried on the result and printed next to every number.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .geography import relate
from .intervals import TimeInterval
from .model import (
    Claim,
    DetectionAssumption,
    EvidenceClass,
    GeoRelation,
    Quantity,
    TimeRole,
)


class LeadKind(str, Enum):
    ALERT_TO_FIRST_SENSOR_DETECTION = "ALERT_TO_FIRST_SENSOR_DETECTION"
    ALERT_TO_PHYSICAL_FIRE_ARRIVAL = "ALERT_TO_PHYSICAL_FIRE_ARRIVAL"

    @property
    def label(self) -> str:
        return {
            LeadKind.ALERT_TO_FIRST_SENSOR_DETECTION:
                "alert -> first sensor detection",
            LeadKind.ALERT_TO_PHYSICAL_FIRE_ARRIVAL:
                "alert -> physical fire arrival",
        }[self]


#: Time roles admissible on the alert side of a lead-time pairing.
_ALERT_ROLES = {TimeRole.ALERT_SEND_TIME, TimeRole.REPORTED_ALERT_SEND_TIME}

#: Quantities admissible on the reference side, with the kind each produces.
_REFERENCE_KIND: dict[Quantity, LeadKind] = {
    Quantity.FIRST_SENSOR_DETECTION: LeadKind.ALERT_TO_FIRST_SENSOR_DETECTION,
    Quantity.FIRE_ARRIVAL: LeadKind.ALERT_TO_PHYSICAL_FIRE_ARRIVAL,
}


@dataclass(slots=True)
class LeadTimeResult:
    """A computed lead time, or a reasoned refusal."""

    alert_claim_id: str
    reference_claim_id: str
    computed: bool
    kind: LeadKind | None = None
    interval: TimeInterval | None = None
    geo_relation: GeoRelation = GeoRelation.UNKNOWN
    #: True when the alert side rests on news rather than the alert record.
    rests_on_reported_alert_time: bool = False
    refusal_reason: str = ""
    caveats: tuple[str, ...] = ()

    def describe(self) -> str:
        if not self.computed:
            return f"NO DEFENSIBLE ESTIMATE - {self.refusal_reason}"
        assert self.kind and self.interval
        base = f"{self.kind.label}: {self.interval.format_duration()}"
        if self.rests_on_reported_alert_time:
            base += " [rests on a REPORTED alert time, not the alert record]"
        return base


def compute(
    alert: Claim,
    reference: Claim,
    *,
    detection_assumption: DetectionAssumption | None = None,
) -> LeadTimeResult:
    """Compute a lead time, or refuse with a reason.

    Gates applied, in order:

    1. The alert claim must carry an alert time role.
    2. The reference claim must be a quantity that defines a lead kind.
    3. The reference time role must match the quantity - a sensor detection
       needs ``SENSOR_ACQUISITION_TIME``, not a publication time (X-2).
    4. Geography must be compatible at better-than-county resolution (D-006).
    5. A physical-arrival lead needs physical-arrival evidence, which a
       satellite detection is not (FM-12).
    6. Any reliance on non-detection needs a verified DetectionAssumption (FM-10).
    """
    reject = lambda why: LeadTimeResult(  # noqa: E731
        alert.claim_id, reference.claim_id, False, refusal_reason=why,
        geo_relation=relate(alert.geography, reference.geography),
    )

    # 1 - alert side
    if alert.time_role not in _ALERT_ROLES:
        return reject(
            f"alert side carries role {alert.time_role.value}, which is not an "
            "alert-send time"
        )

    # 2 - reference side defines a kind
    kind = _REFERENCE_KIND.get(reference.quantity)
    if kind is None:
        return reject(
            f"reference quantity {reference.quantity.value} does not define a "
            "lead-time kind; only first_sensor_detection and fire_arrival do"
        )

    # 3 - reference role must match its quantity
    if reference.quantity is Quantity.FIRST_SENSOR_DETECTION:
        if reference.time_role is not TimeRole.SENSOR_ACQUISITION_TIME:
            return reject(
                "a first-sensor-detection reference needs SENSOR_ACQUISITION_TIME, "
                f"not {reference.time_role.value} (X-2)"
            )
        if reference.evidence_class is not EvidenceClass.REMOTE_SENSING:
            return reject(
                "a sensor-detection reference must be REMOTE_SENSING evidence; "
                f"{reference.evidence_class.value} cannot supply an acquisition time"
            )
    else:  # physical arrival
        if reference.time_role is not TimeRole.PHYSICAL_EVENT_TIME:
            return reject(
                "a fire-arrival reference needs PHYSICAL_EVENT_TIME, not "
                f"{reference.time_role.value}; a detection time is not an "
                "arrival time (FM-12)"
            )

    # 4 - geography
    rel = relate(alert.geography, reference.geography)
    if rel is GeoRelation.INCOMPATIBLE:
        return reject(
            f"geographies are incompatible: {alert.geography.describe()} vs "
            f"{reference.geography.describe()}"
        )
    if not rel.sufficient_for_lead_time:
        return reject(
            f"geography compatibility is {rel.value}, which is insufficient. A "
            "county-wide alert cannot be paired with an arbitrary detection "
            "inside that county (D-006, FM-11)"
        )

    # 6 - censoring
    if detection_assumption is not None and not detection_assumption.licenses_inference:
        return reject(
            f"DetectionAssumption {detection_assumption.assumption_id!r} has "
            "unverified preconditions, so non-detection licenses no bound (FM-10)"
        )

    interval = reference.time_interval - alert.time_interval
    caveats: list[str] = []
    if alert.tz_assumed or reference.tz_assumed:
        caveats.append("a timezone was assumed rather than stated by the source")
    if kind is LeadKind.ALERT_TO_FIRST_SENSOR_DETECTION:
        caveats.append(
            "this is time to the first SENSOR DETECTION, not to fire arrival at "
            "any inhabited place"
        )
    if interval.is_unknown:
        caveats.append("at least one side was unbounded, so the result is unbounded")

    return LeadTimeResult(
        alert_claim_id=alert.claim_id,
        reference_claim_id=reference.claim_id,
        computed=True,
        kind=kind,
        interval=interval,
        geo_relation=rel,
        rests_on_reported_alert_time=(
            alert.time_role is TimeRole.REPORTED_ALERT_SEND_TIME
        ),
        caveats=tuple(caveats),
    )


def bound_from_non_detection(
    assumption: DetectionAssumption | None,
    non_detection_time: TimeInterval,
) -> TimeInterval | None:
    """Turn "the sensor saw nothing at t" into a bound - or refuse.

    Returns ``None`` unless an assumption is supplied *and* its preconditions
    were actually verified. Cloud cover, overpass geometry, sensitivity limits,
    smoke attenuation and sub-pixel fire size each independently break the
    inference, so the default answer is refusal (FM-10, X-8).
    """
    if assumption is None or not assumption.licenses_inference:
        return None
    return TimeInterval.after(
        __import__("datetime").datetime.fromtimestamp(
            non_detection_time.upper, __import__("datetime").timezone.utc
        )
    )
