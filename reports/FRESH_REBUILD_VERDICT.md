# Fresh rebuild verdict

Generated 2026-09-20. Answers the thirteen questions the brief requires.

This audit was not optimised for a positive result. It was optimised for the
strongest result the evidence supports — and twice, an independent review
showed the result was weaker than claimed. Both corrections are recorded here
rather than in a footnote.

---

## 1. Which official datasets were identified?

| Domain | Dataset | Status |
|---|---|---|
| Emergency alerts | `DSSP-IF-00247` (safetydata.go.kr, dataSn=228) — **current authoritative** | gated |
| Emergency alerts | `/disaster-data/disasterNotification` — public archive of the same records | **retrieved** |
| Emergency alerts | 국민안전24 `calamitySms.do` | retrieved, but empty for this window |
| Emergency alerts | data.go.kr 15134001 (a `LINK` pointer), legacy `DisasterMsg3` (superseded) | — |
| Satellite | FIRMS Area API; Archive Download Tool; LAADS `VNP14IMG`/`VJ114IMG` | gated |
| Satellite | GK2A AMI L2 Forest Fire (`ff`) — NMSC product tree, KMA API Hub, data.kma.go.kr, AWS `noaa-gk2a-pds` | tree **retrieved**; NetCDF gated |
| Forest service | KFS `15121205` 산불상태별 이력; `3070842` 산불발생통계; `15121380`; 산불통계연보 2025 | 1 retrieved, rest gated/manual |
| Government | MOIS 중대본 releases via korea.kr; 안동시 portal; NARS Brief 72 | **retrieved** |
| Weather | KMA `15000415` 기상특보; ASOS/AWS | gated |

## 2. Which were actually retrieved?

- **1,688 emergency-alert records** (2025-03-21 → 2025-04-02), second-resolution
  send times, verbatim message text, issuing authority, stable record ids.
- **635 GK2A L2 Forest Fire observation slots** across 15 consecutive days, all
  byte-unique.
- **9 MOIS 중대본 releases**, including the per-fire status tables.
- **KFS `15121205`** suppression records (three separate 의성 rows).
- 안동시's retrospective page; NARS Brief 72 metadata.

## 3. Which require credentials?

FIRMS active-fire detections (`FIRMS_MAP_KEY` — free, by email, **no account**);
KFS `3070842` and KMA `15000415` (one free data.go.kr key covers both); GK2A
`FF`/`DQF_FF` NetCDF (`KMA_API_KEY`); the alert API with typed region codes
(`SAFETYDATA_API_KEY`, requires a Korean mobile number).

## 4. Which require manual download?

FIRMS Archive Download Tool (asynchronous, email-delivered); data.kma.go.kr bulk
GK2A orders; ASOS/AWS surface observations; 산불통계연보 2025 PDF (needs a
browser context).

## 5. Which endpoints had migrated?

