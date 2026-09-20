"""Time-role and timezone semantics. Guards FM-02, FM-04, FM-20."""

from datetime import datetime, timedelta, timezone

import pytest

from wg_alert_audit.core.intervals import (
    KST,
    UTC,
    IntervalError,
    TimeInterval,
    firms_acq_to_interval,
    parse_kst_minute,
)
from wg_alert_audit.core.model import Claim, EvidenceClass, Geography, Quantity, TimeRole


class TestMinuteResolution:
    """FM-20: a minute-resolution source did not report an instant."""

    def test_minute_becomes_a_span_not_a_point(self):
        iv = parse_kst_minute("2025-03-22", "11:24")
        assert not iv.is_point
        assert iv.width_seconds == 59

    def test_span_covers_the_whole_minute(self):
        iv = parse_kst_minute("2025-03-22", "11:24")
        assert iv.contains(datetime(2025, 3, 22, 11, 24, 0, tzinfo=KST))
        assert iv.contains(datetime(2025, 3, 22, 11, 24, 59, tzinfo=KST))
        assert not iv.contains(datetime(2025, 3, 22, 11, 25, 0, tzinfo=KST))

    def test_second_resolution_is_allowed_to_be_a_point(self):
        """A CBS record giving 15:30:17 genuinely is second-resolution."""
        iv = TimeInterval.at_second(datetime(2025, 3, 22, 15, 30, 17, tzinfo=KST))
        assert iv.is_point


class TestTimezone:
    """FM-02: FIRMS acquisition times are UTC, not Korean wall-clock."""

    def test_firms_acq_time_is_utc(self):
        iv = firms_acq_to_interval("2025-03-22", "0310")
        assert datetime.fromtimestamp(iv.lower, UTC).hour == 3

    def test_firms_utc_shifts_nine_hours_into_kst(self):
        iv = firms_acq_to_interval("2025-03-22", "0310")
        assert datetime.fromtimestamp(iv.lower, KST).hour == 12

    def test_firms_utc_can_cross_the_date_line_into_kst(self):
        """UTC 2025-03-22 18:00 is KST 2025-03-23 03:00 - a different day."""
        iv = firms_acq_to_interval("2025-03-22", "1800")
        kst = datetime.fromtimestamp(iv.lower, KST)
        assert (kst.day, kst.hour) == (23, 3)

    def test_firms_zero_stripped_time_is_padded(self):
        """FIRMS emits acq_time '310' for 03:10, not '0310'."""
        assert firms_acq_to_interval("2025-03-22", "310") == firms_acq_to_interval(
            "2025-03-22", "0310"
        )

    def test_naive_datetime_is_refused(self):
        """A naive datetime is how UTC silently becomes KST."""
        with pytest.raises(IntervalError, match="naive datetime"):
            TimeInterval.at_minute(datetime(2025, 3, 22, 11, 24))

    def test_kst_and_utc_intervals_compare_correctly(self):
        kst_noon = parse_kst_minute("2025-03-22", "12:10")
        utc_0310 = firms_acq_to_interval("2025-03-22", "0310")
        assert kst_noon.overlaps(utc_0310), "same instant, different clocks"


class TestRoleSeparation:
    """FM-04: publication time is not acquisition time."""

    def test_article_publication_time_cannot_be_an_acquisition_time(self):
        """A NASA article published 18:00 saying a satellite saw a fire earlier
        supplies PUBLICATION_TIME and nothing else."""
        assert not EvidenceClass.NEWS_REPORT.can_supply(
            TimeRole.SENSOR_ACQUISITION_TIME
        )

    def test_news_reported_alert_time_keeps_its_reported_role(self):
        """15:40 article reporting a 15:30 alert: the 15:30 is REPORTED."""
        c = Claim(
            claim_id="C1",
            incident_id="INC-1",
            quantity=Quantity.FIRST_PUBLIC_WARNING,
            time_interval=parse_kst_minute("2025-03-22", "15:30"),
            time_role=TimeRole.REPORTED_ALERT_SEND_TIME,
            geography=Geography(si_gun="영덕군"),
            evidence_class=EvidenceClass.NEWS_REPORT,
            source_id="S1",
            raw_text="오후 3시 30분 재난문자가 발송됐다",
        )
        assert c.time_role is TimeRole.REPORTED_ALERT_SEND_TIME

    def test_publication_time_is_separately_representable(self):
        pub = parse_kst_minute("2025-03-22", "15:40")
        reported = parse_kst_minute("2025-03-22", "15:30")
        assert not pub.overlaps(reported), "the two times are distinct data"


class TestIntervalArithmetic:
    def test_unbounded_before(self):
        iv = TimeInterval.before(datetime(2025, 3, 22, 15, 30, tzinfo=KST))
        assert iv.lower == float("-inf")
        assert "(-inf," in iv.format()

    def test_unbounded_after(self):
        iv = TimeInterval.after(datetime(2025, 3, 22, 14, 0, tzinfo=KST))
        assert iv.upper == float("inf")
        assert "+inf)" in iv.format()

    def test_difference_uses_crossed_bounds(self):
        """L = [f_L - a_U, f_U - a_L]."""
        a = parse_kst_minute("2025-03-22", "15:30")
        f = parse_kst_minute("2025-03-22", "16:00")
        lead = f - a
        assert lead.lower == pytest.approx(29 * 60 + 1)
        assert lead.upper == pytest.approx(30 * 60 + 59)

    def test_inf_minus_inf_is_unknown_not_a_number(self):
        a = TimeInterval.after(datetime(2025, 3, 22, 14, 0, tzinfo=KST))
        f = TimeInterval.after(datetime(2025, 3, 22, 15, 0, tzinfo=KST))
        assert (f - a).is_unknown

    def test_lower_above_upper_is_rejected(self):
        with pytest.raises(IntervalError):
            TimeInterval(100.0, 50.0)

    def test_unknown_interval_carries_no_information(self):
        assert TimeInterval.unknown().is_unknown
        assert TimeInterval.unknown().format() == "unknown"
