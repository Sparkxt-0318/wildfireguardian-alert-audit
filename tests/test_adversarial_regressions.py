"""Regressions for the adversarial audit's findings.

The strings are verbatim from the harvested corpus. Each test exists because
a hostile reviewer found the pipeline getting it wrong.
"""

import json
from pathlib import Path

import pytest

from wg_alert_audit.core.geography import attribute, extract_from_clause
from wg_alert_audit.core.intervals import KST, TimeInterval, parse_kst_minute
from wg_alert_audit.core.korean import (
    AlertPurpose,
    classify_alert_purpose,
    is_evacuation_directive,
    parse,
)
from wg_alert_audit.core.model import Quantity

ROOT = Path(__file__).resolve().parents[1]


class TestC1_AlertPurposeSelectsRealWarnings:
    """`"산불" in text` selected boilerplate for four counties out of five."""

    BOILERPLATE = (
        "도내 산불이 많이 발생중이며 건조한 날씨와 바람으로 산불위험이 매우 높으니, "
        "소각을 금지하여 주시고 산불이 발생하지 않도록 주의하여 주시기 바랍니다."
    )
    ROAD_NOTICE = (
        "고속도로 인근 산불로 서산영덕선 북의성IC~영덕TG 양방향 전면차단 중이오니 "
        "국도우회 바랍니다."
    )
    REAL_WARNING = (
        "오늘 11:25 안평면 괴산리 산61(발화지점) 산불 발생. 입산 금지, 창문개방 자제, "
        "인근 주민과 등산객은 안전사고에 주의하세요."
    )

    def test_burn_ban_boilerplate_is_not_a_warning(self):
        assert classify_alert_purpose(self.BOILERPLATE) is AlertPurpose.FIRE_RISK_ADVISORY
        assert not classify_alert_purpose(self.BOILERPLATE).warns_about_an_incident

    def test_expressway_closure_is_not_a_warning(self):
        """And note which expressway: the one X-3 exists to handle."""
        assert classify_alert_purpose(self.ROAD_NOTICE) is AlertPurpose.ROAD_IMPACT
        assert not classify_alert_purpose(self.ROAD_NOTICE).warns_about_an_incident

    def test_a_real_incident_warning_is_one(self):
        p = classify_alert_purpose(self.REAL_WARNING)
        assert p is AlertPurpose.INCIDENT_WARNING
        assert p.warns_about_an_incident

    def test_stay_out_of_the_hills_does_not_demote_a_real_warning(self):
        """입산 금지 appears in both the boilerplate and the genuine warning."""
        assert "입산 금지" in self.REAL_WARNING
        assert classify_alert_purpose(self.REAL_WARNING).warns_about_an_incident

    def test_utility_notice_is_not_a_warning(self):
        t = "산불 발생으로 인해 가압장이 정전되어 수돗물이 일시적으로 단수됨을 알려드립니다"
        assert classify_alert_purpose(t) is AlertPurpose.INFRASTRUCTURE_NOTICE

    def test_risk_of_a_fire_is_not_a_report_of_one(self):
        t = "건조한 날씨와 강풍이 계속되어 산불 발생 위험이 높으니 소각을 자제"
        assert classify_alert_purpose(t) is AlertPurpose.FIRE_RISK_ADVISORY

    def test_an_evacuation_order_outranks_everything(self):
        t = "(대피명령 발령) 지품면 옥류리 주민께서는 산불로 도로가 통제되오니 대피해 주시기바랍니다"
        assert classify_alert_purpose(t) is AlertPurpose.EVACUATION_ORDER


class TestC2_IntervalWidthIsNotTwoSeconds:
    """The published '±2 s' was the seconds field, not the width."""

    def test_the_hull_is_119_seconds_wide(self):
        a = parse_kst_minute("2025-03-22", "11:24")
        b = parse_kst_minute("2025-03-22", "11:25")
        assert a.hull(b).width_seconds == 119

    def test_a_derived_interval_inherits_that_width(self):
        from datetime import datetime

        hull = parse_kst_minute("2025-03-22", "11:24").hull(
            parse_kst_minute("2025-03-22", "11:25")
        )
        alert = TimeInterval.at_second(
            datetime(2025, 3, 22, 12, 50, 32, tzinfo=KST)
        )
        assert (alert - hull).width_seconds == 119

    def test_published_intervals_are_119s_wide(self):
        p = ROOT / "data" / "timeline" / "intervals.json"
        if not p.exists():
            pytest.skip("intervals not built")
        data = json.loads(p.read_text(encoding="utf-8"))
        for county, e in data["counties"].items():
            g = e["reported_ignition_to_first_alert"]
            width = g["upper_seconds"] - g["lower_seconds"]
            assert width == 119, f"{county}: width {width}s, expected 119s"


class TestM6_CrossProvinceCollision:
    """Eup/myeon names are not nationally unique."""

    JEONBUK = "오늘 21:22 무주군 부남면 대소리 819-1번지 인근 산불 발생"

    def test_a_jeonbuk_myeon_is_not_assigned_to_gyeongbuk(self):
        assert extract_from_clause(self.JEONBUK).all_si_gun == []

    def test_attribute_refuses_it(self):
        assert attribute(self.JEONBUK) is None

    def test_the_refusal_names_the_foreign_municipality(self):
        assert "무주군" in extract_from_clause(self.JEONBUK).note

    def test_the_same_myeon_in_scope_still_resolves(self):
        r = extract_from_clause("청송군 부남면 주민 대피")
        assert r.all_si_gun == ["청송군"] and "부남면" in r.all_eup_myeon

    def test_an_unqualified_in_scope_myeon_still_resolves(self):
        assert extract_from_clause("안평면 괴산리 산불").all_si_gun == ["의성군"]


class TestMinor1_LiftingAnOrderIsNotIssuingOne:
    def test_rescinding_an_evacuation_order_is_not_an_order(self):
        t = "영덕군 관내 주불진화로 대피명령을 해제하오니 안심하시기 바랍니다"
        assert classify_alert_purpose(t) is not AlertPurpose.EVACUATION_ORDER

    def test_it_is_not_a_directive_either(self):
        t = "영덕군 관내 주불진화로 대피명령을 해제하오니"
        assert classify_alert_purpose(t) is not AlertPurpose.EVACUATION_DIRECTIVE


class TestM10_DirectivesAreASupersetOfOrders:
    """58 orders against 57 directives was arithmetically impossible."""

    ASSEMBLE = (
        "(긴급대피명령 발령) 산불 확산으로 단촌면 전주민과 등산객은 "
        "단촌초등학교 운동장으로 집결하시기바랍니다"
    )

    def test_an_order_using_집결_is_still_a_directive(self):
        assert Quantity.EVACUATION_ORDER in parse(self.ASSEMBLE).quantities
        assert is_evacuation_directive(self.ASSEMBLE)

    def test_every_formal_order_is_a_directive(self):
        for t in (
            "(대피명령 발령) 주민은 대피하시기 바랍니다",
            "(긴급대피명령 발령) 운동장으로 집결하시기바랍니다",
            "대피령이 발령되었습니다",
        ):
            if Quantity.EVACUATION_ORDER in parse(t).quantities:
                assert is_evacuation_directive(t), t

    def test_the_invariant_holds_on_the_built_corpus(self):
        p = ROOT / "data" / "timeline" / "timeline.json"
        if not p.exists():
            pytest.skip("timeline not built")
        events = json.loads(p.read_text(encoding="utf-8"))["events"]
        for e in events:
            if e.get("is_evacuation_order"):
                assert e.get("is_evacuation_directive"), (
                    f"{e['record_id']}: order but not directive"
                )
