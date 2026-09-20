"""Acquisition-outcome classification. Guards FM-01, FM-19."""

from wg_alert_audit.core.access import Attempt, classify
from wg_alert_audit.core.model import AccessStatus


def st(**kw) -> AccessStatus:
    kw.setdefault("source_id", "S")
    kw.setdefault("url", "https://example.test/x")
    return classify(Attempt(**kw))[0]


class TestCredentialGating:
    """A gated dataset is not an absent dataset."""

    def test_firms_invalid_map_key_is_api_key_required(self):
        assert st(http_status=200, body_sample="Invalid MAP_KEY.") is (
            AccessStatus.API_KEY_REQUIRED
        )

    def test_401_on_a_key_bearing_url_is_api_key_required(self):
        assert st(url="https://x/api/area/csv/MAP_KEY=abc/", http_status=401) is (
            AccessStatus.API_KEY_REQUIRED
        )

    def test_401_without_a_key_param_is_authentication_required(self):
        assert st(http_status=401) is AccessStatus.AUTHENTICATION_REQUIRED

    def test_korean_unregistered_service_key(self):
        assert st(http_status=200, body_sample="SERVICE KEY IS NOT REGISTERED ERROR") is (
            AccessStatus.API_KEY_REQUIRED
        )

    def test_korean_language_key_error(self):
        assert st(http_status=200, body_sample="등록되지 않은 인증키입니다") is (
            AccessStatus.API_KEY_REQUIRED
        )

    def test_gated_never_implies_absence(self):
        for s in (
            AccessStatus.API_KEY_REQUIRED,
            AccessStatus.AUTHENTICATION_REQUIRED,
            AccessStatus.REGISTRATION_REQUIRED,
            AccessStatus.MANUAL_DOWNLOAD_AVAILABLE,
            AccessStatus.ACCESS_DENIED,
        ):
            assert not s.implies_data_absent
            assert s.is_gated


class TestMigration:
    def test_cross_host_redirect_is_migration(self):
        assert st(
            url="https://old.test/a", http_status=302, redirect_to="https://new.test/a"
        ) is AccessStatus.ENDPOINT_MIGRATED

    def test_same_host_redirect_is_not_migration(self):
        assert st(
            url="https://x.test/a", http_status=302, redirect_to="https://x.test/b"
        ) is AccessStatus.UNKNOWN

    def test_korean_service_termination_notice(self):
        assert st(http_status=200, body_sample="본 서비스는 종료되었습니다") is (
            AccessStatus.ENDPOINT_MIGRATED
        )

    def test_404_on_an_unverified_path_is_migration_not_absence(self):
        """docs/ACCESS_STATUS_MODEL.md rule 2."""
        assert st(http_status=404, query_was_valid=False) is (
            AccessStatus.ENDPOINT_MIGRATED
        )

    def test_404_on_a_verified_query_is_not_found(self):
        assert st(http_status=404, query_was_valid=True) is AccessStatus.NOT_FOUND


class TestTransport:
    def test_timeout_is_temporary(self):
        assert st(transport_error="connection timed out") is (
            AccessStatus.TEMPORARY_NETWORK_FAILURE
        )

    def test_connection_reset_is_temporary(self):
        assert st(transport_error="Connection reset by peer") is (
            AccessStatus.TEMPORARY_NETWORK_FAILURE
        )

    def test_dns_failure_is_temporary(self):
        assert st(transport_error="Temporary failure in name resolution") is (
            AccessStatus.TEMPORARY_NETWORK_FAILURE
        )

    def test_transport_failure_never_implies_absence(self):
        assert not st(transport_error="timeout").implies_data_absent

    def test_5xx_is_server_error(self):
        assert st(http_status=503) is AccessStatus.SERVER_ERROR


class TestEmptyResults:
    """FM-19: NO_RELEVANT_RECORD needs a successful, valid query."""

    def test_valid_query_with_zero_rows(self):
        assert st(
            http_status=200, parsed_empty_result=True, query_was_valid=True
        ) is AccessStatus.NO_RELEVANT_RECORD

    def test_empty_result_from_an_unvalidated_query_is_withheld(self):
        assert st(
            http_status=200, parsed_empty_result=True, query_was_valid=False
        ) is AccessStatus.UNKNOWN

    def test_only_no_relevant_record_licenses_absence(self):
        absent = [s for s in AccessStatus if s.implies_data_absent]
        assert absent == [AccessStatus.NO_RELEVANT_RECORD]


class TestSuccessAndManual:
    def test_plain_success(self):
        assert st(http_status=200, body_sample="<html>data</html>") is (
            AccessStatus.RETRIEVED
        )

    def test_download_request_form_is_manual(self):
        assert st(http_status=200, body_sample="다운로드 신청 페이지") is (
            AccessStatus.MANUAL_DOWNLOAD_AVAILABLE
        )

    def test_rate_limit(self):
        assert st(http_status=429) is AccessStatus.RATE_LIMITED

    def test_korean_quota_message(self):
        assert st(http_status=200, body_sample="일일 호출 한도 초과") is (
            AccessStatus.RATE_LIMITED
        )

    def test_body_signal_beats_a_200_status(self):
        """Korean and NASA services return 200 with an error document."""
        assert st(http_status=200, body_sample="Invalid MAP_KEY.") is not (
            AccessStatus.RETRIEVED
        )


class TestReasonIsRecorded:
    def test_every_classification_explains_itself(self):
        status, reason = classify(
            Attempt(source_id="S", url="https://x", http_status=200,
                    body_sample="Invalid MAP_KEY.")
        )
        assert status is AccessStatus.API_KEY_REQUIRED
        assert "not data absence" in reason
