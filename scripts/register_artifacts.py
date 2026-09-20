"""Register the audit's derived datasets in the provenance ledger.

The per-item SHA-256s for retrieved content live inside the normalized files
themselves (every GK2A slot carries its image hash, every alert its record id).
This registers the *datasets* so that `wg-alert-audit verify` re-hashes them and
a reader can confirm the corpus has not drifted since the reports were written.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wg_alert_audit.core.model import AccessStatus, EvidenceClass  # noqa: E402
from wg_alert_audit.core.provenance import ProvenanceStore  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

ITEMS = [
    (
        "data/normalized/gk2a_ff_slots.jsonl",
        "gk2a-ff-slot-sweep",
        "https://nmsc.kma.go.kr/IMG/GK2A/AMI/L2/FF/",
        EvidenceClass.REMOTE_SENSING,
        "GK2A L2 FF observation-slot probe, 650 slots, per-slot SHA-256 inline",
    ),
    (
        "data/normalized/alerts_archive.jsonl",
        "safetydata-archive-harvest",
        "https://www.safetydata.go.kr/disaster-data/disasterNotification",
        EvidenceClass.PRIMARY_OPERATIONAL,
        "1,688 emergency-alert records, 2025-03-21..2025-04-02",
    ),
    (
        "data/timeline/timeline.json",
        "timeline",
        "derived://timeline",
        EvidenceClass.DERIVED,
        "311 claims extracted from the alert corpus",
    ),
    (
        "data/timeline/intervals.json",
        "intervals",
        "derived://intervals",
        EvidenceClass.DERIVED,
        "alert-timing intervals; explicitly not warning lead times",
    ),
    (
        "data/normalized/source_graph.json",
        "source-graph",
        "derived://source-graph",
        EvidenceClass.DERIVED,
        "source-upgrade graph, 11 nodes / 10 typed edges",
    ),
    (
        "data/normalized/verification_sample.json",
        "verification-sample",
        "derived://verification-sample",
        EvidenceClass.DERIVED,
        "pre-registered random sample, seed 20250322, n=50 of 311",
    ),
]


def main() -> None:
    store = ProvenanceStore(ROOT / "data" / "raw")
    for rel, source_id, url, cls, note in ITEMS:
        p = ROOT / rel
        if not p.exists():
            print(f"  skip (absent): {rel}")
            continue
        art = store.put(
            content=p.read_bytes(),
            source_id=source_id,
            url=url,
            content_type="application/json"
            if p.suffix == ".json"
            else "application/x-ndjson",
            evidence_class=cls,
            access_status=AccessStatus.RETRIEVED,
            language="ko" if "alert" in source_id else "und",
            title=rel,
            notes=note,
        )
        print(f"  {art.sha256[:12]}  {rel}  ({art.byte_length:,} B)")

    problems = store.verify()
    print(f"\nledger: {len(store.records())} artifacts")
    print("verify:", problems or "all blobs verify against their recorded SHA-256")


if __name__ == "__main__":
    main()
