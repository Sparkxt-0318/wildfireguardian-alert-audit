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
| **reported ignition** | `[2025-03-22T11:24:00+09:00, 2025-03-22T11:25:59+09:00]` — the hull of two conflicting primary records (C-01). Not averaged. |
| **formal evacuation order** | the alert text declares 대피명령 / 대피령 / 긴급대피 |
| **evacuation directive** | the alert instructs people to evacuate, whether or not an order was formally declared. A superset of the above. |
| **first alert about this fire** | earliest alert from that authority that mentions 산불 **and** was sent at or after the earliest reported ignition. The time floor matters: without it, each county's "first alert" is a pre-ignition dryness warning and the interval comes out negative. |

### Result: reported ignition → first public warning

| County | Alerts | Formal orders | Directives | First alert (KST) | Reported ignition → first alert |
|---|---:|---:|---:|---|---|
| 의성군 Uiseong | 66 | 58 | 57 | 2025-03-22 **12:50:32** | **[1h24m33s, 1h26m32s]** |
| 안동시 Andong | 106 | 51 | 76 | 2025-03-22 **13:07:13** | **[1h41m14s, 1h43m13s]** |
| 청송군 Cheongsong | 17 | 12 | 12 | 2025-03-22 **13:39:21** | **[2h13m22s, 2h15m21s]** |
| 영양군 Yeongyang | 26 | 4 | 17 | 2025-03-22 **16:14:02** | **[4h48m03s, 4h50m02s]** |
| 영덕군 Yeongdeok | 14 | 5 | 13 | 2025-03-24 **17:02:00** | **[53h36m01s, 53h38m00s]** |

Each interval is two seconds wide, and the width comes **entirely** from the
11:24/11:25 disagreement between two primary records. The alert side is exact.

### Result: reported ignition → first formal evacuation order

| County | First formal order (KST) | Reported ignition → first order | First alert → first order |
|---|---|---|---|
| 의성군 | 2025-03-22 **12:50:32** | [1h24m33s, 1h26m32s] | 0h00m00s (the first alert *was* the order) |
| 안동시 | 2025-03-22 **21:29:18** | [10h03m19s, 10h05m18s] | 8h22m05s |
| 청송군 | 2025-03-25 **16:49:19** | [77h23m20s, 77h25m19s] | 75h09m58s |
| 영양군 | 2025-03-25 **18:18:45** | [78h52m46s, 78h54m45s] | 74h04m43s |
| 영덕군 | 2025-03-25 **18:58:23** | [79h32m24s, 79h34m23s] | 25h56m23s |

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
| Reported ignition → first warning? | **Yes**, 5 counties, ±2 s. |
| Reported ignition → first order? | **Yes**, 5 counties, ±2 s. |
| First alert → first order? | **Yes**, 5 counties, exact. |

The audit produces no warning lead time, and that is the correct result rather
than a shortfall. What it produces instead is a second-resolution record of when
five county governments warned and ordered, with every interval labelled for
what it actually measures.
