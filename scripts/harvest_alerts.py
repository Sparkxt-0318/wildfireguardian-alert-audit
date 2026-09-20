"""Harvest the public 재난문자 archive across the target window.

These are PRIMARY_OPERATIONAL records: the operational alerting system's own
published output, with send times to the second. They are the only
first-public-warning evidence this audit obtained without a credential.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wg_alert_audit.adapters.alert_archive import harvest  # noqa: E402
from wg_alert_audit.core.provenance import ProvenanceStore  # noqa: E402
from wg_alert_audit.core.model import AccessStatus, EvidenceClass  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "normalized" / "alerts_archive.jsonl"

# Day-by-day, because the archive is nationwide and a wide window paginates deep.
DAYS = [f"2025-03-{d:02d}" for d in range(21, 32)] + ["2025-04-01", "2025-04-02"]


def main() -> None:
    store = ProvenanceStore(ROOT / "data" / "raw")
    all_alerts = []
    seen = set()
    for day in DAYS:
        res = harvest(day, day, per_page=100, max_pages=30)
        fresh = [a for a in res.alerts if a.sn not in seen]
        for a in fresh:
            seen.add(a.sn)
        all_alerts.extend(fresh)
        print(
            f"  {day}  {res.status.value:<26} pages={res.pages_fetched:<3} "
            f"records={len(fresh)}",
            flush=True,
        )
        if res.status is not AccessStatus.RETRIEVED:
            print(f"      !! {res.reason}", flush=True)

    all_alerts.sort(key=lambda a: a.sent_raw)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for a in all_alerts:
            fh.write(json.dumps(a.to_json(), ensure_ascii=False) + "\n")

    # Store the corpus itself as an artifact so it carries a provenance record.
    store.put(
        content=OUT.read_bytes(),
        source_id="safetydata-archive-harvest",
        url="https://www.safetydata.go.kr/disaster-data/disasterNotification",
        content_type="application/x-ndjson",
        evidence_class=EvidenceClass.PRIMARY_OPERATIONAL,
        access_status=AccessStatus.RETRIEVED,
        language="ko",
        title="재난문자 archive harvest, 2025-03-21..2025-04-02",
        notes=f"{len(all_alerts)} records, nationwide, harvested day by day",
    )
    print(f"\ntotal {len(all_alerts)} alert records -> {OUT}")


if __name__ == "__main__":
    main()
