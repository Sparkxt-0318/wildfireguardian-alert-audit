"""Adapter behaviour and CLI surface. Guards FM-18, FM-19 and the soft-404."""

from datetime import date, datetime, timezone

import pytest

from wg_alert_audit.adapters import alert_archive, alerts, firms, gk2a
from wg_alert_audit.core.model import AccessStatus


class TestFirmsHistoricalSemantics:
    """March 2025 needs the SP archive; an empty NRT result is a window artefact."""

    def test_historical_sources_are_all_sp_or_no_sp_stream(self):
        for s in firms.HISTORICAL_SOURCES:
            assert s.endswith("_SP") or s == "VIIRS_NOAA21_NRT"

    def test_rolling_nrt_sources_are_listed_separately(self):
        assert "VIIRS_SNPP_NRT" in firms.ROLLING_NRT_SOURCES
        assert "VIIRS_SNPP_NRT" not in firms.HISTORICAL_SOURCES

    def test_missing_key_is_a_credential_gap_not_an_absence(self, monkeypatch):
        monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
        monkeypatch.delenv("NASA_FIRMS_MAP_KEY", raising=False)
        r = firms.retrieve("VIIRS_SNPP_SP", date(2025, 3, 21))
        assert r.status is AccessStatus.API_KEY_REQUIRED
        assert not r.status.implies_data_absent
        assert "not data absence" in r.reason

    def test_redacted_url_carries_no_key(self, monkeypatch):
        monkeypatch.setenv("FIRMS_MAP_KEY", "0123456789abcdef0123456789abcdef")
        r = firms.retrieve("VIIRS_SNPP_SP", date(2025, 3, 21))
        assert "0123456789abcdef" not in r.url_redacted

    def test_bbox_is_west_south_east_north(self):
        w, s, e, n = (float(x) for x in firms.GYEONGBUK_BBOX.split(","))
        assert w < e and s < n
        assert 128 < w < 130 and 35 < s < 37

    def test_day_range_is_capped(self):
        with pytest.raises(ValueError):
            firms.area_url("K", "VIIRS_SNPP_SP", firms.GYEONGBUK_BBOX, 6, date(2025, 3, 1))

    def test_windows_tile_the_span(self):
        ws = firms.windows(date(2025, 2, 28), date(2025, 4, 1))
        assert ws[0] == date(2025, 2, 28)
        assert (ws[1] - ws[0]).days == firms.MAX_DAY_RANGE

    def test_sp_rows_are_flagged_science_quality(self):
        csv = (
            "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,"
            "instrument,confidence,version,bright_ti5,frp,daynight\n"
            "36.5,128.9,320.1,0.4,0.4,2025-03-22,310,N,VIIRS,n,2.0,295.0,5.2,D\n"
            "36.6,128.8,330.0,0.4,0.4,2025-03-22,311,N,VIIRS,n,2.0NRT,295.0,6.0,D\n"
        )
        rows = firms.parse_csv(csv, "VIIRS_SNPP_SP")
        assert rows[0].is_science_quality
        assert not rows[1].is_science_quality

    def test_acquisition_time_is_utc(self):
        csv = (
            "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,"
            "instrument,confidence,version,bright_ti5,frp,daynight\n"
            "36.5,128.9,320.1,0.4,0.4,2025-03-22,310,N,VIIRS,n,2.0,295.0,5.2,D\n"
        )
        iv = firms.parse_csv(csv, "VIIRS_SNPP_SP")[0].acquisition_interval
        assert datetime.fromtimestamp(iv.lower, timezone.utc).hour == 3


