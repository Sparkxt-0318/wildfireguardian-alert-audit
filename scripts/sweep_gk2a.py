"""Probe GK2A L2 FF observation slots across the target window.

Establishes *observation availability* - which slots the operational forest-fire
detection product actually covered - using the credential-free NMSC public
product tree. This is one of the three things the research question asks about,
and it is obtainable without any credential.

It is NOT a fire detection survey: a rendered PNG is not pixel data.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wg_alert_audit.adapters.gk2a import probe_slot  # noqa: E402

KST = timezone(timedelta(hours=9))
OUT = Path(__file__).resolve().parents[1] / "data" / "normalized" / "gk2a_ff_slots.jsonl"

# Target window (docs/DECISIONS.md D-005), expressed in UTC.
START = datetime(2025, 3, 21, 0, 0, tzinfo=KST).astimezone(timezone.utc)
END = datetime(2025, 4, 5, 0, 0, tzinfo=KST).astimezone(timezone.utc)


def plan() -> list[tuple[datetime, str, str]]:
    """Stratified sample. The strata are declared here so COVERAGE.md can cite them."""
    jobs: list[tuple[datetime, str, str]] = []

    # Stratum A: hourly KO probes across the whole window -> coverage envelope.
    t = START
    while t < END:
        jobs.append((t, "KO", "A_hourly_envelope"))
        t += timedelta(hours=1)

    # Stratum B: native 2-minute cadence over one 6-hour block, to verify that
    # the documented KO cadence actually held during the event.
    t = datetime(2025, 3, 25, 0, 0, tzinfo=timezone.utc)
    for _ in range(180):
        jobs.append((t, "KO", "B_native_cadence"))
        t += timedelta(minutes=2)

    # Stratum C: the documented 00:40-00:50 UTC wheel-offload gap, on three
    # separate days. A miss here is expected and must not be read as an outage.
    for day in (22, 25, 28):
        for mm in (36, 38, 40, 42, 44, 46, 48, 50, 52, 54):
            jobs.append(
                (datetime(2025, 3, day, 0, mm, tzinfo=timezone.utc), "KO", "C_known_gap")
            )

    # Stratum D: East Asia + Full Disk at 10-minute cadence on the peak day.
    for area in ("EA", "FD"):
        t = datetime(2025, 3, 25, 0, 0, tzinfo=timezone.utc)
        for _ in range(48):
            jobs.append((t, area, "D_wider_areas"))
            t += timedelta(minutes=30)

    return jobs


def run_one(job):
    t, area, stratum = job
    s = probe_slot(t, area)
    return {
        "observed_utc": t.isoformat(),
        "observed_kst": t.astimezone(KST).isoformat(),
        "area": area,
        "stratum": stratum,
        "available": s.available,
        "access_status": s.access_status.value,
        "byte_length": s.byte_length,
        "content_type": s.content_type,
        "sha256": s.sha256,
        "url": s.url,
    }


def main() -> None:
    jobs = plan()
    print(f"probing {len(jobs)} GK2A L2 FF observation slots", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, rec in enumerate(pool.map(run_one, jobs), 1):
            results.append(rec)
            if i % 100 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    avail = sum(1 for r in results if r["available"])
    print(f"done: {avail}/{len(results)} slots available -> {OUT}")


if __name__ == "__main__":
    main()
