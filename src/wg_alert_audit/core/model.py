"""The audit's type system: evidence classes, time roles, access status.

These enums are not labels; they carry the rules. ``EvidenceClass`` refuses
promotion, ``TimeRole`` refuses substitution, ``AccessStatus`` refuses to let a
network failure masquerade as data absence.

See ``docs/EVIDENCE_MODEL.md``, ``docs/TIME_ONTOLOGY.md``,
``docs/ACCESS_STATUS_MODEL.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final

from .intervals import TimeInterval


class EvidenceClass(str, Enum):
    """What kind of thing an artifact *is*. A property of the artifact."""

    PRIMARY_OPERATIONAL = "PRIMARY_OPERATIONAL"
    REMOTE_SENSING = "REMOTE_SENSING"
    OFFICIAL_RETROSPECTIVE = "OFFICIAL_RETROSPECTIVE"
    NEWS_REPORT = "NEWS_REPORT"
    TERTIARY = "TERTIARY"
    DERIVED = "DERIVED"

    @property
    def strength(self) -> int:
        """Ordering for "best available evidence", *not* for promotion."""
        return _STRENGTH[self]

    def can_supply(self, role: "TimeRole") -> bool:
        """Whether this class may supply a timestamp in this role.

        This is the guard against FM-03, FM-04 and FM-15: a news article can
        report that an alert was sent, but it cannot *be* the alert record, and
        an agency blog post is not a sensor.
        """
        return role in _CLASS_CAN_SUPPLY[self]


_STRENGTH: Final[dict[EvidenceClass, int]] = {
    EvidenceClass.PRIMARY_OPERATIONAL: 5,
    EvidenceClass.REMOTE_SENSING: 5,
    EvidenceClass.OFFICIAL_RETROSPECTIVE: 3,
    EvidenceClass.NEWS_REPORT: 2,
    EvidenceClass.TERTIARY: 1,
    EvidenceClass.DERIVED: 0,
}


class TimeRole(str, Enum):
    """What a timestamp *means*. Never silently substituted."""

    PHYSICAL_EVENT_TIME = "PHYSICAL_EVENT_TIME"
    ALERT_SEND_TIME = "ALERT_SEND_TIME"
    REPORTED_ALERT_SEND_TIME = "REPORTED_ALERT_SEND_TIME"
    SENSOR_ACQUISITION_TIME = "SENSOR_ACQUISITION_TIME"
    PROCESSING_TIME = "PROCESSING_TIME"
    PUBLICATION_TIME = "PUBLICATION_TIME"
    REPORT_TIME = "REPORT_TIME"
    RETRIEVAL_TIME = "RETRIEVAL_TIME"


#: Which classes may supply which roles. Absence is a hard refusal.
_CLASS_CAN_SUPPLY: Final[dict[EvidenceClass, frozenset[TimeRole]]] = {
    # Only the operational system itself can state when it acted.
    EvidenceClass.PRIMARY_OPERATIONAL: frozenset(
        {
            TimeRole.ALERT_SEND_TIME,
            TimeRole.PHYSICAL_EVENT_TIME,
            TimeRole.REPORT_TIME,
            TimeRole.PUBLICATION_TIME,
            TimeRole.RETRIEVAL_TIME,
        }
    ),
    # Only an actual sensor product carries an acquisition time.
    EvidenceClass.REMOTE_SENSING: frozenset(
        {
            TimeRole.SENSOR_ACQUISITION_TIME,
            TimeRole.PROCESSING_TIME,
            TimeRole.RETRIEVAL_TIME,
        }
    ),
    # A retrospective report assigns times to events; it did not observe them.
    # Notably it may NOT supply ALERT_SEND_TIME - that needs the alert record.
    EvidenceClass.OFFICIAL_RETROSPECTIVE: frozenset(
        {
            TimeRole.REPORT_TIME,
            TimeRole.REPORTED_ALERT_SEND_TIME,
            TimeRole.PUBLICATION_TIME,
            TimeRole.RETRIEVAL_TIME,
        }
    ),
    # Journalism reports; it does not transmit alerts or operate sensors.
    EvidenceClass.NEWS_REPORT: frozenset(
        {
            TimeRole.REPORTED_ALERT_SEND_TIME,
            TimeRole.REPORT_TIME,
            TimeRole.PUBLICATION_TIME,
            TimeRole.RETRIEVAL_TIME,
        }
    ),
    # Aggregation. Discovery aid only.
    EvidenceClass.TERTIARY: frozenset(
        {
            TimeRole.REPORTED_ALERT_SEND_TIME,
            TimeRole.PUBLICATION_TIME,
            TimeRole.RETRIEVAL_TIME,
        }
    ),
    # Our own calculations.
    EvidenceClass.DERIVED: frozenset({TimeRole.REPORT_TIME, TimeRole.RETRIEVAL_TIME}),
}


class AccessStatus(str, Enum):
    """The outcome of one acquisition attempt. See docs/ACCESS_STATUS_MODEL.md."""

    RETRIEVED = "RETRIEVED"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    API_KEY_REQUIRED = "API_KEY_REQUIRED"
    REGISTRATION_REQUIRED = "REGISTRATION_REQUIRED"
    ENDPOINT_MIGRATED = "ENDPOINT_MIGRATED"
    MANUAL_DOWNLOAD_AVAILABLE = "MANUAL_DOWNLOAD_AVAILABLE"
    TEMPORARY_NETWORK_FAILURE = "TEMPORARY_NETWORK_FAILURE"
    SERVER_ERROR = "SERVER_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_FOUND = "NOT_FOUND"
    FORMAT_UNSUPPORTED = "FORMAT_UNSUPPORTED"
    NO_RELEVANT_RECORD = "NO_RELEVANT_RECORD"
    UNKNOWN = "UNKNOWN"

    @property
    def implies_data_absent(self) -> bool:
        """Does this outcome license *any* inference about data existence?

        Exactly one status does, and only because it requires a successful
        query as a precondition. This property exists so that the answer is
        written down once (FM-01).
        """
        return self is AccessStatus.NO_RELEVANT_RECORD

    @property
    def is_gated(self) -> bool:
        """Data plausibly exists but this agent cannot reach it automatically."""
        return self in _GATED


_GATED: Final[frozenset[AccessStatus]] = frozenset(
    {
        AccessStatus.AUTHENTICATION_REQUIRED,
        AccessStatus.API_KEY_REQUIRED,
        AccessStatus.REGISTRATION_REQUIRED,
        AccessStatus.MANUAL_DOWNLOAD_AVAILABLE,
        AccessStatus.ACCESS_DENIED,
    }
)


class GapStatus(str, Enum):
    """Aggregate status of a *quantity*, across all attempts."""

    AVAILABLE = "AVAILABLE"
    PARTIALLY_AVAILABLE = "PARTIALLY_AVAILABLE"
    CREDENTIAL_REQUIRED = "CREDENTIAL_REQUIRED"
    MANUAL_DOWNLOAD_REQUIRED = "MANUAL_DOWNLOAD_REQUIRED"
    NOT_RETRIEVED = "NOT_RETRIEVED"
    OBSERVATION_DOES_NOT_EXIST = "OBSERVATION_DOES_NOT_EXIST"
    UNKNOWN = "UNKNOWN"


class GeoRelation(str, Enum):
    """How two geographies relate, for pairing purposes."""

    EXACT_LOCALITY = "EXACT_LOCALITY"
    SAME_EUP_MYEON = "SAME_EUP_MYEON"
    SAME_COUNTY = "SAME_COUNTY"
    SENSOR_FOOTPRINT_INTERSECTS = "SENSOR_FOOTPRINT_INTERSECTS"
    NEARBY = "NEARBY"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"

    @property
    def sufficient_for_lead_time(self) -> bool:
        """D-006: SAME_COUNTY is recorded but gated out (FM-11).

        A county-wide alert says nothing about where within ~1000 km2 the fire
        front was. Pairing it with an arbitrary in-county detection would
        manufacture a lead time out of administrative geography.
        """
        return self in _GEO_SUFFICIENT


_GEO_SUFFICIENT: Final[frozenset[GeoRelation]] = frozenset(
    {
        GeoRelation.EXACT_LOCALITY,
        GeoRelation.SAME_EUP_MYEON,
        GeoRelation.SENSOR_FOOTPRINT_INTERSECTS,
    }
)


class Quantity(str, Enum):
    """The distinct quantities this audit refuses to conflate."""

    IGNITION = "ignition"
    REPORTED_IGNITION = "reported_ignition"
    FIRST_SENSOR_DETECTION = "first_sensor_detection"
    FIRST_OFFICIAL_AWARENESS = "first_official_awareness"
    #: The earliest public warning about an incident for a given locality.
    #: A superlative, so it may hold for at most one record per locality.
    FIRST_PUBLIC_WARNING = "first_public_warning"
    #: Any subsequent public warning about the same incident. Added because
    #: stamping every alert FIRST_PUBLIC_WARNING asserted the superlative
    #: hundreds of times and drained the field of information.
    PUBLIC_WARNING = "public_warning"
    FIRE_ARRIVAL = "fire_arrival"
    ROAD_IMPACT = "road_impact"
    EVACUATION_ORDER = "evacuation_order"
    CONTAINMENT = "containment"
    RE_IGNITION = "re_ignition"


class EdgeType(str, Enum):
    """Typed edges in the source-upgrade graph (docs/EVIDENCE_MODEL.md)."""

    CITES = "CITES"
    QUOTES = "QUOTES"
    REPRODUCES = "REPRODUCES"
    SUPERSEDES = "SUPERSEDES"
    CONTRADICTS = "CONTRADICTS"
    CORROBORATES = "CORROBORATES"


@dataclass(frozen=True, slots=True)
class Geography:
    """Normalised Korean administrative geography.

    Every level is optional because sources are partial. ``raw`` keeps the
    original string so that a normalisation can always be re-checked by a human.
    """

    province: str | None = None
    si_gun: str | None = None
    eup_myeon_dong: str | None = None
    ri: str | None = None
    named_place: str | None = None
    road: str | None = None
    facility: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    #: Radius in km within which the true location is believed to lie.
    spatial_uncertainty_km: float | None = None
    raw: str = ""

    @property
    def finest_level(self) -> str:
        for level in ("ri", "eup_myeon_dong", "si_gun", "province"):
            if getattr(self, level):
                return level
        return "unknown"

    def describe(self) -> str:
        parts = [
            p
            for p in (self.province, self.si_gun, self.eup_myeon_dong, self.ri)
            if p
        ]
        return " ".join(parts) if parts else (self.named_place or "unknown")


@dataclass(frozen=True, slots=True)
class DetectionAssumption:
    """An explicit, named model licensing inference from *non*-detection.

    Without one of these, the system refuses to turn "no VIIRS detection at t1"
    into "no fire at t1" (FM-10). Cloud cover, overpass geometry, sensitivity
    limits, smoke attenuation and sub-pixel fire size all break that inference,
    so the assumption has to be stated and owned, not implied.
    """

    assumption_id: str
    description: str
    #: What must hold for the non-detection to be informative.
    preconditions: tuple[str, ...]
    #: Minimum fire size / FRP the sensor is assumed able to detect.
    detection_threshold: str
    #: Whether those preconditions were actually verified for this case.
    preconditions_verified: bool = False
    verification_notes: str = ""

    @property
    def licenses_inference(self) -> bool:
        return self.preconditions_verified


@dataclass(slots=True)
class Claim:
    """The atomic unit of the audit."""

    claim_id: str
    incident_id: str  # or "UNRESOLVED"
    quantity: Quantity
    time_interval: TimeInterval
    time_role: TimeRole
    geography: Geography
    evidence_class: EvidenceClass
    source_id: str
    raw_text: str
    tz_assumed: bool = False
    geo_relation_notes: str = ""
    confidence_notes: str = ""
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_class.can_supply(self.time_role):
            raise ValueError(
                f"evidence class {self.evidence_class.value} may not supply a "
                f"timestamp in role {self.time_role.value} "
                f"(docs/EVIDENCE_MODEL.md promotion rules)"
            )
        if not self.raw_text.strip():
            raise ValueError("raw_text is mandatory: the verbatim source span")
