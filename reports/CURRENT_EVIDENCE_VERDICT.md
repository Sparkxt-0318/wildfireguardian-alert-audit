# Current evidence verdict

Generated 2026-09-20. Answers `docs/RESEARCH_QUESTION.md` Q1–Q5 in order.

---

## Q1 — What relevant evidence actually exists and is accessible?

### Obtained, without any credential

| Evidence | Class | Volume | Resolution |
|---|---|---|---|
| Emergency alert records (긴급재난문자) | `PRIMARY_OPERATIONAL` | **1,688** records, 264 about this fire | **second** |
| GK2A L2 Forest Fire product slots | `REMOTE_SENSING` | **635** of 650 probed, 15 days | 2 min (KO) |
| KFS 산불상태별 이력 suppression records | `OFFICIAL_RETROSPECTIVE` | 4 rows in scope | minute |
| MOIS 중대본 situation reports | `PRIMARY_OPERATIONAL` | 9 releases, 22–30 Mar | minute |
| Municipal retrospective pages | `OFFICIAL_RETROSPECTIVE` | 안동시 | minute |

### Exists, verified live, credential-gated

| Evidence | Barrier | Cost to unlock |
|---|---|---|
| FIRMS VIIRS/MODIS SP detections | `FIRMS_MAP_KEY` | free, by email, no account |
| KFS per-incident 발생/진화일시 (`3070842`) | data.go.kr key | free, auto-approved |
| KMA 기상특보 issuance times (`15000415`) | data.go.kr key | same key as above |
| GK2A `FF`/`DQF_FF` NetCDF | `KMA_API_KEY` | free registration |
| Alert API with typed region codes | `SAFETYDATA_API_KEY` | needs a Korean mobile number |

### Not retrieved

NFA dispatch records (bot-verification wall), BAI audit (JS-rendered),
경상북도 March 2025 releases (deep-link not resolved), 산불통계연보 2025 PDF
(needs a browser context).

**None of these is recorded as absent.** Every one is an access classification.

---

## Q2 — What timestamps and locations can be established directly?

**Directly established, at second resolution, from primary operational records:**

- The send time of all 264 alerts about this fire.
- Which authority issued each, and what it said, verbatim.
- The first alert about the fire per county, and the first formal 대피명령.
- **132 formal evacuation orders** and **181 evacuation directives** across the
  five counties.

**Directly established at minute resolution from official operational releases:**

- 산불대응 1단계 at **13:05**, 2단계 at **13:45** (2025-03-22).
- 중앙재난안전대책본부 activated **17:30**; 재난사태 declared effective **18:00**.
- 주불진화 완료 for the last managed fire at **13:00** on 2025-03-30.

**Directly established for observation availability:**

- The GK2A L2 FF product was published for 635 of 650 probed slots across
  2025-03-21 → 2025-04-04, at 2-minute cadence over Korea.

**Locations** are established at issuing-authority granularity for every alert,
and at 읍/면/리 granularity wherever the message text names one — which it
frequently does, because these alerts direct people to specific villages and
shelters.

---

## Q3 — What event times can only be bounded?

| Quantity | Bound | Why not a point |
|---|---|---|
| **Reported ignition** | `[11:24:00, 11:25:59]` KST, 2025-03-22 | Two primary records disagree (C-01). The hull retains both; averaging is forbidden. |
| **Actual ignition** | not bounded | Nothing observed it. Every source reports, none observes. |
| **Andong fire arrival** | `3.24 17:02` **or** `3.22 11:25` | Two official sources, different quantities, unreconciled (C-02). |
| **Per-county arrival** | not bounded | Structurally absent from the official record (C-03). |

Non-detection bounds **nothing** here: no `DetectionAssumption` was verified, and
the GK2A product documents five independent reasons it may miss a real fire
(FM-10).

---

## Q4 — For which localities can alert-vs-observation lead intervals be calculated?

**None, for a warning lead time.** See `reports/LEAD_TIME_RESULTS.md`.

The alert side is in hand at second resolution for all five counties. The
observation side is not: FIRMS detections are credential-gated, and GK2A was
retrieved as rendered imagery rather than pixel data. An
`ALERT → FIRST SENSOR DETECTION` lead becomes computable on one free MAP_KEY.

An `ALERT → PHYSICAL FIRE ARRIVAL` lead remains uncomputable regardless of
credentials, because per-locality arrival times were never recorded.

What **is** computed, and named for what it measures:

- reported ignition → first public warning, five counties, ±2 s
- reported ignition → first formal evacuation order, five counties, ±2 s
- first alert → first order, five counties, exact

---

## Q5 — Which quantities remain genuinely unobserved?

**Genuinely unobserved — an affirmative argument, not a retrieval failure:**

- **Resident receipt of warning.** Korean CBS is a one-way broadcast with no
  return path. No party generates a per-recipient receipt. This is the only
  quantity in `reports/EVIDENCE_GAPS.md` marked `OBSERVATION_DOES_NOT_EXIST`.

**Unobserved in accessible sources, but which some record may hold:**

- Physical fire arrival at any named locality, at minute scale.
- Per-county ignition or arrival distinct from the complex's timestamp.
- Road arrival time as opposed to closure-announcement time.
- Fire-agency dispatch times (blocked by an access wall, not shown absent).

---

## The finding that matters most

The audit's most transferable result is not a number. It is that **a successful
query returned a false picture.**

The public 국민안전24 alert search returns `전체 0 건` for the entire target
window. HTTP 200. Valid query. Well-formed. Independently reproduced twice.

Read naively, it says no emergency alerts were issued during the March 2025
Gyeongbuk wildfires.

The same ministry's data platform holds **264 of them for this fire alone**,
including 132 formal evacuation orders, with send times to the second.

The protocol's core rule is usually stated as *a failed request is not evidence
of absence*. This audit found the sharper version: **a successful request
against the wrong surface is not evidence of absence either.** That is why
`NO_RELEVANT_RECORD` is scoped to the surface queried and never generalised,
and why `docs/SOURCE_STRATEGY.md` requires the escalation ladder to be walked
before any gap is classified.
