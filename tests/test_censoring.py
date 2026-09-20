"""Non-detection censoring. Guards FM-10, X-8."""

from wg_alert_audit.core.intervals import TimeInterval, firms_acq_to_interval
from wg_alert_audit.core.lead_time import bound_from_non_detection
from wg_alert_audit.core.model import DetectionAssumption

NON_DETECTION = firms_acq_to_interval("2025-03-22", "0300")


class TestNoAssumptionNoBound:
    """'No VIIRS detection at t1' does not mean 'no fire at t1'."""

    def test_none_assumption_yields_no_bound(self):
        assert bound_from_non_detection(None, NON_DETECTION) is None

    def test_unverified_assumption_yields_no_bound(self):
        da = DetectionAssumption(
            assumption_id="DA-CLEAR",
            description="clear-sky VIIRS detection of a >5 MW fire",
            preconditions=("cloud fraction < 0.1", "fire area > 100 m^2"),
            detection_threshold="FRP > 5 MW",
            preconditions_verified=False,
        )
        assert bound_from_non_detection(da, NON_DETECTION) is None

    def test_verified_assumption_yields_a_lower_bound(self):
        da = DetectionAssumption(
            assumption_id="DA-CLEAR",
            description="clear-sky VIIRS detection of a >5 MW fire",
            preconditions=("cloud fraction < 0.1", "fire area > 100 m^2"),
            detection_threshold="FRP > 5 MW",
            preconditions_verified=True,
            verification_notes="cloud mask and overpass geometry both checked",
        )
        bound = bound_from_non_detection(da, NON_DETECTION)
        assert bound is not None
        assert bound.upper == float("inf"), "a non-detection bounds only from below"


class TestAssumptionSemantics:
    def test_default_assumption_does_not_license_inference(self):
        da = DetectionAssumption("DA", "desc", ("p",), "threshold")
        assert not da.licenses_inference

    def test_preconditions_are_recorded_not_implied(self):
        da = DetectionAssumption(
            "DA-CLOUD", "clear sky", ("cloud fraction < 0.1",), "FRP > 5 MW"
        )
        assert da.preconditions == ("cloud fraction < 0.1",)
        assert da.detection_threshold == "FRP > 5 MW"

    def test_verification_notes_survive(self):
        da = DetectionAssumption(
            "DA", "d", ("p",), "t",
            preconditions_verified=True, verification_notes="checked GK2A cloud mask",
        )
        assert "GK2A" in da.verification_notes


class TestGk2aSpecificConfounders:
    """The GK2A FF product has documented reasons not to detect a real fire."""

    CONFOUNDERS = (
        "FF is not produced at all when the Cloud Mask product is absent",
        "daytime solar reflection lowers detection rate",
        "a 2-minute stability test suppresses single-frame detections",
        "industrial heat sources are on an explicit exclusion list",
        "SZA above 70 degrees is flagged invalid, not merely fire-free",
    )

    def test_confounders_are_enumerated_not_assumed_away(self):
        da = DetectionAssumption(
            assumption_id="DA-GK2A",
            description="GK2A FF would have detected this fire",
            preconditions=self.CONFOUNDERS,
            detection_threshold="unquantified",
            preconditions_verified=False,
        )
        assert len(da.preconditions) == 5
        assert not da.licenses_inference

    def test_an_unavailable_slot_bounds_nothing(self):
        """A missing observation slot is not evidence about fire."""
        missing_slot = TimeInterval.unknown()
        assert bound_from_non_detection(None, missing_slot) is None
