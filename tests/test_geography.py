"""Korean geography extraction. Guards FM-05, FM-06, X-3, X-4."""

from wg_alert_audit.core.geography import attribute, extract, extract_from_clause, relate
from wg_alert_audit.core.model import Geography, GeoRelation


class TestRoadNameFalseMatch:
    """X-3 / FM-05: the canonical failure this repository must not commit.

    Korean expressways are named for their endpoints, so 서산영덕고속도로 contains
    both 서산 and 영덕 while being evidence of neither location.
    """

    TRAP = "서산영덕고속도로 구간에서 차량 통행이 통제됐다"

    def test_expressway_does_not_imply_yeongdeok_county(self):
        for r in extract(self.TRAP):
            assert r.geography.si_gun != "영덕군"

    def test_expressway_does_not_imply_seosan_either(self):
        for r in extract(self.TRAP):
            assert r.geography.si_gun not in ("서산시", "서산")

    def test_expressway_is_captured_as_a_road(self):
        roads = [r.geography.road for r in extract(self.TRAP) if r.geography.road]
        assert "서산영덕고속도로" in roads

    def test_attribute_refuses_a_road_only_text(self):
        assert attribute(self.TRAP) is None

    def test_rejection_is_explained(self):
        res = extract_from_clause("서산영덕고속도로 구간")
        rejected = [m for m in res.matches if not m.accepted]
        assert rejected and "road suffix" in rejected[0].reason

    def test_a_road_alongside_a_real_locality_keeps_both_straight(self):
        g = attribute("영덕군 지품면 영덕로 일대가 통제됐다")
        assert g is not None
        assert (g.si_gun, g.eup_myeon_dong, g.road) == ("영덕군", "지품면", "영덕로")


class TestParticleHandling:
    """로 is both a case particle and the commonest road suffix."""

    def test_place_plus_directional_particle_is_a_place(self):
        res = extract_from_clause("불이 안동시로 번졌다")
        assert res.geography.si_gun == "안동시"
        assert res.geography.road is None

    def test_road_without_admin_suffix_stays_a_road(self):
        res = extract_from_clause("영덕로에서")
        assert res.geography.si_gun is None
        assert res.geography.road == "영덕로"

    def test_locative_particle_is_stripped(self):
        assert extract_from_clause("청송군에서").geography.si_gun == "청송군"

    def test_bare_name_with_particle_resolves_via_parent(self):
        g = extract_from_clause("영양읍에도 불길이 접근했다").geography
        assert (g.si_gun, g.eup_myeon_dong) == ("영양군", "영양읍")


class TestMultiLocationAttribution:
    """X-4 / FM-06: no first-location capture."""

    SENTENCE = "의성군에서 시작된 불이 안동시로 번졌다"

    def test_both_counties_are_seen(self):
        found = {r.geography.si_gun for r in extract(self.SENTENCE)}
        assert {"의성군", "안동시"} <= found

    def test_attribution_refuses_rather_than_picking_the_first(self):
        assert attribute(self.SENTENCE) is None

    def test_clauses_are_separated(self):
        assert len(extract(self.SENTENCE)) > 1


class TestNaturalFeatures:
    """A mountain name does not carry an administrative assignment."""

    def test_mountain_infers_no_county(self):
        g = extract_from_clause("주왕산 인근에서 연기가 목격됐다").geography
        assert g.si_gun is None
        assert g.named_place == "주왕산"

    def test_refusal_is_noted(self):
        assert "no county inferred" in extract_from_clause("주왕산 인근").note


class TestAdministrativeCurrency:
    """군위군 left Gyeongbuk on 2023-07-01, before the target window."""

    def test_gunwi_is_not_treated_as_gyeongbuk(self):
        g = extract_from_clause("군위군 지역에 재난문자가 발송됐다").geography
        assert g.si_gun is None

    def test_exclusion_is_explained(self):
        res = extract_from_clause("군위군 지역")
        assert any("대구광역시" in m.reason for m in res.matches if not m.accepted)


class TestGeoRelation:
    """D-006 / FM-11: county-level pairing is recorded but not sufficient."""

    EUP = Geography(province="경상북도", si_gun="영덕군", eup_myeon_dong="지품면")
    EUP2 = Geography(province="경상북도", si_gun="영덕군", eup_myeon_dong="강구면")
    COUNTY = Geography(province="경상북도", si_gun="영덕군")
    OTHER = Geography(province="경상북도", si_gun="의성군")

    def test_same_eup_myeon(self):
        assert relate(self.EUP, self.EUP) is GeoRelation.SAME_EUP_MYEON

    def test_different_eup_same_county(self):
        assert relate(self.EUP, self.EUP2) is GeoRelation.SAME_COUNTY

    def test_county_only_is_same_county(self):
        assert relate(self.COUNTY, self.COUNTY) is GeoRelation.SAME_COUNTY

    def test_different_counties_are_incompatible(self):
        assert relate(self.EUP, self.OTHER) is GeoRelation.INCOMPATIBLE

    def test_same_county_is_gated_out_of_lead_time(self):
        assert not GeoRelation.SAME_COUNTY.sufficient_for_lead_time

    def test_eup_level_is_sufficient(self):
        assert GeoRelation.SAME_EUP_MYEON.sufficient_for_lead_time

    def test_unknown_geography_is_insufficient(self):
        assert not GeoRelation.UNKNOWN.sufficient_for_lead_time


class TestRoadDetectionIsPlaceAware:
    """로 and 길 are also particles and noun endings.

    The road rule exists to stop a road name leaking its embedded county (X-3),
    so it fires on stems that embed a place name and stays quiet otherwise.
    Cases below are all real strings from the harvested alert corpus.
    """

    def test_weather_particle_is_not_a_road(self):
        assert extract_from_clause("날씨로 인해").geography.road is None

    def test_verb_ending_is_not_a_road(self):
        assert extract_from_clause("단계이므로 주의").geography.road is None

    def test_please_evacuate_is_not_a_road(self):
        assert extract_from_clause("대피하시길 바랍니다").geography.road is None

    def test_time_plus_buro_is_not_a_road(self):
        assert extract_from_clause("금일 13:44부로 통제").geography.road is None

    def test_facility_plus_directional_particle_is_a_facility(self):
        g = extract_from_clause("의성실내체육관으로 대피").geography
        assert g.facility is not None and g.road is None

    def test_a_facility_does_not_leak_its_embedded_county(self):
        """의성실내체육관 contains 의성 and must not imply 의성군."""
        assert extract_from_clause("의성실내체육관으로 대피").geography.si_gun is None

    def test_real_road_with_embedded_place_is_still_caught(self):
        g = extract_from_clause("영덕군 지품면 영덕로 일대").geography
        assert g.road == "영덕로" and g.si_gun == "영덕군"

    def test_expressway_still_blocks_both_endpoints(self):
        g = extract_from_clause("서산영덕고속도로 구간").geography
        assert g.road == "서산영덕고속도로" and g.si_gun is None

    def test_line_name_does_not_leak_a_county(self):
        """청주영덕선 (Cheongju-Yeongdeok Line) embeds 영덕."""
        assert extract_from_clause("청주영덕선 통제").geography.si_gun is None

    def test_interchange_name_does_not_leak_a_county(self):
        """서의성IC embeds 의성; exact token matching keeps it out."""
        assert extract_from_clause("서의성IC 통제").geography.si_gun is None
