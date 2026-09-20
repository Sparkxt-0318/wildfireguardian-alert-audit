# Manual verification

Generated 2026-09-20.

Independent manual verification of extracted records, performed by a separate
agent role that read the verbatim Korean and did **not** run this repository's
parsers. Running the parser to check the parser would be circular; the point is
an independent reading of the source text.

The figure below is a **manual verification discrepancy rate**, not an accuracy
figure. Three reasons that distinction is load-bearing are given under
"Why not accuracy".

---

## Round 1 — the pipeline as first built

**Sample.** 50 claims, simple random sample without replacement, **seed
20250322**, drawn from 311 claims. The seed was fixed before drawing, so the
sample is reproducible and could not be chosen to flatter the result.

**Dimensions checked per claim:** time, time role, geography, event label,
evidence class, raw-text fidelity, source attribution.

### Result

> ## Manual verification discrepancy rate: **32.0 %** (16/50)
> ### 95 % Wilson score interval: **[20.8 %, 45.8 %]**

Excluding two arguable corpus-scope items: **28.0 %** (14/50), CI
**[17.5 %, 41.7 %]**.

Either way the lower bound sits above 17 %, so "roughly one claim in three
carried a discrepancy" is not sampling noise.

### Per-dimension

| Dimension | Discrepancies |
|---|---|
| time | **0** |
| time role | **0** |
| geography | **5** |
| event label | **11** |
| evidence class | **0** |
| raw-text fidelity | **0** |
| source attribution | **0** |

All 50 `raw_text` values were confirmed **byte-identical** to the harvested
corpus, preserving original artifacts including a typo (「길안초등학**고**」), a
doubled particle, middle dots, and an embedded newline. Every `provenance` URL
carried an `sn` matching its `record_id`.

### The failures were clustered, not scattered

Four defects accounted for 14 of the 16, which is why they were fixable.

| Cluster | Defect | Example |
|---|---|---|
| **A** (6) | `발생` ("occurrence") mapped to an ignition report regardless of what it governed | 「연기 다량 **발생**중」 — smoke; 「인명사고 **발생**」 — casualties; 「산불**발생** 위험」 — a *risk*; 「산불이 **발생**하지 않도록」 — a prevention notice asking that fires **not** occur |
| **B** (2) | `진화 중` (suppression **in progress**) mapped to containment, because the veto list held only the unspaced `진화중` | a drone no-fly notice; an alert telling evacuees **not** to go home |
| **C** (1) | `발화지점` ("ignition **point**", a location noun) produced a bare ignition event | an alert sent at 16:10, hours after the fact |
| **D** (5) | only the **first** locality per clause was kept | a cross-county road closure naming 안동시 **and** 청송군 in one sentence lost the second |

Two further scope errors: PM2.5 air-quality advisories were entering the
wildfire timeline as `first_public_warning`, because
`docs/INCLUSION_RULES.md` I-4/I-5 gate on time and place but never on **topic**;
and the gazetteer's five-county horizon dropped all three 면 from an alert
naming 「포항 북구 죽장면, 기북면, 송라면」.

### Direction of error matters

Nine of the eleven label discrepancies were **false positives that fabricated
events**, all in the same direction — making the alert record look **richer and
earlier** than the Korean supports. The most damaging sat at **11:05:22**, twenty
minutes *before* the real ignition: a spurious ignition report there would have
silently pre-dated the earliest genuine one in any min-over-claims query.

The five geography discrepancies ran the other way, **shrinking** the spatial
footprint and deleting cross-county spread evidence.

### What the verifier could not check

- **Recall.** A sample of *emitted* claims cannot see claims never emitted. At
  least one such omission was found by inspection: `sn=231369`, 「(대피명령발령)
  **11:25** 안평면 괴산리 산61 산불 확산」, stated the fire's ignition minute in
  an official alert and produced no time claim at all.
- **The `재발화` guard**, the project's headline Korean-semantics rule, was
  **not exercised** — no `재발화` record was drawn. It remains covered by unit
  tests but unverified by this sample.
- **Road rejection.** `roads_mentioned_not_localities` was empty in all 50
  records, making the field vacuous as evidence: empty whether a road was
  correctly rejected or simply never noticed. The verifier re-derived it by
  hand across six road/facility names and found **no leakage** — including the
  hard cases 남**안동**농협주유소, 안**평**초등학교 신평분교장, **남후**농공단지 and
  의성실내체육관.

### Fixes applied

All six issues were fixed and covered by **23 regression tests**, each built
from a verbatim corpus string with the record id it came from
(`tests/test_verification_regressions.py`). Lexicon entries gained context
predicates; clause extraction now exposes every locality; the gazetteer was
extended to neighbouring municipalities; a topic gate was added; and a stated
clock time with no accompanying event language is now preserved **verbatim with
no quantity asserted**, rather than inferred into an ignition report.

The headline intervals in `reports/LEAD_TIME_RESULTS.md` were **unchanged** by
these fixes, which is the expected result: the defects created spurious extra
events rather than corrupting the alert send times the intervals rest on.

---

## Why not "accuracy"

`docs/CLAIM_RULES.md` C-6 requires a metric to state what it measures.

1. It measures **precision on sampled claims only**. It cannot see claims the
   parser never emitted, and at least one consequential omission existed.
