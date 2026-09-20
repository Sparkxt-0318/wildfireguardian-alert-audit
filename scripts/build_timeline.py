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

from wg_alert_audit.core import gazetteer as gz  # noqa: E402
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

#: Counties at the centre of the complex.
TARGET_COUNTIES = {"의성군", "안동시", "청송군", "영양군", "영덕군"}

#: Every Gyeongbuk municipality is mappable, not just the five. Restricting the
#: mapping to TARGET_COUNTIES silently produced issuer_county=None for 포항시,
#: which issued alerts about this fire.
def issuer_county(issuer: str) -> str | None:
    """Map an issuing authority to a si/gun, where it names one."""
    norm = issuer.strip()
    for suffix in ("청", "시청", "군청"):
        if norm.endswith(suffix) and len(norm) > len(suffix):
            norm = norm[: -len("청")]
            break
    for canonical, aliases in gz.SI_GUN.items():
        if norm == canonical or norm in aliases:
            return canonical
    return None


#: A record enters the timeline as a warning ABOUT THIS FIRE only if its text
#: is about fire. Stamping every alert from a target county as
#: `first_public_warning` put PM2.5 air-quality advisories into the wildfire
#: timeline - a modelling error the inclusion rules did not catch, because
#: INCLUSION_RULES I-4/I-5 gate on time and place but never on topic.
FIRE_TOPIC_TOKENS = ("산불", "화재", "불길", "연기", "화선", "진화", "대피")


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
        # Every locality named, not merely the first in each clause.
        body_counties: list[str] = []
        eups: list[str] = []
        non_localities: list[str] = []
        for c in clause_results:
            for x in c.all_si_gun:
                if x not in body_counties:
                    body_counties.append(x)
            for x in c.all_eup_myeon:
                if x not in eups:
                    eups.append(x)
            for x in c.all_non_localities:
                if x not in non_localities:
                    non_localities.append(x)

        # In scope when one of the five complex counties issued the alert, or
        # when any Gyeongbuk municipality issued one that NAMES a complex
        # county - which is how 포항시's alert about the 의성 fire qualifies
        # while 김천시's generic burn-ban notice does not.
        in_area = ic in TARGET_COUNTIES or bool(
            TARGET_COUNTIES & set(body_counties)
        )
        on_topic = any(t in text for t in FIRE_TOPIC_TOKENS)
        if not (in_area and on_topic):
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
            # Every road/facility token seen, whether or not it embedded a
            # place name. Recording only the dangerous ones made the field
            # vacuous as evidence: it was empty whether a road was correctly
            # rejected or simply never noticed.
            "non_locality_tokens": non_localities,
            "roads_mentioned_not_localities": [
                c.geography.road for c in clause_results if c.geography.road
            ],
            "raw_text": text,
            "source_id": r["record_id"],
            "provenance": r["retrieval_provenance"],
            # Every clock time written in the message body, verbatim, with no
            # quantity asserted. Some alerts state a time without saying what
            # happened at it - e.g. 「(대피명령발령) 11:25 안평면 괴산리 산61 산불
            # 확산」, where 11:25 is almost certainly the ignition minute but the
            # text says only 확산 (spread). Recording the datum without naming
            # the quantity keeps it available to a human without the pipeline
            # inferring an ignition report the Korean does not make.
            "stated_times_in_text": [
                {"verbatim": tm.raw, "hh_mm": f"{tm.hour:02d}:{tm.minute:02d}"}
                for tm in find_times(text)
            ],
        }

        # Claim 1: the alert was sent. Always true of every record.
        events.append(
            {
                **base,
                "quantity": Quantity.FIRST_PUBLIC_WARNING.value,
                "time_role": "ALERT_SEND_TIME",
                "evidence_class": "PRIMARY_OPERATIONAL",
                "interval_kst": r["send_interval"],
                "labels": sorted(set(quantities)),
                "is_evacuation_order": Quantity.EVACUATION_ORDER.value in quantities,
                # Superset: an imperative instruction to leave, whether or not
                # a formal 대피명령 was declared.
                "is_evacuation_directive": is_evacuation_directive(text),
            }
        )

        # Claim 2: where the text states an ignition time, record it as a
        # REPORTED ignition at the text's own resolution - never as an
        # observation, and never merged with the send time.
        states_ignition = (
            Quantity.REPORTED_IGNITION.value in quantities
            or Quantity.IGNITION.value in quantities
            or "발화지점" in text
        )
        if states_ignition:
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
                        "labels": sorted(set(quantities)),
                        "is_evacuation_order": Quantity.EVACUATION_ORDER.value
                        in quantities,
                        "is_evacuation_directive": is_evacuation_directive(text),
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
