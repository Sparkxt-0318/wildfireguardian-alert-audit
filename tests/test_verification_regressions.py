"""Regressions for every defect found by the independent verification pass.

Each case is a verbatim string from the harvested alert corpus, with the record
id it came from. These are the concrete failures that a 50-claim manual audit
found at a 32% discrepancy rate; they exist so the same shapes cannot regress.
"""

from wg_alert_audit.core.geography import extract, extract_from_clause
from wg_alert_audit.core.korean import parse
from wg_alert_audit.core.model import Quantity


def quantities(text: str) -> list[str]:
    return [q.value for q in parse(text).quantities]


def counties(text: str) -> list[str]:
    out: list[str] = []
    for c in extract(text):
        for x in c.all_si_gun:
            if x not in out:
                out.append(x)
    return out


def eup_myeon(text: str) -> list[str]:
    out: list[str] = []
    for c in extract(text):
        for x in c.all_eup_myeon:
            if x not in out:
                out.append(x)
    return out


class TestClusterA_OccurrenceIsNotAlwaysIgnition:
    """발생 ("occurrence") governed by something other than a fire."""

    def test_smoke_occurring_is_not_an_ignition(self):
        # sn=232247
        t = "강한 바람으로 연기 다량 발생중 남선면 원림1리 마을 주민분들께서는"
        assert Quantity.REPORTED_IGNITION.value not in quantities(t)

    def test_casualties_occurring_is_not_an_ignition(self):
        # sn=232148
        t = "관내 산불로 인해 인명사고 발생 및 주요시설물 소실"
        assert Quantity.REPORTED_IGNITION.value not in quantities(t)

    def test_water_outage_caused_by_a_fire_is_not_an_ignition(self):
        # sn=232285, sent five days after ignition
        t = "산불 발생으로 인해 가압장이 정전되어 수돗물이 일시적으로 단수됨을 알려드립니다"
        assert Quantity.REPORTED_IGNITION.value not in quantities(t)

    def test_risk_of_a_fire_is_not_an_ignition(self):
        """sn=231363 - sent 11:05:22, twenty minutes BEFORE the real ignition.

        The most damaging instance found: a spurious ignition report here would
        silently pre-date the earliest genuine one in any min-over-claims query.
        """
        t = "건조한 날씨와 강한 바람으로 산불발생 위험이 높습니다"
        assert Quantity.REPORTED_IGNITION.value not in quantities(t)

    def test_a_negated_occurrence_is_not_an_ignition(self):
        # sn=231373 - a prevention PSA asking that fires NOT occur
        t = "도내 산불이 많이 발생중이며 산불이 발생하지 않도록 주의하여 주시기 바랍니다"
        assert Quantity.REPORTED_IGNITION.value not in quantities(t)

    def test_a_genuine_fire_occurrence_is_still_caught(self):
        t = "금일 11:24 의성군 안평면 괴산리 산 61번지 일원 산불 발생하여 확산중"
        assert Quantity.REPORTED_IGNITION.value in quantities(t)

    def test_labels_are_deduplicated(self):
        t = "산불이 발생중이며 산불이 발생하지 않도록 주의"
        assert len(quantities(t)) == len(set(quantities(t)))


class TestClusterB_SuppressionInProgressIsNotContainment:
    """진화 중 is the opposite of contained, and the veto list missed the space."""

    def test_spaced_suppression_in_progress(self):
        # sn=232076 - the same alert tells evacuees NOT to go home
        t = "현재 산불 진화 중. 대피소에 대피하신 분들께서는 머물러 주시고 귀가를 자제하여 주시기 바랍니다"
        assert Quantity.CONTAINMENT.value not in quantities(t)

    def test_suppression_work_in_progress(self):
        # sn=232678 - a drone no-fly notice
        t = "금일 헬기 산불진화 작업 중이므로 드론운영을 절대 금지합니다"
        assert Quantity.CONTAINMENT.value not in quantities(t)

    def test_genuine_containment_is_still_caught(self):
        assert Quantity.CONTAINMENT.value in quantities("주불진화 완료")

    def test_containment_rate_is_still_not_an_event(self):
        assert Quantity.CONTAINMENT.value not in quantities("진화율 92%")


class TestClusterC_IgnitionPointIsALocation:
    """발화지점 names a place; it does not report that an ignition just occurred."""

    def test_ignition_point_is_not_a_bare_ignition(self):
        # sn=231423, an alert sent at 16:10 - hours after the fact
        t = "안평면 괴산리(발화지점) 산불 확산으로 의성읍 후죽1리 주민들께서는 대피하시기 바랍니다"
        assert Quantity.IGNITION.value not in quantities(t)

    def test_the_locality_is_still_extracted(self):
        t = "안평면 괴산리(발화지점) 산불 확산으로 의성읍 후죽1리 주민들께서는 대피"
        assert "안평면" in eup_myeon(t) and "의성읍" in eup_myeon(t)


class TestClusterD_AllLocalitiesAreKept:
    """Every locality in a clause, not the first one only."""

    def test_cross_county_road_closure_keeps_both_counties(self):
        # sn=231903 - 청송군 written in full and previously dropped
        t = "산불 확산으로 인한 914번 지방도 길안면 양곡재 - 청송군 파천면 통행불가"
        assert {"안동시", "청송군"} <= set(counties(t))

    def test_cross_county_road_closure_keeps_both_myeon(self):
        t = "산불 확산으로 인한 914번 지방도 길안면 양곡재 - 청송군 파천면 통행불가"
        assert {"길안면", "파천면"} <= set(eup_myeon(t))

    def test_second_myeon_in_a_clause_is_kept(self):
        # sn=232045
        t = "현재 산불관련 입암면-임동면 군도2호선 산불 접근으로 전면 통제 합니다"
        assert {"입암면", "임동면"} <= set(eup_myeon(t))

    def test_eup_after_a_ri_is_kept(self):
        # sn=231443
        t = "(대피명령 발령) 안평면 괴산리 산 61 산불 확산 의성읍 중리 3리 주민과 등산객은 대피"
        assert "의성읍" in eup_myeon(t)

    def test_neighbouring_municipality_myeon_are_known(self):
        # sn=232036 - three 면 lost to a five-county gazetteer horizon
        t = "의성 산불로 인하여 포항 북구 죽장면, 기북면, 송라면 등 직간접 피해"
        assert {"죽장면", "기북면", "송라면"} <= set(eup_myeon(t))
        assert "포항시" in counties(t)


class TestHazardCompounds:
    """의성산불 is a place plus a hazard noun, written without a space."""

    def test_concatenated_compound_resolves(self):
        assert "의성군" in counties("의성산불이 우리지역으로 확산되고 있습니다")

    def test_other_compounds_resolve(self):
        assert "안동시" in counties("안동산불 경보")
        assert "청송군" in counties("청송화재 발생")

    def test_the_expressway_guard_still_holds(self):
        """The split requires an EXACT gazetteer prefix, so X-3 is untouched."""
        assert counties("서산영덕고속도로 구간에서 차량 통행이 통제됐다") == []

    def test_line_and_interchange_names_still_leak_nothing(self):
        assert counties("청주영덕선 서의성IC 구간 통제") == []

    def test_facility_embedding_a_county_still_leaks_nothing(self):
        assert extract_from_clause("의성실내체육관으로 대피").all_si_gun == []