2. **34/50 "clean" is not 34/50 "verified correct."** One field was vacuous and
   had to be re-derived by hand, and the headline `재발화` guard was untested by
   the draw.
3. The errors were **deterministic by message shape**, not independent per
   claim. "Accuracy" implies a per-item error probability; the real structure
   was that specific Korean constructions failed every time they appeared. That
   is also why this rate should not be quoted as a stable property of the
   pipeline.

---

## Round 2 — after the round-1 fixes

**Sample.** 50 claims, **seed 20260920**, drawn from the *rebuilt* 302-claim
corpus. A new seed was used deliberately: re-verifying the round-1 sample would
be circular, because those exact records drove the fixes.

### Result

> ## Manual verification discrepancy rate: **34.0 %** (17/50)
> ### 95 % Wilson score interval: **[22.4 %, 47.8 %]**

Sensitivity, excluding sub-county (동) omissions as arguably out of schema
scope: **30.0 %** (15/50), CI **[19.1 %, 43.8 %]**.

### The honest reading: the rate did not improve

Round 1 was 32.0 %, CI [20.8 %, 45.8 %]. Round 2 is 34.0 %, CI [22.4 %, 47.8 %].
**The intervals overlap almost entirely. There is no statistical evidence that
the fixes reduced the overall discrepancy rate.**

What changed is *composition*, not magnitude:

| | Round 1 | Round 2 |
|---|---|---|
| event label | 11 | 7 |
| geography | 5 | **13** |
| time / time role | 0 | 2 |

Geography went from 31 % of findings to **57 %**. Fixing four named clusters
moved the defect mass rather than removing it, which is what should be expected
and is worth stating plainly: *fixing named clusters and re-sampling will keep
producing this result until the residual classes are attacked.*

One qualitative improvement is real, though it does not show in the rate.
Round 1's failures were **false positives that fabricated events** — a
fabricated ignition twenty minutes before the real one, two containment events
while suppression was explicitly still underway. Round 2's are mostly
**recall misses in inventory fields**. A missing facility name is a worse
catalogue; a fabricated ignition is a worse finding.

### Status of the round-1 clusters

| Cluster | Status |
|---|---|
| **A** — 발생 over-matching | **Fixed.** Four independent in-sample cases all clean. |
| **B** — 진화 중 → containment | **Fixed** where tested; the verifier additionally checked all 8 suppression-in-progress records in the full corpus, none carries a containment label. 진화율 never appeared, so that sub-rule is **untested by sampling**. |
| **C** — 발화지점 → ignition | **Fixed**, one in-sample case. A single successful test, not a strong result. |
| **D** — first-locality-only | **Half fixed.** Multi-locality capture works where each name carries its suffix; it failed on Korean **suffix-elided coordination** (「남선, 임하, 길안면」 kept only the last). Now fixed, with a test. |
| PM2.5 advisories | **Was handled by exclusion, not comprehension.** The literal string no longer reaches the corpus, but three wildfire-*smoke* advisories were still stamped as warnings. Now handled semantically by `classify_alert_purpose`. |
| gazetteer horizon | **Not fixed, and actively harmful.** It produced a *false positive*, not merely nulls. Now fixed. |

### New findings from round 2, and what was done

| # | Finding | Action |
|---|---|---|
| **NEW-1** | **Quantity vocabulary collapse.** The corpus emitted 2 of 10 modelled quantities; 295 of 302 records were stamped `first_public_warning` — a superlative asserted hundreds of times, leaving any count or join keyed on it operating on a constant. | Quantities now derive from `classify_alert_purpose`; the corpus uses 6. `PUBLIC_WARNING` added as the non-superlative sibling, and `first_public_warning` now holds **at most once per county**, enforced by a test. |
| **NEW-2** | `is_evacuation_directive` was not a superset of `is_evacuation_order` (58 vs 57) — three orders say 집결 (assemble) rather than 대피. | Superset made true by construction; 집결/피신 added; invariant tested on the corpus. |
| **NEW-3** | Ambiguous 면 resolved by gazetteer priority over the county written beside it. | An out-of-scope municipality anywhere in the text now blocks parent inference. |
| **NEW-4** | Facility/road inventories recall-poor (7/50). **Precision was perfect — no facility name leaked into a geography field anywhere in 50 records.** | Inventory widened; the leak-guard was already sound. |
| **NEW-5** | Sub-county geography discarded (동 dropped, 리 absent) — which silently demoted the two best-timed ignition claims to county level, where D-006 gates them out of lead-time eligibility. | Andong's 동 added to the gazetteer. 리 remains unmodelled in the timeline schema — **open**. |
| **NEW-6** | A 무주군 (North Jeolla) fire sat in the corpus **labelled 청송군**. | Both records now excluded. Tested. |
| **NEW-7** | Duplicate and superseding alerts not linked; 「(정정)」 corrections stamped as first warnings. | **Open.** `EdgeType.SUPERSEDES` exists but is unused for alert pairs. |

### Still open after round 2

- **리-level geography** is modelled in `Geography` but not carried in the
  timeline schema.
- **Duplicate/superseding alert linkage** (NEW-7).
- **진화율 → containment** remains verified only by unit test, never by sampling.
- A third sampling round would very likely find a further ~30 %, in classes not
  yet named. That is the expected behaviour of this method, not a sign the
  corpus is unusable — but it does mean **the discrepancy rate should be read as
  a property of the sampling process, not as a quality certificate.**
