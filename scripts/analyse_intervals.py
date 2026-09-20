"""Compute the alert-timing intervals the evidence actually supports.

Deliberately does NOT compute a warning lead time. A warning lead time is the
gap between a warning and the hazard arriving, and no accessible source places
fire at a named locality at minute scale. What the evidence does support is a
set of alert-timing intervals, each named for exactly what it measures.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wg_alert_audit.core.intervals import KST, TimeInterval  # noqa: E402
from wg_alert_audit.core.model import Quantity  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TL = ROOT / "data" / "timeline" / "timeline.json"
OUT = ROOT / "data" / "timeline" / "intervals.json"

COUNTIES = ["의성군", "안동시", "청송군", "영양군", "영덕군"]

#: The reported-ignition interval, as the hull of the two conflicting primary
#: records (reports/CONTRADICTIONS.md C-01). Not averaged.
REPORTED_IGNITION = TimeInterval(
    datetime(2025, 3, 22, 11, 24, 0, tzinfo=KST).timestamp(),
    datetime(2025, 3, 22, 11, 25, 59, tzinfo=KST).timestamp(),
)


def fmt(seconds: float) -> str:
    """Format a duration. Sign is carried explicitly.

    Python's floor division rounds toward negative infinity, so a naive
    ``s // 3600`` renders -2392 s (39m52s before) as "-1h20m08s". The magnitude
    is formatted from ``abs`` and the sign prepended.
    """
    sign = "-" if seconds < 0 else ""
    s = int(abs(seconds))
    return f"{sign}{s // 3600}h{(s % 3600) // 60:02d}m{s % 60:02d}s"


def main() -> None:
    ev = json.loads(TL.read_text(encoding="utf-8"))["events"]

    # "First alert about this fire" is decided by what the alert is FOR, not by
    # whether the word 산불 appears in it. Testing for the word selects the
    # wrong record in four counties out of five: three pick up the same
    # province-wide burn-ban boilerplate, and one picks up an expressway
    # closure notice. classify_alert_purpose() separates a warning about a
    # burning fire from a prevention advisory, a road closure and a utility
    # notice - all of which mention 산불.
    #
    # Note there is deliberately NO ignition-time floor here. An earlier
    # version filtered to alerts sent at or after the reported ignition, which
    # made the metric structurally incapable of returning a negative value. If
    # an authority warned before the stated ignition minute, that is a finding,
    # not something to filter away.
    warnings = [e for e in ev if e.get("warns_about_an_incident")]

    results = {"counties": {}, "generated": datetime.now(timezone.utc).isoformat()}

    for county in COUNTIES:
        mine = sorted(
            (e for e in warnings if e["issuer_county"] == county),
            key=lambda e: e["send_time_kst"],
        )
        if not mine:
            continue
        first = mine[0]
        orders = [e for e in mine if e.get("is_evacuation_order")]
        first_order = orders[0] if orders else None

        ft = datetime.fromisoformat(first["send_time_kst"])
        first_iv = TimeInterval.at_second(ft)
        # reported ignition -> first public warning by this authority
        gap = first_iv - REPORTED_IGNITION

        entry = {
            "county": county,
            "alerts_issued": len(mine),
            "evacuation_orders": len(orders),
            "first_alert_kst": first["send_time_kst"],
            "first_alert_text": first["raw_text"],
            "first_alert_record_id": first["record_id"],
            "reported_ignition_to_first_alert": {
                "interval": gap.format_duration(),
                "lower_seconds": gap.lower,
                "upper_seconds": gap.upper,
                "lower_h": fmt(gap.lower),
                "upper_h": fmt(gap.upper),
                "kind": "REPORTED_IGNITION -> FIRST_PUBLIC_WARNING by this authority",
                "caveat": (
                    "NOT a warning lead time. It measures the gap between an "
                    "authority's own stated ignition time and its first public "
                    "alert. It says nothing about where the fire was, and "
                    "therefore nothing about how much time anyone had."
                ),
            },
        }

        if first_order:
            ot = datetime.fromisoformat(first_order["send_time_kst"])
            order_iv = TimeInterval.at_second(ot)
            to_order = order_iv - REPORTED_IGNITION
            first_to_order = order_iv - first_iv
            entry["first_evacuation_order"] = {
                "kst": first_order["send_time_kst"],
                "record_id": first_order["record_id"],
                "text": first_order["raw_text"],
                "reported_ignition_to_first_order": {
                    "interval": to_order.format_duration(),
                    "lower_h": fmt(to_order.lower),
                    "upper_h": fmt(to_order.upper),
                },
                "first_alert_to_first_order": {
                    "interval": first_to_order.format_duration(),
                    "exact": fmt(first_to_order.lower),
                    "note": (
                        "both endpoints are second-resolution PRIMARY_OPERATIONAL "
                        "records, so this interval is exact"
                    ),
                },
            }

        # Escalation sequence: consecutive evacuation orders.
        seq = []
        for a, b in zip(orders, orders[1:]):
            ta = datetime.fromisoformat(a["send_time_kst"])
            tb = datetime.fromisoformat(b["send_time_kst"])
            seq.append(
                {
                    "from": a["send_time_kst"],
                    "to": b["send_time_kst"],
                    "gap": fmt((tb - ta).total_seconds()),
                }
            )
        entry["order_escalation_gaps"] = seq[:40]
        results["counties"][county] = entry

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    for c, e in results["counties"].items():
        print(f"\n=== {c} ===")
        print(f"  alerts {e['alerts_issued']:>3}   evacuation orders {e['evacuation_orders']:>3}")
        print(f"  first alert      {e['first_alert_kst'][:19]}")
        g = e["reported_ignition_to_first_alert"]
        print(f"  reported ignition -> first alert : [{g['lower_h']}, {g['upper_h']}]")
        if "first_evacuation_order" in e:
            fo = e["first_evacuation_order"]
            print(f"  first evac order {fo['kst'][:19]}")
            o = fo["reported_ignition_to_first_order"]
            print(f"  reported ignition -> first order : [{o['lower_h']}, {o['upper_h']}]")
            print(f"  first alert -> first order       : {fo['first_alert_to_first_order']['exact']} (exact)")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
