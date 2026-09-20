# Coverage

Generated 2026-09-20.

`docs/CLAIM_RULES.md` C-6 forbids an undefined coverage percentage. "Percentage
of the event documented" is not a defined quantity and does not appear here.
Every number below states its target interval, what was counted, the spatial
requirement, how overlap was handled, and its denominator.

---

## Metric 1 — GK2A L2 FF observation-slot availability

### Definition

Let `S(a)` be the set of **nominal observation slots** for GK2A area `a` in the
target interval, where a nominal slot is a timestamp on the product's documented
cadence (KO: 2 min; EA, FD: 10 min).

Let `R ⊆ S(a)` be the slots **probed** by this audit, and `A ⊆ R` the slots for
which the operational L2 FF product was **retrieved** (HTTP 200, `image/png`,
> 4 KiB — the size and content-type test that distinguishes a real product from
the NMSC soft-404).

```
observation_slot_availability(a) = |A| / |R|
```

- **Target interval:** 2025-03-21T00:00+09:00 → 2025-04-05T00:00+09:00 (D-005),
  evaluated in UTC.
- **Evidence class counted:** `REMOTE_SENSING` only.
- **Spatial requirement:** the product area must contain Gyeongsangbuk-do. All
  three areas (KO, EA, FD) do.
- **Overlap handling:** slots are deduplicated on `(timestamp, area)` before
  counting, so a timestamp sampled by two strata contributes once.
- **Denominator:** `|R|`, the slots actually probed — **not** `|S(a)|`. This is
  a sampled estimate, not a census, and the strata are declared below so the
  sample is reproducible.

### What this metric does and does not say

It measures **whether the operational forest-fire detection product ran and was
published for a given observation slot**. That is *observation availability*,
one of the three things the research question asks about.

It is **not** a fire-detection census. These are rendered PNG twins of the
NetCDF product; reading fire pixels out of them would require the product
colormap and is not attempted. A retrieved slot means *the sensor product
covered that moment*, not *a fire was detected then*.

### Result

| Stratum | Area | Cadence | Available / probed | Rate |
|---|---|---|---|---|
| A — hourly envelope, whole window | KO | 60 min | 354 / 354 | **100.00 %** |
| B — native cadence, 2025-03-25 00:00–06:00 UTC | KO | 2 min | 170 / 170 | **100.00 %** |
| C — documented instrument gap, 3 days | KO | 2 min | 15 / 30 | 50.00 % |
| D — wider areas, 2025-03-25 | EA, FD | 30 min | 96 / 96 | **100.00 %** |
| **Total (deduplicated)** | | | **635 / 650** | **97.69 %** |

Window actually spanned: **2025-03-21 → 2025-04-04 KST**, 15 consecutive days.

### Every unavailable slot is accounted for

All 15 unavailable slots fall inside **00:40–00:48 UTC**, and all 15 are in
stratum C, which was designed to test exactly that window. The NMSC
documentation describes a daily wheel-offload observation gap at **00:40–00:50
UTC** for the December–April period. The measurement reproduces it precisely on
all three sampled days:

```
2025-03-22  00:36 ✓  00:38 ✓  00:40 ✗  00:42 ✗  00:44 ✗  00:46 ✗  00:48 ✗  00:50 ✓  00:52 ✓  00:54 ✓
2025-03-25  00:36 ✓  00:38 ✓  00:40 ✗  00:42 ✗  00:44 ✗  00:46 ✗  00:48 ✗  00:50 ✓  00:52 ✓  00:54 ✓
2025-03-28  00:36 ✓  00:38 ✓  00:40 ✗  00:42 ✗  00:44 ✗  00:46 ✗  00:48 ✗  00:50 ✓  00:52 ✓  00:54 ✓
```

This is a **scheduled instrument gap, not an outage and not a data loss.** It is
recorded as `NO_RELEVANT_RECORD` — the one status that licenses a statement
about dataset contents, and licensed here because the service answered
correctly and the query was valid.

**Outside that documented gap, availability was 100 % across 620 probed slots.**

### Transient failures were re-probed, not recorded

Three slots (2025-03-25 05:30 UTC KO, 2025-03-25 11:00 UTC EA, 2025-03-29 04:00
UTC KO) returned `SERVER_ERROR` on first attempt. All three returned the product
on re-probe. Recording them as first seen would have introduced three false
absences into a 650-slot sample — a 0.46 % error rate arising purely from
treating a transport failure as a finding.

---

## Metric 2 — primary alert-record coverage

### Definition

```
alert_record_coverage = (alert records retrieved for the target interval
                         and province) / (alert records known to exist for it)
```

### Result

**Numerator: 0. Denominator: unknown.**

The denominator is genuinely unknown and is not estimated. The authoritative
source (`DSSP-IF-00247`) is credential-gated, so this audit cannot enumerate
what exists. The public 국민안전24 surface returns `전체 0 건` for the window,
but that is a property of *that surface's retention*, not of the MOIS store.

Reporting `0 / 0 = 0 %` or "no alerts were sent" would be exactly the error this
repository exists to prevent. The correct statement is: **coverage of primary
alert records is zero, and the size of what is missing is not knowable from
outside the credential wall.**

---

## Metric 3 — retrieved-corpus temporal coverage

### Definition

For evidence class `c`, the union of time intervals asserted by retrieved
artifacts of that class, divided by the target interval's length:

```
temporal_coverage(c) = |⋃ intervals(c) ∩ T| / |T|,   T = the target interval
```

Overlapping intervals are unioned before measuring, so corroborating sources do
not inflate coverage. Unbounded intervals are clipped to `T`.

### Result

| Evidence class | Temporal coverage of T | Basis |
|---|---|---|
| `REMOTE_SENSING` | 15 of 15 days sampled; 100 % of probed slots outside the documented gap | GK2A L2 FF product tree |
| `PRIMARY_OPERATIONAL` | **0 %** | no alert record obtained — credential-gated |
| `OFFICIAL_RETROSPECTIVE` | see `reports/CURRENT_EVIDENCE_VERDICT.md` | — |
| `NEWS_REPORT` | see `reports/CURRENT_EVIDENCE_VERDICT.md` | — |

The asymmetry is the headline finding: **observation availability is
well-established and alert timing is not established at all.** Since a warning
lead time needs both sides, this asymmetry — not any analytical difficulty — is
what determines the result in `reports/LEAD_TIME_RESULTS.md`.
