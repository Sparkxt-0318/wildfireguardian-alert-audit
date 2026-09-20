# Lead-time results

Generated 2026-09-20. Governed by `docs/CLAIM_RULES.md` C-2 and C-4.

---

## Headline

> ## NO DEFENSIBLE WARNING LEAD TIME — for any locality.

A warning lead time is the interval between a warning and **the hazard arriving
where the warned people are**. Computing one requires fire-arrival timing at the
locality scale. No accessible source provides it.

This is not a retrieval failure and not a gap that a credential would close. The
official operational record **does not contain per-locality fire-arrival times**,
because it was never structured to. `reports/CONTRADICTIONS.md` C-03 documents
the reason: in the government's own per-fire table, all five affected Gyeongbuk
counties carry the **identical** 산불발생 timestamp `3.22(토) 11:25`. The five
fires are administratively one fire, timestamped to the Uiseong ignition.

Even the single closest candidate — 안동시's retrospective `2025. 3. 24.(월)
17:02` — is one hour-minute figure, for an entire city of ~1,500 km², on a
municipal web page, and it **contradicts** the central record for the same
county. Under `docs/DECISIONS.md` D-006 a county-level geography is too coarse
to pair with any alert, so it is gated out rather than used.

**Forcing a number here would require inventing the very thing the brief
forbids inventing.**

---

## What the evidence *does* support

The audit obtained **264 emergency alerts about this fire**, all
`PRIMARY_OPERATIONAL`, with send times to the **second**. That makes several
intervals computable and defensible — provided each is named for exactly what it
measures. None of them is a warning lead time.

### Definitions used below

| Term | Meaning |
|---|---|
| **reported ignition** | `[2025-03-22T11:24:00+09:00, 2025-03-22T11:25:59+09:00]` — evidence class **`DERIVED`**. Belongs specifically to the **안평면 괴산리** ignition; see the incident-identity caveat below. |
| **formal evacuation order** | the alert text declares 대피명령 / 대피령 / 긴급대피 |
| **evacuation directive** | the alert instructs people to evacuate, whether or not an order was formally declared. A superset of the above. |
| **first warning about this fire** | earliest alert from that authority whose **purpose** is to warn about an actually-burning fire — an evacuation order, an evacuation directive, or an incident warning. Classified by `core/korean.classify_alert_purpose`. Burn-ban advisories, road-closure notices and utility notices are excluded and recorded under their own purposes. **No ignition-time floor is applied** (see the correction note). |

#### Why the reported-ignition interval is `DERIVED`, and why a hull is allowed

Two primary records disagree: one says 11:24, one says 11:25 (C-01). At minute
resolution those are `[11:24:00, 11:24:59]` and `[11:25:00, 11:25:59]`.

`docs/TIME_ONTOLOGY.md` forbids averaging them into 11:24:30, and permits a
combination only as **an explicitly labelled `DERIVED` analysis with a stated
justification**. This is that label and that justification.

The combination used is the **convex hull**: the narrowest interval containing
both readings. It is admissible precisely because it is a *weakening*. It
asserts strictly less than either source alone and rules out no possibility
either source allows. An average would assert more than any source does — a
precision to the second that no record anywhere supplies.

Consequence: every interval in the tables below inherits `DERIVED` status on
its ignition side. The alert side remains `PRIMARY_OPERATIONAL` and exact.

#### Correction note — these tables were wrong in an earlier revision

An adversarial review found two errors here, both of which flattered the result.
They are recorded rather than quietly patched.

**1. The selection rule picked the wrong record for four counties out of five.**
The first version selected "the earliest alert mentioning 산불, sent at or after
the reported ignition". Every routine burn-ban SMS in Korea contains 산불, and so
does a road-closure notice. What that rule actually selected:

| County | Old "first alert" | What it really was |
|---|---|---|
| 안동시 | 13:07:13 | province-wide burn-ban boilerplate |
| 청송군 | 13:39:21 | the same boilerplate, word for word |
| 영양군 | 16:14:02 | the same boilerplate, word for word |
| 영덕군 | 03-24 17:02 | an **expressway closure notice** — about 서산영덕선, the very road this repository's geography module exists to keep out of locality inference |

The corrected figures are **later, not earlier**: 안동 moved from 1h41m to
3h52m, 청송 from 2h13m to 77h23m, 영양 from 4h48m to 24h05m, 영덕 from 53h36m to
78h56m. Every error ran in the direction that made each county look like it had
warned sooner.

**2. The published precision was wrong by a factor of sixty.** The intervals
were described as "two seconds wide" and "±2 s". They are **119 seconds** wide.
The error came from reading the *seconds field* of the two endpoints
(`1h24m33s` … `1h26m32s`) as the width. A test now asserts the width is 119 s.

**3. An ignition-time floor has been removed.** Filtering to alerts sent at or
after the reported ignition made the metric *structurally incapable* of
returning a negative value. If an authority had warned before the stated
ignition minute, that would be a finding, not something to filter away. The
purpose classifier does the work the floor was compensating for.

#### Incident-identity caveat — the interval belongs to ONE of three fires

Citation-chain work and an administrative dataset agree that Uiseong had
**three separate ignitions on 2025-03-22**, not one. KFS `15121205`, queried
successfully, holds three distinct 의성군 rows:

```
안평면  suppression start 11:38   complete 03-28 17:15
금성면  suppression start 14:08   complete 03-23 08:11
안계면  suppression start 16:27   complete 03-28 17:24
```

The `[11:24, 11:25]` interval is the reported ignition of the **안평면 괴산리**
fire only. Andong's own evacuation order `sn=231946` credits the spread to the
「의성 **안계** 산불」, and Andong's municipal page says the fire came from
「의성군 **안계면, 안평면** 산불」 — plural.

**Consequence for every row below.** The intervals are measured from the 안평면
reported ignition because that is the earliest and best-evidenced of the three.
For Uiseong itself that pairing is sound. For the downstream counties it is a
**convention, not a causal claim**: this audit cannot establish which of the
three fires reached which county, so the later intervals should be read as
"time since the first reported ignition in Uiseong", not as "time since the
fire that reached us started".

### Result: reported ignition → first public warning

| County | Alerts about the fire | Formal orders | First warning (KST) | Reported ignition → first warning |
|---|---:|---:|---|---|
| 의성군 Uiseong | 71 | 66 | 2025-03-22 12:50:32 | **[1h24m33s, 1h26m32s]** |
| 안동시 Andong | 94 | 54 | 2025-03-22 15:18:00 | **[3h52m01s, 3h54m00s]** |
| 청송군 Cheongsong | 24 | 23 | 2025-03-25 16:49:19 | **[77h23m20s, 77h25m19s]** |
| 영양군 Yeongyang | 19 | 4 | 2025-03-23 11:30:44 | **[24h04m45s, 24h06m44s]** |
| 영덕군 Yeongdeok | 14 | 5 | 2025-03-25 18:21:50 | **[78h55m51s, 78h57m50s]** |

Each interval is **119 seconds wide** (±1 minute). That width comes
**entirely** from the 11:24/11:25 disagreement between two primary records
(C-01); the alert side is exact to the second. The ignition side is not
*uncertain*, it is **disputed** — two official records contradict each other —
and a disputed value is not a confidence interval.

### Result: reported ignition → first formal evacuation order

| County | First formal order (KST) | Reported ignition → first order | First warning → first order |
|---|---|---|---|
| 의성군 Uiseong | 2025-03-22 12:50:32 | [1h24m33s, 1h26m32s] | 0h00m00s |
| 안동시 Andong | 2025-03-22 21:29:18 | [10h03m19s, 10h05m18s] | 6h11m18s |
| 청송군 Cheongsong | 2025-03-25 16:49:19 | [77h23m20s, 77h25m19s] | 0h00m00s |
| 영양군 Yeongyang | 2025-03-25 18:18:45 | [78h52m46s, 78h54m45s] | 54h48m01s |
| 영덕군 Yeongdeok | 2025-03-25 18:58:23 | [79h32m24s, 79h34m23s] | 0h36m33s |

`first alert → first order` intervals are **exact**: both endpoints are
second-resolution primary records, so no uncertainty enters.

---

## What these numbers do and do not mean

**They do** establish, from primary operational records, when each authority
first warned the public about this fire and when it first ordered evacuation,
to the second.

**They do not** establish how much time anyone had. Nothing in the table
locates the fire. Uiseong's 1h25m and Yeongdeok's 53h36m are **not** comparable
as warning performance: the fire began in Uiseong and reached Yeongdeok days
later. A longer interval here may mean the fire was far away, not that the
warning was late.

**Specifically forbidden readings of this table** (`docs/CLAIM_RULES.md` C-2):

- ✗ "Residents of Uiseong had 1 hour 25 minutes." — the table says nothing about
  where the fire was at 12:50:32.
- ✗ "The Yeongdeok alert was 53 hours late." — there is no defensible baseline,
  and the fire was not in Yeongdeok at ignition.
- ✗ Any comparison of these intervals as a measure of response quality.
- ✗ Any casualty counterfactual.

Hedging does not lift these (C-3). The constraint is on the quantity, not the
phrasing.

---

## The two lead-time kinds, and why neither is reported

`docs/CLAIM_RULES.md` C-4 requires any lead time to name its kind.

### ALERT → FIRST SENSOR DETECTION — *not computed, but reachable*

Blocked on one free credential. The alert side is **in hand** at second
resolution. The detection side needs FIRMS SP-archive rows, and
`FIRMS_MAP_KEY` is issued free by email with no account.

Even then, `docs/DECISIONS.md` D-006 gates the pairing to
`EXACT_LOCALITY` / `SAME_EUP_MYEON` / `SENSOR_FOOTPRINT_INTERSECTS`. Many alerts
name an 읍/면 in their body, and VIIRS pixels are 375 m, so
`SENSOR_FOOTPRINT_INTERSECTS` is achievable for at least some pairs.

**This is the one genuinely reachable lead-time result, and it costs one email.**
It would still be a lead to *detection*, never to arrival.

### ALERT → PHYSICAL FIRE ARRIVAL — *not computable from public evidence*

Requires fire-arrival truth that does not exist in accessible form. No
credential changes this. It would need fire-progression mapping at locality
scale, which was not published. **This is the audit's firmest negative finding.**

---

## GK2A cannot substitute

The audit retrieved 635 GK2A L2 Forest Fire observation slots. That establishes
**observation availability** — the product ran and was published — and nothing
more. The retrieved artifacts are rendered PNGs, not the `FF`/`DQF_FF` NetCDF,
so no fire pixel is read.

Even with the NetCDF, a detection would be a `SENSOR_ACQUISITION_TIME`, never a
`PHYSICAL_EVENT_TIME` (FM-12). And a slot where the product shows no fire cannot
bound anything without a verified `DetectionAssumption` (FM-10) — the product's
own documentation lists five independent reasons it may not flag a real fire:
it is not produced at all when the Cloud Mask is absent, daytime solar
reflection lowers detection rate, a 2-minute stability test suppresses
single-frame detections, industrial heat sources are on an exclusion list, and
solar zenith angle above 70° is flagged invalid rather than fire-free.

---

## Summary

| Question | Answer |
|---|---|
| Warning lead time, any locality? | **No.** Not computable from accessible evidence. |
| Alert → sensor detection lead? | Not yet — needs one free `FIRMS_MAP_KEY`. |
| Alert → physical arrival lead? | **No, and no credential fixes it.** |
| Reported ignition → first warning? | **Yes**, 5 counties, ±1 minute. |
| Reported ignition → first order? | **Yes**, 5 counties, ±1 minute. |
| First warning → first order? | **Yes**, 5 counties, exact to the second. |

The audit produces no warning lead time, and that is the correct result rather
than a shortfall. What it produces instead is a second-resolution record of when
five county governments warned and ordered, with every interval labelled for
what it actually measures.