SafeKorea's legacy `idsiSFK/...` alert paths now serve 국민안전24. Legacy
`DisasterMsg3` is superseded by `DSSP-IF-00247` — with the replacement stated
verbatim in the official notice. FIRMS' Country API is withdrawn (`Invalid API
call.`, commented out of the API index).

## 6. What primary alert records were obtained?

**1,688**, of which **264** concern this fire. Among them **152 formally
declared 대피명령** and **208 evacuation directives**, every one carrying a send
time to the second, the message as transmitted, and the issuing authority.

These records **corrected** four secondary accounts: Wikipedia places a
Cheongsong all-county order at 17:00 while footnoting the record that reads
**17:42:49**; it gives Pohang 22:16 where the record reads **22:03:43** and its
own text states an effective time of 22:00; and it describes an Andong order as
「전 주민 대피령」 where the record names three 리.

## 7. What remote-sensing acquisition records were obtained?

**None with fire-pixel content.** What was obtained is *observation
availability*: the GK2A L2 FF product was published for 635 of 650 probed slots.
All 15 misses fall inside 00:40–00:48 UTC, the documented daily wheel-offload
gap, reproduced on all three sampled days.

The retrieved artifacts are rendered PNGs, not the NetCDF, so **no fire pixel
was read**. Availability is not detection.

## 8. Which localities have defensible timing intervals?

All five complex counties, on the **alert side**, to the second. See
`reports/LEAD_TIME_RESULTS.md`.

Not one locality has a defensible **fire-arrival** interval.

## 9. Can any warning lead time be estimated?

> ## No.

Not for any locality. A warning lead time needs the hazard's arrival time where
the warned people were. The official record does not contain per-locality
arrival times, and this is structural rather than a retrieval failure: in the
government's own per-fire table **all five affected Gyeongbuk counties carry the
identical 산불발생 timestamp `3.22(토) 11:25`.**

## 10. If yes, exactly what kind of lead time is it?

Not applicable — none is reported. What *is* reported is named for what it
measures, and none of it is a lead time:

- reported ignition → first public warning (5 counties, ±1 minute)
- reported ignition → first formal 대피명령 (5 counties, ±1 minute)
- first warning → first order (5 counties, **exact to the second**)

The ±1 minute is not measurement error. It is the 11:24/11:25 **dispute**
between two primary records, and a disputed value is not a confidence interval.

## 11. What cannot be inferred from the available evidence?

- How much time anyone had. No source locates the fire relative to people.
- Whether any warning was timely. No defensible baseline exists.
- Any casualty counterfactual — out of scope, permanently.
- Physical fire arrival at any named locality at minute scale.
- Which of the **three** 2025-03-22 Uiseong ignitions reached which county.
- That a satellite detection is a fire arrival.
- That anything is absent because a request failed.

## 12. What data would most improve the result?

1. **A free FIRMS `MAP_KEY`** — by email, no account. The alert side is already
   in hand at second resolution; this supplies the only missing half of an
   `ALERT → FIRST SENSOR DETECTION` lead time. Highest leverage, zero cost.
2. **A free data.go.kr service key** — unlocks per-incident 발생/진화일시 and
   건조/강풍 특보 issuance times in one step.
3. **`KMA_API_KEY`** — turns observation *availability* into observation
   *content*.
4. **Fire-progression mapping at locality scale.** This is the only thing that
   would make a genuine warning lead time possible, and it does not appear to
   have been published.

## 13. What previous assumptions were overturned during the fresh rebuild?

This repository was **empty** at the start — `git ls-remote` returned no refs —
so there was no prior implementation to overturn. What follows is what *this
run* overturned about its own working assumptions.

**That a failed request is the thing to guard against.** The sharper failure is
a **successful** request against the wrong surface. 국민안전24 answers
`전체 0 건` for the whole window on a valid HTTP 200 query. Believed, it says no
alerts were issued. The same ministry holds 264 for this fire alone.

**That the headline table was sound.** An adversarial review found four of its
five rows selected the wrong record — three picked up identical burn-ban
boilerplate, and 영덕's was an **expressway closure notice about 서산영덕선**,
the very road this repository's geography module exists to handle. Corrected,
every figure moved **later**: 청송 from 2h13m to 77h23m. Every error had run in
the direction that flattered the response.

**That the published precision was right.** "±2 s" was the *seconds field* of
two endpoints. The intervals are **119 seconds** wide — wrong by sixty-fold,
and in the direction of overclaiming.

**That fixing named defects improves the corpus.** Round 1 verification: 32.0 %
discrepancy. Round 2, after fixing all four named clusters: **34.0 %**. The
confidence intervals overlap almost entirely. The defect mass moved from event
labels into geography rather than disappearing.

**That "one fire" was one fire.** Uiseong had **three** separate ignitions on
2025-03-22 — corroborated by three distinct 의성군 rows in a KFS dataset written
for another purpose entirely.

**That the protocol was being enforced.** The guards lived in the library; the
pipeline wrote plain dicts straight to JSON and never constructed a `Claim`, so
the class/role check never ran on a single real record.

---

## What this audit is worth

Its most reusable output is not the numbers. It is a corpus of 1,688 primary
operational records that corrects published secondary accounts, and a set of
named failure modes — **32 of them**, twelve discovered by review rather than
design — that any similar audit will hit.

Its second most useful output is the negative result, stated without hedging:
**no warning lead time is defensible for any locality**, and no credential
changes that.

The discrepancy rate is published at 34 %, higher than the round before, because
a verification process that only ever confirms the pipeline is not a
verification process. That number should be read as a property of the sampling
method, not as a quality certificate — and a third round would very likely find
a further ~30 %, in classes not yet named.
