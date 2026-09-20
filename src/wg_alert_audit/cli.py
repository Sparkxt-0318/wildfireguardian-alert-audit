"""Command-line interface for the evidence audit.

Every subcommand reports access status honestly and never converts a failure
into a claim about what exists in the world.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .adapters import alerts as alerts_mod
from .adapters import firms as firms_mod
from .adapters import gk2a as gk2a_mod
from .core import credentials
from .core.geography import attribute, extract
from .core.korean import find_times, parse as parse_korean
from .core.model import AccessStatus, EvidenceClass
from .core.provenance import ProvenanceStore

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]


def _root(args) -> Path:
    return Path(args.data_root) if args.data_root else ROOT / "data"


# -- sources ------------------------------------------------------------


def cmd_sources(args) -> int:
    """Inventory every source and its current access status."""
    print("CREDENTIALS (status only; values are never read out)\n")
    for r in credentials.status_table():
        print(f"  {r['env_var']:<26} {r['credential_status']:<10} {r['service']}")
        if r["aliases"] != "-":
            print(f"  {'':26} aliases: {r['aliases']}")
    print("\nEMERGENCY ALERT ROUTES (긴급재난문자)\n")
    for r in alerts_mod.credential_report():
        print(f"  {r['route']:<16} {r['credential_status']:<26} {r['name']}")
        print(f"  {'':16} portal: {r['portal']}")
    print("\nFIRMS SOURCES APPROPRIATE FOR MARCH 2025\n")
    for s in firms_mod.HISTORICAL_SOURCES:
        print(f"  {s}")
    print("\n  Rolling NRT sources that will NOT cover March 2025")
    print("  (an empty result from these is a window artefact, not an absence):")
    for s in firms_mod.ROLLING_NRT_SOURCES:
        print(f"    {s}")
    print("\nGK2A L2 FOREST FIRE (산불탐지)\n")
    for k, v in gk2a_mod.netcdf_access_note().items():
        print(f"  {k:<20} {v}")
    print(
        f"\n  Credential-free product tree: {gk2a_mod.NMSC_IMG_ROOT}"
        "\n  (rendered PNG twins; establishes observation availability, not pixel data)"
    )
    return 0


# -- retrieve -----------------------------------------------------------


def cmd_retrieve(args) -> int:
    """Attempt retrieval and record the real outcome."""
    if args.target in ("gk2a", "all"):
        print("== GK2A L2 FF observation slots ==")
        start = datetime.fromisoformat(args.start).replace(tzinfo=KST)
        end = datetime.fromisoformat(args.end).replace(tzinfo=KST)
        slots = gk2a_mod.slots_between(
            start.astimezone(timezone.utc),
            end.astimezone(timezone.utc),
            args.area,
            step_minutes=args.step,
        )
        avail = 0
        for t in slots:
            s = gk2a_mod.probe_slot(t, args.area)
            avail += bool(s.available)
            print(
                f"  {s.observed_kst:%Y-%m-%d %H:%M} KST  "
                f"{'AVAILABLE' if s.available else s.access_status.value:<20} "
                f"{s.byte_length:>8}B"
            )
        print(f"  -> {avail}/{len(slots)} slots available")

    if args.target in ("firms", "all"):
        print("\n== NASA FIRMS active fire ==")
        for src in firms_mod.HISTORICAL_SOURCES:
            r = firms_mod.retrieve(src, date.fromisoformat(args.start))
            print(f"  {src:<20} {r.status.value}")
            print(f"    {r.reason}")
            if r.note:
                print(f"    {r.note}")

    if args.target in ("alerts", "all"):
        print("\n== Emergency alerts (긴급재난문자) ==")
        for route in alerts_mod.ENDPOINTS:
            st, reason = alerts_mod.status_without_credential(route)
            print(f"  {route:<16} {st.value}")
            print(f"    {reason}")
    return 0


# -- ingest / import ----------------------------------------------------


def cmd_import(args) -> int:
    """Import a legitimately downloaded artifact with full provenance."""
    path = Path(args.path)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 2
    store = ProvenanceStore(_root(args) / "raw")
    content = path.read_bytes()
    art = store.put(
        content=content,
        source_id=args.source_id or path.stem,
        url=f"file://{path.resolve()}",
        content_type=args.content_type,
        evidence_class=EvidenceClass(args.evidence_class),
        access_status=AccessStatus.RETRIEVED,
        acquisition_method="manual_import",
        import_note=args.note,
        language=args.language,
    )
    print(f"imported {path.name}")
    print(f"  sha256          {art.sha256}")
    print(f"  evidence_class  {art.evidence_class.value}")
    print(f"  method          manual_import (same provenance treatment as a fetch)")

    if args.kind == "alerts":
        records = alerts_mod.load_manual_export(str(path))
        out = _root(args) / "normalized" / "alerts.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r.to_json(), ensure_ascii=False) + "\n")
        print(f"  normalised      {len(records)} alert records -> {out}")
    elif args.kind == "firms":
        dets = firms_mod.parse_csv(
            content.decode("utf-8", errors="replace"), args.source_id or "manual"
        )
        print(f"  parsed          {len(dets)} detections")
    return 0


# -- analysis -----------------------------------------------------------


def cmd_parse(args) -> int:
    """Show what the parsers extract from a piece of Korean text."""
    text = args.text
    print(f"text: {text}\n")
    print("event labels:")
    for m in parse_korean(text).labels:
        q = m.quantity.value if m.quantity else "(non-event)"
        print(f"  {m.raw:<12} -> {q:<24} {m.gloss}")
    print("\ntime mentions (no role assigned - that is an evidentiary decision):")
    for t in find_times(text):
        print(f"  {t.raw:<14} -> {t.hour:02d}:{t.minute:02d}")
    print("\ngeography, per clause:")
    for r in extract(text):
        g = r.geography
        print(f"  [{r.clause}]")
        print(
            f"    si_gun={g.si_gun} eup={g.eup_myeon_dong} "
            f"road={g.road} natural={g.named_place}"
        )
        if r.note:
            print(f"    note: {r.note}")
    g = attribute(text)
    print(f"\nwhole-text attribution: {g.describe() if g else 'REFUSED (ambiguous or none)'}")
    return 0


def cmd_verify(args) -> int:
    """Re-hash the stored corpus and report integrity problems."""
    store = ProvenanceStore(_root(args) / "raw")
    recs = store.records()
    problems = store.verify()
    print(f"artifacts in ledger: {len(recs)}")
    drift = [
        l for l in store.drift_log.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    print(f"SOURCE_DRIFT events: {len(drift)}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("all blobs verify against their recorded SHA-256")
    return 0


def cmd_gaps(args) -> int:
    p = ROOT / "reports" / "EVIDENCE_GAPS.md"
    print(p.read_text(encoding="utf-8") if p.exists() else "not generated yet")
    return 0


def cmd_lead_time(args) -> int:
    p = ROOT / "reports" / "LEAD_TIME_RESULTS.md"
    print(p.read_text(encoding="utf-8") if p.exists() else "not generated yet")
    return 0


def cmd_timeline(args) -> int:
    p = _root(args) / "timeline" / "timeline.json"
    if not p.exists():
        print("timeline not built yet")
        return 1
    data = json.loads(p.read_text(encoding="utf-8"))
    events = data.get("events", [])
    if args.county:
        events = [e for e in events if e.get("issuer_county") == args.county]
    if args.orders_only:
        events = [e for e in events if e.get("is_evacuation_order")]

    for e in events[: args.limit]:
        flag = "ORDER" if e.get("is_evacuation_order") else (
            "directive" if e.get("is_evacuation_directive") else ""
        )
        where = e.get("issuer_county") or "-"
        detail = " ".join(e.get("body_eup_myeon", [])) or ""
        print(
            f"  {e['send_time_kst'][:19]}  {where:<7} {e['quantity']:<22} {flag}"
        )
        if detail:
            print(f"      localities: {detail}")
        print(f"      {e['raw_text'][:96]}")
        print(f"      [{e['source_id']}] {e['evidence_class']}")
    print(f"\n  {len(events)} claims" + (f" (showing {args.limit})" if len(events) > args.limit else ""))
    return 0


def cmd_report(args) -> int:
    for name in (
        "CURRENT_EVIDENCE_VERDICT.md",
        "SOURCE_ACCESS_STATUS.md",
        "EVIDENCE_GAPS.md",
        "CONTRADICTIONS.md",
        "COVERAGE.md",
        "MANUAL_VERIFICATION.md",
        "LEAD_TIME_RESULTS.md",
        "FRESH_REBUILD_VERDICT.md",
    ):
        p = ROOT / "reports" / name
        print(f"  {'OK ' if p.exists() else '-- '} {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="wg-alert-audit",
        description="Historical evidence audit of the March 2025 Gyeongbuk wildfires",
    )
    ap.add_argument("--data-root", default=None, help="override the data/ directory")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="inventory sources and access status").set_defaults(
        func=cmd_sources
    )

    p = sub.add_parser("retrieve", help="attempt retrieval, record real status")
    p.add_argument("target", choices=["gk2a", "firms", "alerts", "all"])
    p.add_argument("--start", default="2025-03-21")
    p.add_argument("--end", default="2025-03-22")
    p.add_argument("--area", default="KO", choices=list(gk2a_mod.AREAS))
    p.add_argument("--step", type=int, default=60, help="minutes between probes")
    p.set_defaults(func=cmd_retrieve)

    p = sub.add_parser("import", help="import a legitimately downloaded artifact")
    p.add_argument("path")
    p.add_argument("--kind", default="source", choices=["alerts", "firms", "gk2a", "source"])
    p.add_argument("--source-id", default="")
    p.add_argument("--content-type", default="application/octet-stream")
    p.add_argument("--evidence-class", default="PRIMARY_OPERATIONAL",
                   choices=[e.value for e in EvidenceClass])
    p.add_argument("--language", default="ko")
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("parse", help="show parser output for Korean text")
    p.add_argument("text")
    p.set_defaults(func=cmd_parse)

    sub.add_parser("verify", help="re-hash the corpus").set_defaults(func=cmd_verify)
    sub.add_parser("gaps", help="show the evidence-gap registry").set_defaults(func=cmd_gaps)
    sub.add_parser("lead-time", help="show lead-time results").set_defaults(func=cmd_lead_time)
    p = sub.add_parser("timeline", help="show the reconstructed timeline")
    p.add_argument("--county", default=None, help="filter to one issuing county")
    p.add_argument("--orders-only", action="store_true",
                   help="only formally declared 대피명령")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_timeline)
    sub.add_parser("ingest", help="alias of import for a directory").set_defaults(func=cmd_import)
    sub.add_parser("report", help="list generated reports").set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
