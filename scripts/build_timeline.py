"""Turn harvested alert records into provenance-preserving claims.

Each alert yields at least one claim - the ALERT_SEND_TIME, which is
PRIMARY_OPERATIONAL and carries second resolution. Alerts whose text *states* an
ignition time yield a second, weaker claim: a reported ignition, at whatever
resolution the text used, and explicitly NOT an observation of ignition.

Geography comes from the token/context-aware matcher, so an alert mentioning an
expressway does not acquire that expressway's endpoint counties.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wg_alert_audit.core.geography import extract  # noqa: E402
from wg_alert_audit.core.intervals import KST, TimeInterval  # noqa: E402
from wg_alert_audit.core.korean import (  # noqa: E402
    find_times,
    is_evacuation_directive,
    parse as parse_ko,
)
from wg_alert_audit.core.model import Quantity  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ALERTS = ROOT / "data" / "normalized" / "alerts_archive.jsonl"
OUT = ROOT / "data" / "timeline" / "timeline.json"

TARGET_COUNTIES = {"의성군", "안동시", "청송군", "영양군", "영덕군"}

#: Issuers whose alerts concern the Gyeongbuk complex.
TARGET_ISSUERS = {
    "의성군", "의성군청", "안동시", "청송군", "영양군", "영덕군", "경상북도",
}


def issuer_county(issuer: str) -> str | None:
    """Map an issuing authority to a county, where it names one."""
    norm = issuer.replace("청", "") if issuer.endswith("군청") else issuer
    for c in TARGET_COUNTIES:
        if norm == c or norm == c[:-1]:
            return c
    return None


def build() -> dict:
    rows = [
        json.loads(l)
        for l in ALERTS.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]

    events: list[dict] = []
    for r in rows:
        text = r["message_text"]
        issuer = r["issuing_authority"]
        ic = issuer_county(issuer)

        # Geography: the issuer's own county is the alert's target when the
        # issuer is a county government. Message-body geography is extracted
        # separately and never overrides it.
        clause_results = extract(text)
        body_counties = sorted(
            {c.geography.si_gun for c in clause_results if c.geography.si_gun}
        )
        roads = sorted({c.geography.road for c in clause_results if c.geography.road})
        eups = sorted(
            {c.geography.eup_myeon_dong for c in clause_results
             if c.geography.eup_myeon_dong}
        )

        relevant = bool(ic) or bool(TARGET_COUNTIES & set(body_counties))
        if not relevant:
            continue

        labels = parse_ko(text)
        quantities = [q.value for q in labels.quantities]

        base = {
            "record_id": r["record_id"],
            "send_time_kst": r["send_time_kst"],
            "send_interval_kst": r["send_interval"],
            "issuing_authority": issuer,
            "issuer_county": ic,
            "body_counties": body_counties,
            "body_eup_myeon": eups,
            "roads_mentioned_not_localities": roads,
            "raw_text": text,
            "source_id": r["record_id"],
            "provenance": r["retrieval_provenance"],
        }

        # Claim 1: the alert was sent. Always true of every record.
        events.append(
            {
                **base,
                "quantity": Quantity.FIRST_PUBLIC_WARNING.value,
                "time_role": "ALERT_SEND_TIME",
                "evidence_class": "PRIMARY_OPERATIONAL",
                "interval_kst": r["send_interval"],
                "labels": quantities,
                "is_evacuation_order": Quantity.EVACUATION_ORDER.value in quantities,
                # Superset: an imperative instruction to leave, whether or not
                # a formal 대피명령 was declared.
                "is_evacuation_directive": is_evacuation_directive(text),
            }
        )

        # Claim 2: where the text states an ignition time, record it as a
        # REPORTED ignition at the text's own resolution - never as an
        # observation, and never merged with the send time.
        if Quantity.IGNITION.value in quantities or "발생" in text:
            for tm in find_times(text):
                sent = datetime.fromisoformat(r["send_time_kst"])
                stated = sent.replace(
                    hour=tm.hour, minute=tm.minute, second=0, microsecond=0
                )
                if stated > sent:  # a stated time after the send is not this event
                    continue
                if (sent - stated) > timedelta(hours=14):
                    continue
                events.append(
                    {
                        **base,
                        "quantity": Quantity.REPORTED_IGNITION.value,
                        "time_role": "REPORT_TIME",
                        "evidence_class": "PRIMARY_OPERATIONAL",
                        "interval_kst": TimeInterval.at_minute(stated).format(KST),
                        "stated_time_verbatim": tm.raw,
                        "labels": quantities,
                        "note": (
                            "an authority's stated ignition time carried inside an "
                            "operational alert. It is a REPORT of ignition, not an "
                            "observation of it, and its resolution is the minute "
                            "the text used."
                        ),
                    }
                )

    events.sort(key=lambda e: (e["send_time_kst"], e["quantity"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "target_window_kst": "2025-03-21T00:00+09:00 .. 2025-04-05T00:00+09:00",
        "source": "safetydata.go.kr public 재난문자 archive",
        "counties": sorted(TARGET_COUNTIES),
        "event_count": len(events),
        "events": events,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


if __name__ == "__main__":
    d = build()
    print(f"{d['event_count']} claims -> {OUT}")
