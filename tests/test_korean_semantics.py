"""Korean event-label extraction. Guards FM-07, FM-08, X-5."""

from wg_alert_audit.core.korean import find_times, parse
from wg_alert_audit.core.model import Quantity


class TestIgnitionVsReignition:
    """FM-07: 재발화 contains 발화 but is the opposite kind of evidence."""

    def test_reignition_is_not_ignition(self):
        r = parse("오후 6시 20분께 재발화가 확인됐다")
        assert Quantity.RE_IGNITION in r.quantities
        assert Quantity.IGNITION not in r.quantities

    def test_plain_ignition_still_works(self):
        r = parse("22일 11시 24분 발화한 것으로 추정된다")
        assert Quantity.IGNITION in r.quantities
        assert Quantity.RE_IGNITION not in r.quantities

    def test_initial_ignition_compound(self):
        r = parse("최초발화 지점은 야산이었다")
        assert r.quantities == [Quantity.IGNITION]

    def test_reignition_retains_verbatim_korean(self):
        r = parse("재발화가 확인됐다")
        assert r.labels[0].raw == "재발화"

    def test_both_in_one_text_stay_separate(self):
        r = parse("발화 이후 진화됐으나 재발화가 발생했다")
        assert Quantity.IGNITION in r.quantities
        assert Quantity.RE_IGNITION in r.quantities


class TestSuppressionFamily:
    """진화 vs 재진화 vs 진화율 - the same prefix trap."""

    def test_re_suppression_is_not_containment(self):
        assert Quantity.CONTAINMENT not in parse("재진화 작업이 시작됐다").quantities

    def test_containment_rate_is_not_a_containment_event(self):
        assert Quantity.CONTAINMENT not in parse("진화율 92%").quantities

    def test_main_fire_extinguished_is_containment(self):
        assert Quantity.CONTAINMENT in parse("주불진화 완료").quantities


class TestEvacuationFamily:
    """FM-08: a mention of 대피 is not an evacuation order."""

    def test_generic_evacuation_mention_is_not_an_order(self):
        assert Quantity.EVACUATION_ORDER not in parse("주민 대피가 이어졌다").quantities

    def test_shelter_is_not_an_order(self):
        assert Quantity.EVACUATION_ORDER not in parse("주민들은 대피소로 이동했다").quantities

    def test_advisory_is_not_an_order(self):
        assert Quantity.EVACUATION_ORDER not in parse("대피 권고가 발령됐다").quantities

    def test_order_is_an_order(self):
        assert Quantity.EVACUATION_ORDER in parse("영덕군에 대피명령이 내려졌다").quantities

    def test_short_form_order_is_an_order(self):
        assert Quantity.EVACUATION_ORDER in parse("대피령이 발령됐다").quantities

    def test_advisory_is_labelled_as_advisory(self):
        r = parse("대피 권고가 발령됐다")
        assert "ADVISORY" in r.labels[0].gloss


class TestAlertFamily:
    def test_emergency_alert_is_a_public_warning(self):
        assert Quantity.FIRST_PUBLIC_WARNING in parse("긴급재난문자가 발송됐다").quantities

    def test_longest_form_wins(self):
        r = parse("긴급재난문자 발송")
        assert r.labels[0].raw == "긴급재난문자"

    def test_broadcast_is_not_a_text_alert(self):
        assert parse("재난방송이 송출됐다").quantities == []


class TestNoOverlappingMatches:
    """A span consumed by a longer surface is closed to shorter ones."""

    def test_spans_do_not_overlap(self):
        r = parse("재발화 이후 대피명령과 긴급재난문자가 이어졌다")
        spans = sorted((m.start, m.end) for m in r.labels)
        for (_, e1), (s2, _) in zip(spans, spans[1:]):
            assert e1 <= s2


class TestTimeMentions:
    def test_meridiem_afternoon(self):
        t = find_times("오후 3시 30분")[0]
        assert (t.hour, t.minute, t.meridiem_used) == (15, 30, True)

    def test_meridiem_morning(self):
        assert find_times("오전 11시 24분")[0].hour == 11

    def test_noon_boundary(self):
        assert find_times("오후 12시 5분")[0].hour == 12

    def test_midnight_boundary(self):
        assert find_times("오전 12시 5분")[0].hour == 0

    def test_24_hour_form(self):
        t = find_times("15시 30분")[0]
        assert (t.hour, t.minute, t.meridiem_used) == (15, 30, False)

    def test_colon_form(self):
        assert find_times("15:30에 발송")[0].hour == 15

    def test_verbatim_surface_is_preserved(self):
        assert find_times("오후 3시 30분")[0].raw == "오후 3시 30분"

    def test_multiple_times_are_ordered(self):
        ts = find_times("11시 24분에 발화해 오후 3시 30분에 문자가 발송됐다")
        assert [t.hour for t in ts] == [11, 15]

    def test_out_of_range_is_ignored(self):
        assert find_times("99:99") == []
