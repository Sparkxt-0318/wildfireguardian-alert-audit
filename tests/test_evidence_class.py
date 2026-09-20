"""Evidence-class promotion rules. Guards FM-03, FM-15, X-1."""

import pytest

from wg_alert_audit.core.intervals import KST, TimeInterval, parse_kst_minute
from wg_alert_audit.core.model import (
    Claim,
    EvidenceClass,
    Geography,
    Quantity,
    TimeRole,
)


def make(evidence_class: EvidenceClass, role: TimeRole) -> Claim:
    return Claim(
        claim_id="C",
        incident_id="INC-1",
        quantity=Quantity.FIRST_PUBLIC_WARNING,
        time_interval=parse_kst_minute("2025-03-22", "15:30"),
        time_role=role,
        geography=Geography(si_gun="영덕군"),
        evidence_class=evidence_class,
        source_id="S",
        raw_text="원문 텍스트",
    )


class TestTertiaryCannotBecomePrimary:
    def test_wikipedia_cannot_supply_an_alert_send_time(self):
        with pytest.raises(ValueError, match="may not supply"):
            make(EvidenceClass.TERTIARY, TimeRole.ALERT_SEND_TIME)

    def test_wikipedia_cannot_supply_a_sensor_acquisition_time(self):
        with pytest.raises(ValueError):
            make(EvidenceClass.TERTIARY, TimeRole.SENSOR_ACQUISITION_TIME)

    def test_wikipedia_may_report_an_alert_time(self):
        c = make(EvidenceClass.TERTIARY, TimeRole.REPORTED_ALERT_SEND_TIME)
        assert c.evidence_class is EvidenceClass.TERTIARY


class TestNewsCannotBecomeTheAlertRecord:
    def test_news_cannot_supply_an_alert_send_time(self):
        with pytest.raises(ValueError):
            make(EvidenceClass.NEWS_REPORT, TimeRole.ALERT_SEND_TIME)

    def test_quoting_an_official_does_not_promote_a_news_article(self):
        """The rule is about the artifact, not about who is quoted in it."""
        assert not EvidenceClass.NEWS_REPORT.can_supply(TimeRole.ALERT_SEND_TIME)

    def test_news_may_report_an_alert_time(self):
        c = make(EvidenceClass.NEWS_REPORT, TimeRole.REPORTED_ALERT_SEND_TIME)
        assert c.time_role is TimeRole.REPORTED_ALERT_SEND_TIME


class TestAgencyArticleIsNotASensor:
    def test_official_retrospective_cannot_supply_acquisition_time(self):
        """A NASA/agency article without an acquisition timestamp is not a sensor."""
        with pytest.raises(ValueError):
            make(EvidenceClass.OFFICIAL_RETROSPECTIVE, TimeRole.SENSOR_ACQUISITION_TIME)

    def test_official_retrospective_cannot_supply_alert_send_time(self):
        """Even an official report only *reports* what the alert system did."""
        with pytest.raises(ValueError):
            make(EvidenceClass.OFFICIAL_RETROSPECTIVE, TimeRole.ALERT_SEND_TIME)

    def test_only_remote_sensing_supplies_acquisition_time(self):
        suppliers = [
            e for e in EvidenceClass if e.can_supply(TimeRole.SENSOR_ACQUISITION_TIME)
        ]
        assert suppliers == [EvidenceClass.REMOTE_SENSING]

    def test_only_primary_operational_supplies_alert_send_time(self):
        suppliers = [
            e for e in EvidenceClass if e.can_supply(TimeRole.ALERT_SEND_TIME)
        ]
        assert suppliers == [EvidenceClass.PRIMARY_OPERATIONAL]


class TestRawTextIsMandatory:
    def test_claim_without_raw_text_is_refused(self):
        with pytest.raises(ValueError, match="raw_text"):
            Claim(
                claim_id="C",
                incident_id="INC-1",
                quantity=Quantity.IGNITION,
                time_interval=TimeInterval.unknown(),
                time_role=TimeRole.REPORT_TIME,
                geography=Geography(),
                evidence_class=EvidenceClass.NEWS_REPORT,
                source_id="S",
                raw_text="   ",
            )


class TestStrengthOrdering:
    def test_primary_and_remote_sensing_outrank_retrospective(self):
        assert (
            EvidenceClass.PRIMARY_OPERATIONAL.strength
            > EvidenceClass.OFFICIAL_RETROSPECTIVE.strength
        )

    def test_retrospective_outranks_news_which_outranks_tertiary(self):
        assert (
            EvidenceClass.OFFICIAL_RETROSPECTIVE.strength
            > EvidenceClass.NEWS_REPORT.strength
            > EvidenceClass.TERTIARY.strength
        )

    def test_strength_does_not_license_promotion(self):
        """Being stronger does not let a class supply a role it cannot."""
        assert EvidenceClass.OFFICIAL_RETROSPECTIVE.strength > EvidenceClass.NEWS_REPORT.strength
        assert not EvidenceClass.OFFICIAL_RETROSPECTIVE.can_supply(TimeRole.ALERT_SEND_TIME)
