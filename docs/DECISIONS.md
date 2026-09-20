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

---

## D-007 — The public alert archive is treated as `PRIMARY_OPERATIONAL`
**Date:** 2026-09-20
**Context:** The historical alert **API** (`DSSP-IF-00247`) is credential-gated,
but the same MOIS platform publishes the alerts themselves at
`/disaster-data/disasterNotification` with no credential, carrying send time to
the second, the message text as transmitted, the issuing authority and a stable
record id.
**Decision:** Classify these as `PRIMARY_OPERATIONAL`.
**Reasoning, including the counter-argument:** the page is a *publication* of
the records rather than the operational database itself, which is an argument
for `OFFICIAL_RETROSPECTIVE`. It is rejected because the artifact reproduces the
operational payload verbatim — the transmitted message text, its send timestamp
and its issuer — rather than describing or summarising it, and it is published
by the operating ministry rather than by a third party. It is the same relation
a court transcript bears to a hearing. The audit records the distinction
explicitly (`source_system` names the public archive, not the API), so a reader
who disagrees can re-grade every record without losing information.
**Consequence:** first-public-warning timing rests on `PRIMARY_OPERATIONAL`
evidence. Had it been graded `OFFICIAL_RETROSPECTIVE`, the time role would fall
to `REPORTED_ALERT_SEND_TIME` and every interval in
`reports/LEAD_TIME_RESULTS.md` would carry that weaker label. The numbers would
not change; their standing would.

---

## D-008 — "First alert about this fire" needs an explicit rule
**Date:** 2026-09-20
**Context:** Taking each county's earliest alert in the window produced
*negative* intervals against the reported ignition. The cause was that the
earliest alert from 의성군 in the window is a pre-ignition dryness warning
(10:46:07, 「건조한 날씨와 강풍으로 산불발생 위험이 매우 높습니다」), which
mentions 산불 without being about this fire.
**Decision:** An alert counts as "about this fire" when it mentions 산불 **and**
was sent at or after the earliest reported ignition (11:24:00). An alert sent
before the fire began cannot be about it.
**Consequence:** Uiseong's first alert about the fire is 12:50:32, not 10:46:07.
The rule is stated in `reports/LEAD_TIME_RESULTS.md` so the filter is auditable,
and it is deliberately crude — it would misclassify a warning about a *different*
concurrent fire, which is why incident identity stays explicit.

---

## D-009 — Formal orders and evacuation directives are counted separately
**Date:** 2026-09-20
**Context:** `docs/EXCLUSION_RULES.md` X-5 requires that a generic mention of
대피 not be read as a 대피명령. Applied strictly, an alert reading 「주민들께서는
즉시 의성실내체육관으로 대피하시기 바랍니다」 is not an order — yet it plainly
directs people to leave.
**Decision:** Report both. `is_evacuation_order` stays strict (대피명령 / 대피령
/ 긴급대피 only). `is_evacuation_directive` is a superset capturing imperative
instructions to evacuate.
**Consequence:** 132 formal orders and 181 directives. Reporting only the first
would understate what was communicated; reporting only the second would
overstate the formal record. Neither number stands alone.
