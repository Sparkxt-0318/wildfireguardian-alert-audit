"""Immutable, content-addressed provenance store.

Every artifact that enters the corpus - fetched or hand-imported - is stored
by the SHA-256 of its bytes and described by an append-only ledger line. Two
properties matter:

* **Immutability.** Re-fetching a URL whose content changed does not overwrite
  the old artifact. It stores a second one and records ``SOURCE_DRIFT`` linking
  them, so a claim always points at the bytes it was actually read from (FM-13).
* **Auditability.** The ledger is committed to git; the blobs are not (they can
  be large and are re-fetchable). The ledger alone is enough to verify that a
  quoted span matches the artifact it claims to come from.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .credentials import redact
from .model import AccessStatus, EvidenceClass


@dataclass(slots=True)
class Artifact:
    """One retrieved or imported artifact, with complete provenance."""

    source_id: str
    url: str
    retrieval_time: str
    sha256: str
    content_type: str
    evidence_class: EvidenceClass
    access_status: AccessStatus
    language: str = "unknown"
    publication_time: str | None = None
    byte_length: int = 0
    #: "http" | "manual_import" | "derived"
    acquisition_method: str = "http"
    #: For manual imports: what the operator says this is and where it came from.
    import_note: str = ""
    #: Set when this artifact supersedes an earlier fetch of the same URL.
    drift_from: str | None = None
    title: str = ""
    notes: str = ""
    escalation_trail: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        d = asdict(self)
        d["evidence_class"] = self.evidence_class.value
        d["access_status"] = self.access_status.value
        # Defence in depth: nothing leaves this object with a key in it.
        d["url"] = redact(self.url)
        d["notes"] = redact(self.notes)
        d["import_note"] = redact(self.import_note)
        d["escalation_trail"] = [redact(s) for s in self.escalation_trail]
        return d


class ProvenanceStore:
    """Append-only artifact ledger plus a content-addressed blob directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.blobs = self.root / "blobs"
        self.index = self.root / "INDEX.jsonl"
        self.drift_log = self.root / "SOURCE_DRIFT.jsonl"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.index.touch(exist_ok=True)
        self.drift_log.touch(exist_ok=True)

    # -- reading ---------------------------------------------------------

    def records(self) -> list[dict]:
        return [
            json.loads(line)
            for line in self.index.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def by_url(self, url: str) -> list[dict]:
        target = redact(url)
        return [r for r in self.records() if r.get("url") == target]

    def blob_path(self, sha: str) -> Path:
        return self.blobs / sha[:2] / sha

    def read_blob(self, sha: str) -> bytes | None:
        p = self.blob_path(sha)
        return p.read_bytes() if p.exists() else None

    # -- writing ---------------------------------------------------------

    def put(
        self,
        *,
        content: bytes,
        source_id: str,
        url: str,
        content_type: str,
        evidence_class: EvidenceClass,
        access_status: AccessStatus,
        language: str = "unknown",
        publication_time: str | None = None,
        acquisition_method: str = "http",
        import_note: str = "",
        title: str = "",
        notes: str = "",
        escalation_trail: list[str] | None = None,
    ) -> Artifact:
        """Store bytes immutably and append a ledger line.

        If this URL was fetched before with *different* bytes, a
        ``SOURCE_DRIFT`` record is written and the new artifact links back to
        the old one. The old artifact is never modified or removed.
        """
        sha = hashlib.sha256(content).hexdigest()

        prior = self.by_url(url)
        drift_from = None
        if prior:
            previous = prior[-1]
            if previous["sha256"] != sha:
                drift_from = previous["sha256"]
                self._record_drift(url, previous, sha)
            else:
                # Identical bytes: return the existing record, do not duplicate.
                return _artifact_from_json(previous)

        dest = self.blob_path(sha)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(content)

        art = Artifact(
            source_id=source_id,
            url=url,
            retrieval_time=datetime.now(timezone.utc).isoformat(),
            sha256=sha,
            content_type=content_type,
            evidence_class=evidence_class,
            access_status=access_status,
            language=language,
            publication_time=publication_time,
            byte_length=len(content),
            acquisition_method=acquisition_method,
            import_note=import_note,
            drift_from=drift_from,
            title=title,
            notes=notes,
            escalation_trail=escalation_trail or [],
        )
        with self.index.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(art.to_json(), ensure_ascii=False) + "\n")
        return art

    def _record_drift(self, url: str, previous: dict, new_sha: str) -> None:
        entry = {
            "event": "SOURCE_DRIFT",
            "url": redact(url),
            "previous_sha256": previous["sha256"],
            "previous_retrieval_time": previous["retrieval_time"],
            "new_sha256": new_sha,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Content at this URL changed between retrievals. Both artifacts "
                "are retained; claims continue to reference the bytes they were "
                "read from."
            ),
        }
        with self.drift_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def verify(self) -> list[str]:
        """Re-hash every stored blob. Returns a list of problems."""
        problems: list[str] = []
        for rec in self.records():
            sha = rec["sha256"]
            blob = self.read_blob(sha)
            if blob is None:
                problems.append(f"{rec['source_id']}: blob {sha[:12]} missing")
            elif hashlib.sha256(blob).hexdigest() != sha:
                problems.append(f"{rec['source_id']}: blob {sha[:12]} hash mismatch")
        return problems


def _artifact_from_json(d: dict) -> Artifact:
    return Artifact(
        source_id=d["source_id"],
        url=d["url"],
        retrieval_time=d["retrieval_time"],
        sha256=d["sha256"],
        content_type=d["content_type"],
        evidence_class=EvidenceClass(d["evidence_class"]),
        access_status=AccessStatus(d["access_status"]),
        language=d.get("language", "unknown"),
        publication_time=d.get("publication_time"),
        byte_length=d.get("byte_length", 0),
        acquisition_method=d.get("acquisition_method", "http"),
        import_note=d.get("import_note", ""),
        drift_from=d.get("drift_from"),
        title=d.get("title", ""),
        notes=d.get("notes", ""),
        escalation_trail=d.get("escalation_trail", []),
    )
