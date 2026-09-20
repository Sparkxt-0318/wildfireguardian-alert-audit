"""Provenance immutability and credential redaction. Guards FM-13, FM-14."""

import hashlib
import os
from pathlib import Path

import pytest

from wg_alert_audit.core import credentials
from wg_alert_audit.core.model import AccessStatus, EvidenceClass
from wg_alert_audit.core.provenance import ProvenanceStore


@pytest.fixture()
def store(tmp_path: Path) -> ProvenanceStore:
    return ProvenanceStore(tmp_path / "raw")


def put(store: ProvenanceStore, content: bytes, url: str = "https://example.test/a"):
    return store.put(
        content=content,
        source_id="S1",
        url=url,
        content_type="text/html",
        evidence_class=EvidenceClass.NEWS_REPORT,
        access_status=AccessStatus.RETRIEVED,
    )


class TestContentAddressing:
    def test_sha256_matches_the_content(self, store):
        art = put(store, "원문".encode())
        assert art.sha256 == hashlib.sha256("원문".encode()).hexdigest()

    def test_blob_is_retrievable(self, store):
        art = put(store, "원문".encode())
        assert store.read_blob(art.sha256) == "원문".encode()

    def test_identical_content_is_not_duplicated(self, store):
        put(store, b"same")
        put(store, b"same")
        assert len(store.records()) == 1

    def test_verify_passes_on_an_intact_store(self, store):
        put(store, b"content")
        assert store.verify() == []


class TestSourceDrift:
    """FM-13: changed web content never silently overwrites the old artifact."""

    def test_changed_content_records_drift(self, store):
        put(store, b"version one")
        art = put(store, b"version two")
        assert art.drift_from is not None

    def test_drift_links_to_the_previous_hash(self, store):
        first = put(store, b"version one")
        second = put(store, b"version two")
        assert second.drift_from == first.sha256

    def test_both_artifacts_survive(self, store):
        first = put(store, b"version one")
        second = put(store, b"version two")
        assert store.read_blob(first.sha256) == b"version one"
        assert store.read_blob(second.sha256) == b"version two"

    def test_drift_is_logged(self, store):
        put(store, b"v1")
        put(store, b"v2")
        log = store.drift_log.read_text(encoding="utf-8")
        assert "SOURCE_DRIFT" in log

    def test_ledger_is_append_only(self, store):
        put(store, b"v1")
        put(store, b"v2")
        assert len(store.records()) == 2


class TestCredentialRedaction:
    """FM-14: no credential value reaches a log, report, or ledger."""

    KEY = "0123456789abcdef0123456789abcdef"

    @pytest.fixture(autouse=True)
    def _set_key(self, monkeypatch):
        monkeypatch.setenv("FIRMS_MAP_KEY", self.KEY)

    def test_key_in_a_url_path_is_redacted(self):
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{self.KEY}/VIIRS_SNPP_SP/1"
        out = credentials.redact(url)
        assert self.KEY not in out
        assert "<REDACTED>" in out

    def test_key_in_a_query_parameter_is_redacted(self):
        assert self.KEY not in credentials.redact(f"https://x/api?MAP_KEY={self.KEY}")

    def test_a_foreign_key_shaped_parameter_is_also_redacted(self):
        """Catches keys that never passed through this module."""
        out = credentials.redact("https://x/api?serviceKey=SOMEONE_ELSES_SECRET_VALUE")
        assert "SOMEONE_ELSES_SECRET_VALUE" not in out

    def test_korean_service_key_parameter_is_redacted(self):
        out = credentials.redact(
            "https://www.safetydata.go.kr/V2/api/DSSP-IF-00247?serviceKey=ABCDEF123456&pageNo=1"
        )
        assert "ABCDEF123456" not in out
        assert "pageNo=1" in out, "non-secret parameters must survive"

    def test_status_table_contains_no_values(self):
        blob = repr(credentials.status_table())
        assert self.KEY not in blob

    def test_status_reports_availability_only(self):
        assert credentials.status("firms") is credentials.CredentialStatus.AVAILABLE
        assert credentials.status("nmsc") is credentials.CredentialStatus.ABSENT

    def test_provenance_ledger_redacts_urls(self, store):
        art = store.put(
            content=b"x",
            source_id="S",
            url=f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{self.KEY}/X/1",
            content_type="text/csv",
            evidence_class=EvidenceClass.REMOTE_SENSING,
            access_status=AccessStatus.RETRIEVED,
        )
        assert self.KEY not in art.to_json()["url"]
        assert self.KEY not in store.index.read_text(encoding="utf-8")


class TestNoSecretsInRepo:
    def test_env_example_has_no_values(self):
        p = Path(__file__).resolve().parents[1] / ".env.example"
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                assert line.split("=", 1)[1].strip() == "", f"value present: {line}"

    def test_env_is_gitignored(self):
        gi = (Path(__file__).resolve().parents[1] / ".gitignore").read_text()
        assert "\n.env\n" in gi
