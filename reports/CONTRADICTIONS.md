# Contradiction registry

Generated 2026-09-20.

Conflicts are **retained, not resolved**. `docs/TIME_ONTOLOGY.md` forbids
averaging conflicting timestamps, and `docs/EVIDENCE_MODEL.md` forbids deleting
the weaker record when a stronger one appears. Where an explanation is offered
it is labelled `HYPOTHESIS` and carries no evidentiary weight.

---

## C-01 — Uiseong ignition: 11:24 vs 11:25

**Status: UNRESOLVED. Both retained.**

The conflict sits inside the *primary operational records themselves* — two
county governments, issuing official emergency alerts 98 seconds apart, state
different ignition minutes for a fire at the same street address.

| Value | Source | Class | Sent / published |
|---|---|---|---|
| **11:25** | 의성군청 emergency alert | `PRIMARY_OPERATIONAL` | 2025/03/22 **15:16:22** |
| **11:24** | 안동시 emergency alert | `PRIMARY_OPERATIONAL` | 2025/03/22 **15:18:00** |
| **11시 24분경** | MOIS 보도자료, same day | `PRIMARY_OPERATIONAL` | 2025-03-22 |
| **11:25** | MOIS 중대본 4차 status table | `PRIMARY_OPERATIONAL` | 2025-03-25 |
| **11:25** | MOIS 중대본 8차 status table | `PRIMARY_OPERATIONAL` | 2025-03-29 |

Verbatim:

> 「오늘 **11:25** 안평면 괴산리 산61(**발화지점**) 산불 발생. 입산 금지, 창문개방 자제.」 [의성군청]

> 「금일 **11:24** 의성군 안평면 괴산리 산 61번지 일원 산불 발생하여 확산중. 입산 금지.」 [안동시]

> 「…오늘(22일) **11시 24분경** 경상북도 의성군 안평면에서 발생한 산불이…」 — MOIS 보도자료, 2025-03-22

**Representation.** The audit records the reported-ignition interval as the
hull of both readings:

```
reported ignition = [2025-03-22T11:24:00+09:00, 2025-03-22T11:25:59+09:00]
```

a 119-second interval. It is **not** recorded as 11:24:30. Note that even the
"agreeing" sources agree only to the minute, so no source anywhere places the
ignition to the second.

**HYPOTHESIS (unevidenced):** the two counties drew on the same 119 신고 record
and rounded or transcribed differently, or one used report-received time and the
other used an estimated start. Nothing retrieved supports either reading, and
the minute-level discrepancy is small enough that it changes no conclusion in
this audit.

---

## C-02 — Andong: 2025-03-22 11:25 vs 2025-03-24 17:02

**Status: UNRESOLVED. Both retained. Probably measuring different things.**

| Value | Source | Class | Nature |
|---|---|---|---|
| **3.22(토) 11:25** | MOIS 중대본 8차 per-fire table | `PRIMARY_OPERATIONAL` | operational-at-the-time |
| **2025. 3. 24.(월) 17:02** | 안동시 대형산불 종합안내 portal | `OFFICIAL_RETROSPECTIVE` | retrospective |

Verbatim:

> 「발생 일시 : **2025. 3. 24.(월) 17:02** [주불진화 : 3. 28.(금) 17:00]」 — 안동시
> 「**3. 22. 의성군 안계면, 안평면 산불로부터 확산**」 — 안동시, same page

**This is a quantity conflict, not merely a time conflict.** `docs/EVIDENCE_MODEL.md`
requires `ignition`, `fire arrival` and `reported ignition` to stay distinct. The
central government table assigns Andong the *complex's* ignition timestamp; the
city's own page appears to record when fire **arrived in Andong**. The city page
itself says the fire spread from Uiseong on 3.22, so the two are not making the
same assertion.

**Consequence for the audit.** The `3.24 17:02` figure is the closest thing found
to a *fire-arrival* time for any locality — and it is a single retrospective
municipal web page, at hour-minute resolution, for a whole city. It is recorded
as `OFFICIAL_RETROSPECTIVE` with quantity `fire_arrival` and geography `안동시`
(county-level), which under D-006 is **too coarse to pair with any alert** for a
lead-time computation. See `reports/LEAD_TIME_RESULTS.md`.

---

## C-03 — The five Gyeongbuk counties share one ignition timestamp

**Status: not a contradiction between sources — a structural property of the
official record that must not be mistaken for five measurements.**

MOIS 중대본 8차 (2025-03-29) per-fire table, verbatim:

> 「경북 의성 | 경북 안동 | 경북 영덕 | 경북 영양 | 경북 청송
> 산불발생 **3.22(토) 11:25 | 3.22(토) 11:25 | 3.22(토) 11:25 | 3.22(토) 11:25 | 3.22(토) 11:25**」

