# Source access status

Generated 2026-09-20. Statuses follow `docs/ACCESS_STATUS_MODEL.md`.

**Reading rule.** A gated or failed source is **not** an absent source. Only
`NO_RELEVANT_RECORD` says anything about what a dataset contains, and it is only
used after a successful query against the right dataset. Nothing in this table
licenses the conclusion that March 2025 records do not exist.

---

## 1. Korean emergency alerts (긴급재난문자 / CBS) — highest priority

| Source | Role | Access status | Credential | Verified |
|---|---|---|---|---|
| [safetydata.go.kr `DSSP-IF-00247`](https://www.safetydata.go.kr/disaster-data/view?dataSn=228) (dataSn=228) | **Current authoritative record-level source** | `API_KEY_REQUIRED` | `SAFETYDATA_API_KEY` | live call, HTTP **200** + `resultCode 30` |
| [data.go.kr 15134001](https://www.data.go.kr/data/15134001/openapi.do) | Catalogue **pointer only** (`API 유형: LINK`) | `RETRIEVED` (catalogue) | — | resolves to the row above |
| [국민안전24 `calamitySms.do`](https://www.safekorea.go.kr/safekorea-kor/ctim/cmsg/calamitySms.do?menuSn=34&firstYn=Y) | Public search UI, no credential | `NO_RELEVANT_RECORD` **for this surface** | none | `전체 0 건` for 2025-03-21..31 |
| SafeKorea legacy `idsiSFK/...` paths | Former alert search | `ENDPOINT_MIGRATED` | — | now serves the 국민안전24 site |
| `DisasterMsg3/getDisasterMsg1List` | Superseded predecessor | `ENDPOINT_MIGRATED` | — | official notice, below |
| [빠띠 civic mirror](https://data.campaigns.do/datasets/3wOHDP) | Third-party bulk CSV | `MANUAL_DOWNLOAD_AVAILABLE` | none | coverage **ends 2024-08-31** — does not reach March 2025 |

### The migration, verbatim from data.go.kr 15134001

> 공공데이터포털(data.go.kr)에서 제공되던, '행정안전부_재난문자방송 발령현황' /
> '행정안전부_재난문자방송 발령현황(지역별)'을 대체하는 서비스입니다. 기존 서비스는
> 조회가 제한되며 향후 폐기될 예정이므로, 앞으로 해당 정보를 이용하려는 사용자께서는
> '긴급재난문자 API' 를 신청 및 활용하여 주시기 바랍니다.

### Verified API contract (DSSP-IF-00247)

Request: `serviceKey` (**capital K**, required), `numOfRows`, `pageNo`,
`returnType` (`json`|`xml`), `crtDt` (**start** date `YYYYMMDD`; no documented
end-date parameter), `rgnNm` (시도명 or 시군구명).

Response fields: `SN`, `CRT_DT`, `MSG_CN`, `RCPTN_RGN_NM`, `EMRG_STEP_NM`,
`DST_SE_NM`, `REG_YMD`, `MDFCN_YMD`, `RCPTN_RGN_ID`, `EMRG_STEP_ID`, `DST_SE_ID`.
`CRT_DT` is `YYYY/MM/DD HH:MM:SS` — **second resolution**, which is finer than
any news report and is precisely why this source matters.
`EMRG_STEP_NM` ∈ {위급재난, 긴급재난, 안전안내}. `DST_SE_NM` includes `산불`.

Live probe with a deliberately invalid key returned **HTTP 200** with:

```json
{"header":{"resultMsg":"SERVICE KEY IS NOT REGISTERED ERROR","resultCode":"30",
 "errorMsg":"등록되지 않은 서비스키"},"body":null}
```

A status-code-only client would have recorded this as a successful retrieval of
an empty dataset. It is `API_KEY_REQUIRED`.

### Unlock path (requires a human — not performed by this agent)

1. Register at `https://www.safetydata.go.kr/registMember_1`.
   The form requires **SMS verification of a Korean mobile number**, which is a
   real barrier for non-Korean researchers.
2. Log in and 활용신청 on the dataset page (`dataSn=228`). Free; 개발단계 is
   auto-approved.
3. Set `SAFETYDATA_API_KEY` in `.env` and run `wg-alert-audit retrieve alerts`.
4. Settle coverage with one call:
   `?serviceKey=<KEY>&returnType=json&crtDt=20250322&rgnNm=경상북도`.

Contact if that call returns nothing: 재난정보통신과 044-205-4467; help desk
044-205-8461. A 정보공개청구 via `open.go.kr` is an untested escalation path.

---

## 2. Satellite active fire — NASA FIRMS

| Source | Access status | Credential | Note |
|---|---|---|---|
| FIRMS Area API `/api/area/csv/` | `API_KEY_REQUIRED` | `FIRMS_MAP_KEY` | HTTP **400** + `Invalid MAP_KEY.` |
| FIRMS `/api/data_availability/` | `API_KEY_REQUIRED` | `FIRMS_MAP_KEY` | HTTP **401**, same body |
| FIRMS `/mapserver/mapkey_status/` | `API_KEY_REQUIRED` | `FIRMS_MAP_KEY` | HTTP **403** |
| [FIRMS Archive Download Tool](https://firms.modaps.eosdis.nasa.gov/download/) | `MANUAL_DOWNLOAD_AVAILABLE` | Earthdata login **or** emailed code | asynchronous, email-delivered |
| FIRMS Country API | `ENDPOINT_MIGRATED` | — | `Invalid API call.`; commented out of the API index |
| LAADS DAAC `VNP14IMG` / `VJ114IMG` v002 | `AUTHENTICATION_REQUIRED` | Earthdata login | L2 swath archive |

**The same body, `Invalid MAP_KEY.`, arrives with three different status codes
(400, 401, 403) across three FIRMS endpoints.** Any classifier keyed on status
code alone will mis-handle at least one of them.

### March 2025 needs the SP archive, not NRT

FIRMS splits each sensor into a rolling **NRT** window and a contiguous **SP**
(science-quality) archive behind it, with roughly a five-month lag. Querying
`VIIRS_SNPP_NRT` for March 2025 returns nothing **because the date has moved out
of the NRT window**, not because nothing was observed. Correct sources:

```
VIIRS_SNPP_SP    VIIRS_NOAA20_SP    MODIS_SP    VIIRS_NOAA21_NRT
```

`VIIRS_NOAA21_SP` is rejected by the Area API — NOAA-21 has no SP stream, so its
NRT window reaches back to mission start. The `version` column carries SP/NRT
provenance in band (`"2.0"` vs `"2.0NRT"`) and is retained on every row.

`acq_date`/`acq_time` are **UTC**. KST 00:00–08:59 falls on the *previous* UTC
date, so a March 2025 query must span 2025-02-28 → 2025-04-01 UTC or lose
detections at both ends.

Unlock: free key by email at `https://firms.modaps.eosdis.nasa.gov/api/map_key/`,
then set `FIRMS_MAP_KEY`.

---

## 3. GK2A / 천리안위성 2A — L2 Forest Fire (산불탐지, `ff`)

| Source | Access status | Credential | Note |
|---|---|---|---|
| **NMSC public product tree** `nmsc.kma.go.kr/IMG/GK2A/AMI/L2/FF/` | **`RETRIEVED`** | **none** | rendered PNG twins; **635 slots retrieved for the target window** |
| KMA API Hub `GK2A/LE2/FF` | `API_KEY_REQUIRED` | `KMA_API_KEY` | HTTP 401; retention stated as 2019-07 → present |
| NMSC data service `datasvc.nmsc.kma.go.kr` | `SERVER_ERROR` | membership | HTTP 503 on the web app; static PDFs on the same host return 200 |
| [기상자료개방포털](https://data.kma.go.kr/data/rmt/rmtList.do?code=21&pgmNo=683) | `REGISTRATION_REQUIRED` | portal login | NetCDF + PNG, 제공기간 2019-07-25 → |
| AWS `noaa-gk2a-pds` | `NO_RELEVANT_RECORD` for L2 | none | holds **L1B only**; March 2025 L1B is present and anonymous |

The product exists and is officially documented: ATBD `GK2A_L2_ATBD_국문_산불탐지_FF`,
NetCDF variables **`FF`** (0=fill, 1=fire) and **`DQF_FF`** (0–13 quality flags,
where 8=Fire, 9=Absolute fire, 10=Industrial heat). Naming:
`gk2a_ami_le2_ff_<scn>020<pr>_<YYYYMMDDHHMM>.nc`, timestamp in **UTC**.
Cadence: KO 2 min, EA/FD 10 min.

**The `datasvc` 503 is a service failure, not a statement about the data.** The
API Hub independently states retention from 2019-07.

### Soft-404 trap

A missing slot on the NMSC tree returns **HTTP 200** with a ~1,019-byte
`text/html` body, not a 404. Any harvester keyed on status code would record
non-existent slots as successfully retrieved. `adapters/gk2a.py` checks
content-type and length.

---

## 4. Escalation ladder — applied, not skipped

`docs/SOURCE_STRATEGY.md` requires seven steps before any gap is classified.
Worked example, the emergency-alert track:

| Step | Action | Outcome |
|---|---|---|
| 1 | search for migration | legacy `idsiSFK` paths → 국민안전24; `DisasterMsg3` → `DSSP-IF-00247` |
| 2 | agency's current data platform | safetydata.go.kr identified as authoritative |
| 3 | API documentation | full spec table retrieved, incl. all 15 result codes |
| 4 | downloadable archives | official sample capped at 100 rows; no bulk export found |
| 5 | alternate official domains | data.go.kr entry is a `LINK` pointer, not independent |
| 6 | documentation describing access | registration + 활용신청 procedure recorded |
| 7 | manual import implemented | `wg-alert-audit import <file> --kind alerts` |
| → | **then** classify | `API_KEY_REQUIRED` / `CREDENTIAL_REQUIRED` |

Three transient failures encountered during retrieval (GK2A slots at 2025-03-25
05:30, 2025-03-25 11:00, 2025-03-29 04:00 UTC) were initially `SERVER_ERROR` and
**all three returned the product on re-probe**. Had they been recorded on first
attempt, the audit would carry three false absences.

---

## 5. Credential status

Metadata only. No value is read, logged, or stored anywhere in this repository.

| Service | Variable | Status |
|---|---|---|
| NASA FIRMS | `FIRMS_MAP_KEY` (alias `NASA_FIRMS_MAP_KEY`) | `ABSENT` |
| MOIS disaster-safety platform | `SAFETYDATA_API_KEY` | `ABSENT` |
| 공공데이터포털 | `DATA_GO_KR_SERVICE_KEY` | `ABSENT` |
| KMA | `KMA_API_KEY` (alias `WILDFIREGUARDIAN_KMA_API_KEY`) | `ABSENT` |
| NMSC | `NMSC_API_KEY` | `ABSENT` |
| NASA Earthdata | `EARTHDATA_TOKEN` | `ABSENT` |

**Exposure audit of the main WildfireGuardian repository: no finding.** The full
1000-commit history across all refs was scanned for key-shaped assignments, for
AWS/Google/GitHub/OpenAI/JWT key shapes, and for bare 32-hex tokens. Zero hits on
the first two; the 13 hits on the third were all academic-citation URL path
segments. **No `POTENTIALLY_EXPOSED_CREDENTIAL`; no rotation recommended on this
basis.** See `docs/DECISIONS.md` D-004.
