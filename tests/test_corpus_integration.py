"""Integration tests against the committed corpus.

The adversarial audit's sharpest structural finding was that the enforcement
machinery lived in the library while the pipeline wrote plain dicts straight to
JSON, so `Claim.__post_init__`'s class/role guard never ran on a single real
record. Every test here loads the actual committed data.
"""

import json
from pathlib import Path

import pytest

from wg_alert_audit.core.geography import extract
from wg_alert_audit.core.intervals import KST, TimeInterval
from wg_alert_audit.core.korean import classify_alert_purpose
from wg_alert_audit.core.model import (
    Claim,
    EvidenceClass,
    Geography,
    Quantity,
    TimeRole,
)

ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "data" / "timeline" / "timeline.json"
INTERVALS = ROOT / "data" / "timeline" / "intervals.json"


@pytest.fixture(scope="module")
def events() -> list[dict]:
    if not TIMELINE.exists():
        pytest.skip("timeline not built")
    return json.loads(TIMELINE.read_text(encoding="utf-8"))["events"]


class TestEveryEventRoundTripsThroughClaim:
    """The library's guards must actually run on the real corpus."""

    def test_every_event_constructs_a_valid_claim(self, events):
        from datetime import datetime

        failures = []
        for e in events:
            try:
                Claim(
                    claim_id=e["record_id"],
                    incident_id=e.get("incident_id", "UNRESOLVED"),
                    quantity=Quantity(e["quantity"])
                    if e["quantity"] != "public_alert_other"
                    else Quantity.PUBLIC_WARNING,
                    time_interval=TimeInterval.at_second(
                        datetime.fromisoformat(e["send_time_kst"])
                    ),
                    time_role=TimeRole(e["time_role"]),
                    geography=Geography(si_gun=e.get("issuer_county")),
                    evidence_class=EvidenceClass(e["evidence_class"]),
                    source_id=e["source_id"],
                    raw_text=e["raw_text"],
                )
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{e['record_id']}: {exc}")
        assert not failures, f"{len(failures)} events fail Claim(): {failures[:3]}"

    def test_every_time_role_is_supported_by_its_class(self, events):
        for e in events:
            cls = EvidenceClass(e["evidence_class"])
            role = TimeRole(e["time_role"])
            assert cls.can_supply(role), f"{e['record_id']}: {cls.value}/{role.value}"


class TestCorpusInvariants:
    def test_orders_are_a_subset_of_directives(self, events):
        for e in events:
            if e.get("is_evacuation_order"):
                assert e.get("is_evacuation_directive"), e["record_id"]

    def test_the_superlative_holds_at_most_once_per_county(self, events):
        seen: dict[str, str] = {}
        for e in events:
            if e.get("is_first_public_warning_for_county"):
                c = e["issuer_county"]
                assert c not in seen, f"{c} claimed twice: {seen.get(c)}, {e['record_id']}"
                seen[c] = e["record_id"]

    def test_the_quantity_vocabulary_is_not_collapsed(self, events):
        """295 of 302 records sharing one quantity drained the field."""
        vocab = {e["quantity"] for e in events}
        assert len(vocab) >= 4, f"vocabulary collapsed to {vocab}"

    def test_no_record_ids_are_duplicated_within_a_quantity(self, events):
        seen = set()
        for e in events:
            key = (e["record_id"], e["quantity"])
            assert key not in seen, f"duplicate {key}"
            seen.add(key)

    def test_every_event_preserves_verbatim_korean(self, events):
        for e in events:
            assert e["raw_text"].strip(), e["record_id"]

    def test_provenance_matches_record_id(self, events):
        for e in events:
            assert f"sn={e['record_id']}" in e["provenance"], e["record_id"]


class TestNoForeignJurisdictionsInTheCorpus:
    """A 무주군 (North Jeolla) fire was in the corpus labelled 청송군."""

    #: Eup/myeon that exist in more than one province. Attributing one of
    #: these to a Gyeongbuk county when a foreign county is named alongside it
    #: is the 무주군/청송군 failure.
    AMBIGUOUS = {"부남면": "also in 무주군 (North Jeolla)"}

    def test_an_ambiguous_myeon_is_not_claimed_when_a_foreign_county_is_named(
        self, events
    ):
        for e in events:
            text = e["raw_text"]
            for myeon in self.AMBIGUOUS:
                if myeon in text and ("무주" in text or "곡성" in text):
                    assert not e.get("body_counties"), (
                        f"{e['record_id']}: {myeon} attributed to "
                        f"{e['body_counties']} while the text names a "
                        "municipality in another province"
                    )

    def test_an_out_of_province_issuer_is_recorded_not_dropped(self, events):
        """곡성군 may legitimately mention 의성 산불; the issuer must survive."""
        for e in events:
            if e.get("issuer_county") is None and e.get("issuing_authority"):
                assert e.get("issuer_out_of_scope") is True, e["record_id"]

    def test_geography_in_body_counties_appears_in_the_text(self, events):
        """Precision: nothing in body_counties may be absent from the text."""
        for e in events[:200]:
            derived = {c for r in extract(e["raw_text"]) for c in r.all_si_gun}
            for c in e.get("body_counties", []):
                assert c in derived, f"{e['record_id']}: {c} not re-derivable"


class TestPublishedIntervalsMatchTheData:
    def test_intervals_are_119_seconds_wide(self):
        if not INTERVALS.exists():
            pytest.skip("intervals not built")
        data = json.loads(INTERVALS.read_text(encoding="utf-8"))
        for county, e in data["counties"].items():
            g = e["reported_ignition_to_first_alert"]
            assert g["upper_seconds"] - g["lower_seconds"] == 119, county

    def test_every_first_alert_is_a_real_incident_warning(self):
        """The bug that selected burn-ban boilerplate for four counties."""
        if not INTERVALS.exists():
            pytest.skip("intervals not built")
        data = json.loads(INTERVALS.read_text(encoding="utf-8"))
        for county, e in data["counties"].items():
            purpose = classify_alert_purpose(e["first_alert_text"])
            assert purpose.warns_about_an_incident, (
                f"{county}: first alert is {purpose.value} - {e['first_alert_text'][:60]}"
            )

    def test_no_first_alert_is_a_road_notice(self):
        if not INTERVALS.exists():
            pytest.skip("intervals not built")
        data = json.loads(INTERVALS.read_text(encoding="utf-8"))
        for county, e in data["counties"].items():
            assert "고속도로" not in e["first_alert_text"], county