class TestGk2aUrls:
    def test_url_uses_utc_not_kst(self):
        u = gk2a.image_url(datetime(2025, 3, 22, 3, 0, tzinfo=timezone.utc))
        assert "202503220300" in u

    def test_naive_datetime_is_refused(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            gk2a.image_url(datetime(2025, 3, 22, 3, 0))

    def test_area_codes_carry_their_documented_cadence(self):
        assert gk2a.AREAS["KO"][2] == 2
        assert gk2a.AREAS["EA"][2] == 10
        assert gk2a.AREAS["FD"][2] == 10

    def test_soft_404_threshold_is_set(self):
        """A missing slot is HTTP 200 with a ~1 KB HTML body, not a 404."""
        assert gk2a.SOFT_404_MAX_BYTES > 1019

    def test_slots_respect_cadence(self):
        slots = gk2a.slots_between(
            datetime(2025, 3, 22, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 3, 22, 0, 10, tzinfo=timezone.utc),
            "KO",
        )
        assert len(slots) == 5


class TestAlertRoutes:
    def test_safetydata_is_the_authoritative_route(self):
        assert "AUTHORITATIVE" in alerts.ENDPOINTS["safetydata_dssp"]["role"]

    def test_data_go_kr_is_only_a_pointer(self):
        assert "POINTER" in alerts.ENDPOINTS["data_go_kr_link"]["role"]

    def test_legacy_route_is_marked_superseded(self):
        assert "SUPERSEDED" in alerts.ENDPOINTS["disastermsg3_legacy"]["role"]

    def test_gated_route_reports_credential_not_absence(self):
        st, reason = alerts.status_without_credential("safetydata_dssp")
        assert st is AccessStatus.API_KEY_REQUIRED
        assert not st.implies_data_absent

    def test_result_code_30_is_documented(self):
        assert "NOT REGISTERED" in alerts.RESULT_CODES["30"]

    def test_second_resolution_send_time_is_a_point(self):
        iv, _ = alerts.parse_send_time("2025/03/22 15:30:17")
        assert iv is not None and iv.is_point

    def test_minute_resolution_send_time_is_a_span(self):
        iv, _ = alerts.parse_send_time("2025/03/22 15:30")
        assert iv is not None and not iv.is_point

    def test_timezone_assumption_is_reported(self):
        _, tz_assumed = alerts.parse_send_time("2025/03/22 15:30:17")
        assert tz_assumed is True


class TestAlertArchiveParsing:
    ROW = (
        '<td class="cell-no">1</td>'
        '<td class="board-list-new cell-subject"><a class="tableHover" '
        'href="/disaster-data/disasterNotificationDetail?sn=231574">'
        '(대피명령 발령) 안평면 괴산리 산 61 산불 확산으로 의성읍 업1리 주민과 '
        '등산객은 의성체육관으로 대피하시기바랍니다. [의성군]</a></td>'
        '<td class="cell-date">2025/03/23 16:45:14</td>'
    )

    def test_row_is_parsed(self):
        assert len(alert_archive.parse_listing(self.ROW, "u")) == 1

    def test_record_id_is_captured(self):
        assert alert_archive.parse_listing(self.ROW, "u")[0].sn == "231574"

    def test_send_time_is_second_resolution(self):
        a = alert_archive.parse_listing(self.ROW, "u")[0]
        assert a.send_interval.is_point

    def test_issuing_authority_is_extracted(self):
        assert alert_archive.parse_listing(self.ROW, "u")[0].issuing_authority == "의성군"

    def test_message_text_is_verbatim(self):
        a = alert_archive.parse_listing(self.ROW, "u")[0]
        assert a.message_text.startswith("(대피명령 발령)")

    def test_record_is_primary_operational(self):
        a = alert_archive.parse_listing(self.ROW, "u")[0]
        assert a.to_json()["evidence_class"] == "PRIMARY_OPERATIONAL"
        assert a.to_json()["time_role"] == "ALERT_SEND_TIME"


class TestCli:
    def test_sources_runs(self, capsys):
        from wg_alert_audit.cli import main

        assert main(["sources"]) == 0
        out = capsys.readouterr().out
        assert "CREDENTIALS" in out and "VIIRS_SNPP_SP" in out

    def test_sources_prints_no_credential_values(self, capsys, monkeypatch):
        from wg_alert_audit.cli import main

        monkeypatch.setenv("FIRMS_MAP_KEY", "0123456789abcdef0123456789abcdef")
        main(["sources"])
        assert "0123456789abcdef" not in capsys.readouterr().out

    def test_parse_command_runs(self, capsys):
        from wg_alert_audit.cli import main

        assert main(["parse", "영덕군 지품면에 대피명령이 내려졌다"]) == 0
        assert "evacuation_order" in capsys.readouterr().out
