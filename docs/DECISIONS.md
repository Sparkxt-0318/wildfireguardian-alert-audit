# Decisions log

Append-only. Each entry: context, decision, consequence.

---

## D-001 — Fresh rebuild, prior work treated as untrusted
**Date:** 2026-09-20
**Context:** A previous attempt at this repository was reported. The remote
`Sparkxt-0318/wildfireguardian-alert-audit` was inspected at the start of this
run: `git ls-remote origin` returned **no refs**, and the local clone had **no
commits**. No prior implementation, report, parser, or conclusion exists in this
repository to inherit from or to archive.
**Decision:** Build from first principles. The protocol documents in `docs/` were
written before any inspection of external prior work. Nothing was carried over.
**Consequence:** There is no `archive/alert-audit-v1` branch to create here,
because there is no v1 content in this repository. If prior work surfaces
elsewhere, it is compared adversarially *after* this audit concludes, and
disagreements are preserved rather than reconciled.

---

## D-002 — Credential variable names reuse the main repository's
**Date:** 2026-09-20
**Context:** The brief suggested `FIRMS_MAP_KEY`, `SAFETYDATA_API_KEY`,
`NMSC_API_KEY`, `KMA_API_KEY`, but also instructed to reuse existing names from
the main WildfireGuardian repository rather than create duplicates. Inspection of
that repository found `src/wildfireguardian/live/firms.py` already defines
`FIRMS_MAP_KEY` as primary with `NASA_FIRMS_MAP_KEY` as an accepted alias, and
`.env.example` defines `KMA_API_KEY`.
**Decision:** Primary names `FIRMS_MAP_KEY` and `KMA_API_KEY` (identical to both
the brief and the main repo). Accept `NASA_FIRMS_MAP_KEY` and
`WILDFIREGUARDIAN_KMA_API_KEY` as aliases for compatibility. Introduce
`SAFETYDATA_API_KEY` and `NMSC_API_KEY` as genuinely new names — the main
repository defines nothing for those services.
**Consequence:** No duplicate naming. A `.env` already configured for the main
repository works here unchanged.

---

## D-003 — Credential handling
**Date:** 2026-09-20
**Context:** Security requirements forbid exposing key values anywhere.
**Decision:** Credentials are read from the environment only. `.env` is
gitignored; only `.env.example` (names, no values) is committed. Every URL
emitted to a log, a report, or a provenance record passes through `redact()`,
mirroring the main repository's existing `url.replace(key, "<MAP_KEY>")` pattern.
Status is recorded as metadata only (`credential_status: AVAILABLE | ABSENT`).
**Consequence:** No key value can reach `data/`, `reports/`, stdout, or git.

---

## D-004 — Credential exposure audit result
**Date:** 2026-09-20
**Context:** Required check for keys accidentally committed to the main
WildfireGuardian repository's git history.
**Decision / finding:** The shallow clone was unshallowed to the full **1000
commits** and scanned across all refs for (a) assignments of >=20-char values to
key-shaped variable names, (b) AWS/Google/GitHub/OpenAI/JWT key shapes, and
(c) bare 32-hex tokens (the FIRMS MAP_KEY shape). Results: 0 hits for (a) and
(b). 13 hits for (c), all of which were manually confirmed to be **URL path
segments in academic citations** (`proceedings.iclr.cc/...`, `consensus.app/...`,
`thedocs.worldbank.org/...`), not credentials. One additional grep hit,
`sms.py:41 ENV_AUTH_TOKEN`, is an environment-variable *name* constant
(`"TWILIO_AUTH_TOKEN"`), not a value.
**Consequence:** **No `POTENTIALLY_EXPOSED_CREDENTIAL` finding.** No rotation is
recommended on the basis of this audit. No credential was propagated into this
repository. See `reports/SOURCE_ACCESS_STATUS.md` for live credential status.

---

## D-005 — Target temporal window
**Date:** 2026-09-20
**Context:** Inclusion rule I-4 needs a concrete window, fixed before retrieval
so that it cannot be tuned to the data found.
**Decision:** `2025-03-21T00:00:00+09:00` to `2025-04-05T00:00:00+09:00` (KST),
half-open. Chosen to bracket the reported onset of the March 2025 Gyeongbuk
complex with margin on both sides, without presupposing any specific ignition time.
**Consequence:** Sources outside the window are methodological evidence only.
Widening the window later is a logged decision, not a silent edit.

---

## D-006 — `SAME_COUNTY` is insufficient for lead-time pairing
**Date:** 2026-09-20
**Context:** Korean emergency alerts are frequently addressed to a whole
si/gun. A county can be ~1000 km2; fire-front position within it is not implied.
**Decision:** Lead-time computation requires geography compatibility of
`EXACT_LOCALITY`, `SAME_EUP_MYEON`, or `SENSOR_FOOTPRINT_INTERSECTS`.
`SAME_COUNTY` and `NEARBY` are recorded but gated out of the calculation.
**Consequence:** Fewer lead-time results, each defensible. Expected to be the
binding constraint on Q4.