All five carry the **identical** timestamp. The official record treats them as
one administrative fire, timestamped to the Uiseong ignition. It therefore
contains **no per-county ignition or arrival times**.

Independently corroborated: KFS dataset `15121205` (산불상태별 이력), queried
successfully for 2025-03-22..03-31, contains rows for 의성 (3) and 안동 (1) and
**zero rows for 청송, 영양 or 영덕**. That is a structural absence in a
successfully-queried dataset — `NO_RELEVANT_RECORD`, correctly used — and it
matches the administrative consolidation rather than contradicting it.

**Consequence.** Any per-county ignition time encountered elsewhere does **not**
come from the official operational record and must be traced to its own source
before use.

---

## C-04 — 11:38 is suppression-start, not ignition

**Status: resolved as a category error, logged to prevent recurrence.**

KFS dataset `15121205`, row 359264:

```
359264 | 2025-03-22 | 경상북도 의성군 안평면 | 진화시작 2025-03-22 11:38 | 진화완료 2025-03-28 17:15
```

`진화시작시간` is **suppression start**, roughly 13–14 minutes after the reported
ignition. It is a real, well-evidenced timestamp for a *different quantity*.
Treating it as a third ignition candidate would be exactly the conflation
`docs/EVIDENCE_MODEL.md` prohibits. Recorded under a distinct quantity, not
merged into the ignition interval.

---

## C-05 — Burned-area figures are not comparable across sources

**Status: UNRESOLVED as stated; the sources use different denominators.**

| Figure | Scope | Source | As of |
|---|---|---|---|
| **48,239 ha** | the 11 government-managed fires | MOIS 중대본 | 2025-03-30 |
| **46,927 ha** | 울산·경북·경남 stage-3 fires | MOIS 중대본 7차 | 2025-03-28 06:00 |
| **9,896 ha** | Andong, central figure | MOIS 중대본 7차 | 2025-03-28 06:00 |
| **26,708 ha (잠정)** | Andong, municipal figure | 안동시 portal | retrospective |
| 104,000–116,000 ha | the wider March–May 2025 season | secondary sources | various |

The Andong pair (9,896 vs 26,708 ha) differ by a factor of 2.7 and are both
official. Neither is "wrong"; they are differently scoped, and the municipal
figure is explicitly provisional (잠정). **No figure in this table may be
compared with another without first matching scope and as-of date.**

---

## C-06 — Casualty figures were revised upward throughout

**Status: not a contradiction. A time series, which must never be quoted as a
single number without its as-of timestamp.**

| Deaths | As of | Source |
|---|---|---|
| 14 | 2025-03-26 07:00 | MOIS 중대본 5차 |
| 28 | 2025-03-28 06:00 | MOIS 중대본 7차 |
| 30 | 2025-03-30 12:00 | MOIS 중대본, 주불진화 완료 |

Each figure is correct as of its own timestamp. Quoting an early figure as final,
or a final figure as though known earlier, misrepresents the record.

---

## C-07 — Incident-identity trap: a different Uiseong fire

**Status: resolved. Logged because it nearly corrupted the corpus.**

MOIS article `nttId=123054`, titled 「행정안전부 장관, 경북 의성군 산불 관련
긴급 지시」, ranks highly in searches for this event. It is dated **2026-01-10**
and concerns a **different fire**:

> 「**1월 10일 15시 14분** 경북 의성군 **의성읍 비봉리 산 135-1**」

Different date, different year, different 읍/면, different minister. Its title is
near-identical to the genuine 2025-03-22 release.

This is precisely the hazard `docs/RESEARCH_QUESTION.md` anticipates — *"Do not
assume that all reports refer to the same ignition, fire complex, or local
incident"* — and it is why every claim carries an explicit `incident_id` and
why publication date is verified on every retrieved article.

---

## C-08 — 국민안전24 shows zero alerts; the archive shows many

**Status: not a contradiction about the world. A contradiction between
retrieval surfaces, and the single most important reading lesson of this audit.**

| Surface | Result for 2025-03-21..03-31 |
|---|---|
| 국민안전24 `calamitySms.do` | `전체 0 건` — verified independently twice |
| safetydata.go.kr `/disaster-data/disasterNotification` | hundreds of records, second-precision |

Both were queried successfully. Both returned HTTP 200. They disagree completely,
because the first has a retention boundary around early 2026 and the second does
not.

**Had the audit queried only the first surface, it would have concluded that no
emergency alerts were issued during the March 2025 Gyeongbuk wildfires.** That
conclusion would have been false, and it would have been reached through a
*successful* query rather than a failed one — which is why
`docs/ACCESS_STATUS_MODEL.md` requires `NO_RELEVANT_RECORD` to be scoped to the
surface queried and never generalised to the world.
