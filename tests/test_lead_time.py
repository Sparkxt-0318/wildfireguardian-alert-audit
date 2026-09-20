"""Lead-time gates. Guards FM-11, FM-12, D-006, C-4."""

from wg_alert_audit.core.intervals import firms_acq_to_interval, parse_kst_minute
from wg_alert_audit.core.lead_time import LeadKind, compute
from wg_alert_audit.core.model import (
    Claim,
    DetectionAssumption,
    EvidenceClass,
    Geography,
    GeoRelation,
    Quantity,
    TimeRole,
)

EUP = Geography(province="경상북도", si_gun="영덕군", eup_myeon_dong="지품면")
EUP_OTHER = Geography(province="경상북도", si_gun="영덕군", eup_myeon_dong="강구면")
COUNTY = Geography(province="경상북도", si_gun="영덕군")
OTHER_COUNTY = Geography(province="경상북도", si_gun="의성군")

ALERT_IV = parse_kst_minute("2025-03-22", "15:30")
DET_IV = firms_acq_to_interval("2025-03-22", "0700")  # 07:00 UTC = 16:00 KST


def claim(cid, quantity, interval, role, geo, ec) -> Claim:
    return Claim(cid, "INC-1", quantity, interval, role, geo, ec, "S", "원문")


def alert(geo=EUP, role=TimeRole.ALERT_SEND_TIME,
          ec=EvidenceClass.PRIMARY_OPERATIONAL) -> Claim:
    return claim("A", Quantity.FIRST_PUBLIC_WARNING, ALERT_IV, role, geo, ec)


def detection(geo=EUP, role=TimeRole.SENSOR_ACQUISITION_TIME,
              ec=EvidenceClass.REMOTE_SENSING) -> Claim:
    return claim("D", Quantity.FIRST_SENSOR_DETECTION, DET_IV, role, geo, ec)


class TestGeographyGate:
    """D-006 / FM-11: a county-wide alert does not locate a fire front."""

    def test_eup_level_pairing_is_allowed(self):
        assert compute(alert(EUP), detection(EUP)).computed

    def test_county_only_pairing_is_refused(self):
        r = compute(alert(COUNTY), detection(COUNTY))
        assert not r.computed
        assert "SAME_COUNTY" in r.refusal_reason

    def test_different_eup_in_same_county_is_refused(self):
        assert not compute(alert(EUP), detection(EUP_OTHER)).computed

    def test_different_counties_are_refused(self):
        r = compute(alert(EUP), detection(geo=OTHER_COUNTY))
        assert not r.computed
        assert "incompatible" in r.refusal_reason.lower()

    def test_refusal_records_the_relation(self):
        r = compute(alert(COUNTY), detection(COUNTY))
        assert r.geo_relation is GeoRelation.SAME_COUNTY


class TestDetectionIsNotArrival:
    """FM-12 / C-4: the two lead kinds are different quantities."""

    def test_sensor_detection_cannot_stand_in_for_arrival(self):
        arrival = claim(
            "R", Quantity.FIRE_ARRIVAL, DET_IV,
            TimeRole.SENSOR_ACQUISITION_TIME, EUP, EvidenceClass.REMOTE_SENSING,
        )
        r = compute(alert(), arrival)
        assert not r.computed
        assert "PHYSICAL_EVENT_TIME" in r.refusal_reason

    def test_detection_lead_is_labelled_as_such(self):
        r = compute(alert(), detection())
        assert r.kind is LeadKind.ALERT_TO_FIRST_SENSOR_DETECTION
        assert "first sensor detection" in r.describe()

    def test_detection_lead_carries_an_explicit_caveat(self):
        r = compute(alert(), detection())
        assert any("not to fire arrival" in c for c in r.caveats)

    def test_the_two_kinds_have_distinct_labels(self):
        assert (
            LeadKind.ALERT_TO_FIRST_SENSOR_DETECTION.label
            != LeadKind.ALERT_TO_PHYSICAL_FIRE_ARRIVAL.label
        )


class TestRoleGates:
    def test_publication_time_cannot_be_the_alert_side(self):
        a = claim("A", Quantity.FIRST_PUBLIC_WARNING, ALERT_IV,
                  TimeRole.PUBLICATION_TIME, EUP, EvidenceClass.NEWS_REPORT)
        assert not compute(a, detection()).computed

    def test_reported_alert_time_is_allowed_but_flagged(self):
        a = alert(role=TimeRole.REPORTED_ALERT_SEND_TIME, ec=EvidenceClass.NEWS_REPORT)
        r = compute(a, detection())
        assert r.computed
        assert r.rests_on_reported_alert_time
        assert "REPORTED alert time" in r.describe()

    def test_a_non_sensor_class_cannot_supply_the_detection_side(self):
        d = claim("D", Quantity.FIRST_SENSOR_DETECTION, DET_IV,
                  TimeRole.SENSOR_ACQUISITION_TIME, EUP, EvidenceClass.REMOTE_SENSING)
        assert compute(alert(), d).computed

    def test_containment_is_not_a_lead_time_reference(self):
        c = claim("D", Quantity.CONTAINMENT, DET_IV,
                  TimeRole.REPORT_TIME, EUP, EvidenceClass.OFFICIAL_RETROSPECTIVE)
        r = compute(alert(), c)
        assert not r.computed
        assert "does not define a" in r.refusal_reason


class TestArithmetic:
    def test_interval_is_a_range_not_a_point(self):
        r = compute(alert(), detection())
        assert r.interval is not None and not r.interval.is_point

    def test_bounds_are_correct(self):
        """Alert [15:30:00,15:30:59] KST, detection [16:00:00,16:00:59] KST."""
        r = compute(alert(), detection())
        assert r.interval.lower == 29 * 60 + 1
        assert r.interval.upper == 30 * 60 + 59

    def test_duration_formats_as_an_interval(self):
        assert compute(alert(), detection()).interval.format_duration() == "[0h29m, 0h30m]"


class TestDetectionAssumptionGate:
    """FM-10: non-detection licenses nothing without a verified model."""

    def test_unverified_assumption_blocks_the_computation(self):
        da = DetectionAssumption("DA-1", "clear-sky", ("no cloud",), "FRP>5MW",
                                 preconditions_verified=False)
        r = compute(alert(), detection(), detection_assumption=da)
        assert not r.computed
        assert "unverified preconditions" in r.refusal_reason

    def test_verified_assumption_permits_it(self):
        da = DetectionAssumption("DA-1", "clear-sky", ("no cloud",), "FRP>5MW",
                                 preconditions_verified=True,
                                 verification_notes="cloud mask checked")
        assert compute(alert(), detection(), detection_assumption=da).computed

    def test_assumption_reports_whether_it_licenses_inference(self):
        assert not DetectionAssumption("D", "d", (), "t").licenses_inference


class TestRefusalsAreInformative:
    def test_refusal_describes_as_no_defensible_estimate(self):
        r = compute(alert(COUNTY), detection(COUNTY))
        assert r.describe().startswith("NO DEFENSIBLE ESTIMATE")

    def test_every_refusal_has_a_reason(self):
        for a, d in (
            (alert(COUNTY), detection(COUNTY)),
            (alert(EUP), detection(geo=OTHER_COUNTY)),
        ):
            assert compute(a, d).refusal_reason
