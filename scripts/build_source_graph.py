"""Build the source-upgrade graph (docs/EVIDENCE_MODEL.md).

Discovering a stronger source never deletes the weaker one; it adds a typed
edge. The graph is the audit trail: the strongest node is the current best
evidence, and the chain that reached it stays attached to the claim.

Nodes here are the real sources this audit walked, not an illustration.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wg_alert_audit.core.model import EdgeType, EvidenceClass  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "normalized" / "source_graph.json"

NODES = [
    # --- the ignition-time chain -------------------------------------
    {
        "id": "WIKI-KO",
        "label": "ko.wikipedia 2025년 의성-안동 산불",
        "evidence_class": EvidenceClass.TERTIARY.value,
        "role": "discovery aid only; never a terminal source",
        "url": "https://ko.wikipedia.org/wiki/2025년_의성-안동_산불",
    },
    {
        "id": "NEWS-AGG",
        "label": "Korean press coverage of the Uiseong ignition",
        "evidence_class": EvidenceClass.NEWS_REPORT.value,
        "role": "reports an ignition time; cannot be the record of one",
    },
    {
        "id": "MOIS-PR-0322",
        "label": "MOIS 보도자료, 2025-03-22, 「…의성군 산불 관련 긴급지시」",
        "evidence_class": EvidenceClass.PRIMARY_OPERATIONAL.value,
        "role": "operational-at-the-time; states 11시 24분경",
        "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=156680269",
        "states": "11시 24분경",
    },
    {
        "id": "CBS-UISEONG-151622",
        "label": "의성군청 emergency alert, sent 2025/03/22 15:16:22",
        "evidence_class": EvidenceClass.PRIMARY_OPERATIONAL.value,
        "role": "the operational alert itself; states 11:25",
        "states": "11:25",
    },
    {
        "id": "CBS-ANDONG-151800",
        "label": "안동시 emergency alert, sent 2025/03/22 15:18:00",
        "evidence_class": EvidenceClass.PRIMARY_OPERATIONAL.value,
        "role": "the operational alert itself; states 11:24",
        "states": "11:24",
    },
    {
        "id": "MOIS-JUNGDAEBON-8",
        "label": "MOIS 중대본 8차 per-fire status table, 2025-03-29",
        "evidence_class": EvidenceClass.PRIMARY_OPERATIONAL.value,
        "role": "assigns 3.22 11:25 to all five Gyeongbuk counties",
        "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=156681469",
        "states": "3.22(토) 11:25",
    },
    {
        "id": "DERIVED-IGNITION-HULL",
        "label": "reported ignition = [11:24:00, 11:25:59] KST",
        "evidence_class": EvidenceClass.DERIVED.value,
        "role": "convex hull of the two conflicting primary readings; a weakening",
    },
    # --- the alert-access chain --------------------------------------
    {
        "id": "SAFEKOREA-UI",
        "label": "국민안전24 재난문자 search UI",
        "evidence_class": EvidenceClass.TERTIARY.value,
        "role": "retrieval surface; returns 전체 0 건 for the target window",
    },
    {
        "id": "DSSP-API",
        "label": "safetydata.go.kr DSSP-IF-00247 (alert API)",
        "evidence_class": EvidenceClass.PRIMARY_OPERATIONAL.value,
        "role": "authoritative record-level source; API_KEY_REQUIRED",
    },
    {
        "id": "SAFETYDATA-ARCHIVE",
        "label": "safetydata.go.kr /disaster-data/disasterNotification",
        "evidence_class": EvidenceClass.PRIMARY_OPERATIONAL.value,
        "role": "public archive of the same records; RETRIEVED, 1,688 records",
    },
    # --- the Andong arrival conflict ---------------------------------
    {
        "id": "ANDONG-PORTAL",
        "label": "안동시 대형산불 종합안내",
        "evidence_class": EvidenceClass.OFFICIAL_RETROSPECTIVE.value,
        "role": "retrospective; states 2025. 3. 24.(월) 17:02",
        "url": "https://www.andong.go.kr/portal/contents.do?mId=0616010000",
        "states": "2025. 3. 24.(월) 17:02",
    },
]

EDGES = [
    ("WIKI-KO", "NEWS-AGG", EdgeType.CITES,
     "tertiary used as a discovery aid, then left behind"),
    ("NEWS-AGG", "MOIS-PR-0322", EdgeType.QUOTES,
     "press quotes the ministry; the quote does not become the record"),
    ("MOIS-PR-0322", "CBS-UISEONG-151622", EdgeType.CONTRADICTS,
     "11시 24분경 vs 11:25 — both primary, both retained (C-01)"),
    ("CBS-UISEONG-151622", "CBS-ANDONG-151800", EdgeType.CONTRADICTS,
     "two counties, 98 seconds apart, disagree by one minute"),
    ("CBS-UISEONG-151622", "MOIS-JUNGDAEBON-8", EdgeType.CORROBORATES,
     "the central status table carries the same 11:25"),
    ("CBS-UISEONG-151622", "DERIVED-IGNITION-HULL", EdgeType.REPRODUCES,
     "contributes its reading to the hull"),
    ("CBS-ANDONG-151800", "DERIVED-IGNITION-HULL", EdgeType.REPRODUCES,
     "contributes its reading to the hull"),
    ("SAFEKOREA-UI", "DSSP-API", EdgeType.SUPERSEDES,
     "the UI's retention boundary makes it useless here; the API is authoritative"),
    ("DSSP-API", "SAFETYDATA-ARCHIVE", EdgeType.REPRODUCES,
     "the public archive publishes the same operational records, ungated"),
    ("MOIS-JUNGDAEBON-8", "ANDONG-PORTAL", EdgeType.CONTRADICTS,
     "3.22 11:25 vs 3.24 17:02 for Andong — different quantities (C-02)"),
]


def main() -> None:
    doc = {
        "note": (
            "Discovering a stronger source adds an edge; it never deletes the "
            "weaker node. Every claim keeps the chain that reached it."
        ),
        "nodes": NODES,
        "edges": [
            {"from": a, "to": b, "type": t.value, "note": n} for a, b, t, n in EDGES
        ],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    by_class: dict[str, int] = {}
    for n in NODES:
        by_class[n["evidence_class"]] = by_class.get(n["evidence_class"], 0) + 1
    print(f"{len(NODES)} nodes, {len(EDGES)} edges -> {OUT}")
    for c, k in sorted(by_class.items()):
        print(f"  {c:<24} {k}")
    print("\nedge types used:")
    for t in sorted({t.value for _, _, t, _ in EDGES}):
        print(f"  {t}")


if __name__ == "__main__":
    main()
