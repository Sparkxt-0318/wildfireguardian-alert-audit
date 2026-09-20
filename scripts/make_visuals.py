"""Render the audit's visualisations.

Design constraint from the parent project's CLAUDE.md: this is a life-safety
evidence tool, so legibility and WCAG AA contrast take priority over polish.
Colours are chosen to stay distinguishable in greyscale and for the common
forms of colour-vision deficiency, and every encoding is also labelled in text.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOTS = ROOT / "data" / "normalized" / "gk2a_ff_slots.jsonl"
OUT = ROOT / "visualizations"

INK = "#1a1a1a"
MUTED = "#5c5c5c"
GRID = "#d4d4d4"
AVAIL = "#1b5e20"      # dark green - product retrieved
GAP = "#b71c1c"        # dark red - documented instrument gap
UNKNOWN = "#9e9e9e"    # grey - not probed
BG = "#ffffff"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_timeline() -> str:
    recs = [json.loads(l) for l in SLOTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    hourly = [r for r in recs if r["stratum"] == "A_hourly_envelope" and r["area"] == "KO"]

    by_day: dict[str, dict[int, bool]] = defaultdict(dict)
    for r in hourly:
        kst = datetime.fromisoformat(r["observed_kst"])
        by_day[kst.strftime("%Y-%m-%d")][kst.hour] = r["available"]
    days = sorted(by_day)

    cell, left, top = 26, 130, 118
    w = left + 24 * cell + 190
    h = top + len(days) * cell + 150

    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{w}" height="{h}" fill="{BG}"/>',
        f'<text x="24" y="38" font-size="19" font-weight="700" fill="{INK}">'
        'GK2A L2 Forest Fire product: observation-slot availability</text>',
        f'<text x="24" y="60" font-size="13" fill="{MUTED}">'
        'March 2025 Gyeongbuk wildfires — hourly probe of the Korea-area (KO) '
        'product tree, 2025-03-21 to 2025-04-04 KST</text>',
        f'<text x="24" y="80" font-size="12" fill="{MUTED}">'
        'A filled cell means the operational fire-detection product was published '
        'for that observation slot. It does NOT mean a fire was detected.</text>',
        f'<text x="24" y="98" font-size="12" fill="{MUTED}">'
        'Source: nmsc.kma.go.kr public product tree, retrieved 2026-09-20, no credential required.</text>',
    ]

    for hh in range(0, 24, 2):
        x = left + hh * cell + cell / 2
        p.append(
            f'<text x="{x:.0f}" y="{top - 10}" font-size="11" fill="{MUTED}" '
            f'text-anchor="middle">{hh:02d}</text>'
        )
    p.append(
        f'<text x="{left + 12 * cell:.0f}" y="{top - 30}" font-size="12" '
        f'fill="{INK}" text-anchor="middle" font-weight="600">hour of day (KST)</text>'
    )

    for i, day in enumerate(days):
        y = top + i * cell
        p.append(
            f'<text x="{left - 12}" y="{y + cell * 0.68:.0f}" font-size="11.5" '
            f'fill="{INK}" text-anchor="end">{day}</text>'
        )
        for hh in range(24):
            x = left + hh * cell
            state = by_day[day].get(hh)
            fill = UNKNOWN if state is None else (AVAIL if state else GAP)
            p.append(
                f'<rect x="{x}" y="{y}" width="{cell - 3}" height="{cell - 3}" '
                f'fill="{fill}" stroke="{GRID}" stroke-width="0.5" rx="2"/>'
            )

    ly = top + len(days) * cell + 34
    p.append(
        f'<text x="24" y="{ly}" font-size="12" font-weight="600" fill="{INK}">Legend</text>'
    )
    for j, (colour, label) in enumerate(
        [
            (AVAIL, "product retrieved (HTTP 200, image/png, >4 KiB)"),
            (GAP, "no product for this slot (NO_RELEVANT_RECORD)"),
            (UNKNOWN, "not probed in this stratum"),
        ]
    ):
        yy = ly + 18 + j * 20
        p.append(
            f'<rect x="24" y="{yy - 10}" width="14" height="14" fill="{colour}" '
            f'stroke="{GRID}" rx="2"/>'
            f'<text x="46" y="{yy + 1}" font-size="11.5" fill="{INK}">{esc(label)}</text>'
        )

    p.append(
        f'<text x="24" y="{ly + 96}" font-size="11.5" fill="{MUTED}">'
        '635 of 650 probed slots retrieved. All 15 misses fall in 00:40–00:48 UTC, '
        'the documented daily wheel-offload gap.</text>'
    )
    p.append("</svg>")
    return "\n".join(p)


def build_evidence_map() -> str:
    """Evidence availability by class and quantity. The gaps are the point."""
    rows = [
        ("first sensor detection", "REMOTE_SENSING", "available", "GK2A FF slots retrieved"),
        ("observation availability", "REMOTE_SENSING", "available", "635/650 slots"),
        ("VIIRS/MODIS detection", "REMOTE_SENSING", "credential", "FIRMS_MAP_KEY"),
        ("first public warning", "PRIMARY_OPERATIONAL", "credential", "SAFETYDATA_API_KEY"),
        ("evacuation order", "PRIMARY_OPERATIONAL", "credential", "alert record gated"),
        ("ignition", "PHYSICAL", "unobserved", "not directly observed"),
        ("fire arrival", "PHYSICAL", "unobserved", "no minute-scale truth"),
        ("road impact", "PHYSICAL", "unobserved", "no systematic record"),
        ("resident receipt", "PHYSICAL", "unobserved", "not recorded anywhere"),
    ]
    colours = {
        "available": AVAIL,
        "credential": "#e65100",
        "unobserved": MUTED,
    }
    rh, left, top = 34, 250, 122
    w, h = 940, top + len(rows) * rh + 128

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{w}" height="{h}" fill="{BG}"/>',
        f'<text x="24" y="38" font-size="19" font-weight="700" fill="{INK}">'
        'Evidence map: what can and cannot be established</text>',
        f'<text x="24" y="60" font-size="13" fill="{MUTED}">'
        'March 2025 Gyeongbuk wildfires — by quantity, as of 2026-09-20</text>',
        f'<text x="24" y="82" font-size="12" fill="{MUTED}">'
        'Orange is not absence. It marks data that exists behind a credential this '
        'audit did not hold.</text>',
        f'<text x="24" y="104" font-size="11.5" fill="{MUTED}">'
        'A warning lead time needs one green row on the alert side and one on the '
        'reference side, at compatible geography. There is none.</text>',
    ]

    for i, (quantity, cls, state, note) in enumerate(rows):
        y = top + i * rh
        p.append(
            f'<text x="{left - 14}" y="{y + 20}" font-size="12.5" fill="{INK}" '
            f'text-anchor="end">{esc(quantity)}</text>'
        )
        p.append(
            f'<rect x="{left}" y="{y + 4}" width="250" height="22" '
            f'fill="{colours[state]}" rx="3"/>'
        )
        p.append(
            f'<text x="{left + 125}" y="{y + 19}" font-size="11" fill="#ffffff" '
            f'text-anchor="middle" font-weight="600">{esc(state.upper())}</text>'
        )
        p.append(
            f'<text x="{left + 266}" y="{y + 19}" font-size="11.5" fill="{MUTED}">'
            f'{esc(cls)} — {esc(note)}</text>'
        )

    ly = top + len(rows) * rh + 30
    for j, (state, label) in enumerate(
        [
            ("available", "retrieved by this audit"),
            ("credential", "exists, credential required — NOT absence"),
            ("unobserved", "not observed by any accessible source"),
        ]
    ):
        yy = ly + j * 22
        p.append(
            f'<rect x="24" y="{yy - 11}" width="14" height="14" '
            f'fill="{colours[state]}" rx="2"/>'
            f'<text x="46" y="{yy}" font-size="11.5" fill="{INK}">{esc(label)}</text>'
        )
    p.append("</svg>")
    return "\n".join(p)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "timeline.svg").write_text(build_timeline(), encoding="utf-8")
    (OUT / "evidence_map.svg").write_text(build_evidence_map(), encoding="utf-8")
    print(f"wrote {OUT/'timeline.svg'}")
    print(f"wrote {OUT/'evidence_map.svg'}")


if __name__ == "__main__":
    main()
