# wg-alert-audit

A historical evidence audit of the **March 2025 Gyeongbuk wildfires**
(경상북도 산불), asking what publicly or legitimately accessible evidence can
establish about the timing of wildfire progression, official emergency alerts,
and observation availability — and, just as importantly, what it cannot.

> **This is not a wildfire simulator, not an evacuation counterfactual model,
> and it is not permitted to infer lives saved.** A negative result is a
> legitimate outcome and the project is optimised for the strongest result the
> evidence actually supports, not for producing a positive one.

---

## The one idea

Most of this repository exists to keep two things apart:

```
DATA DOES NOT EXIST          vs          DATA EXISTS BUT WE COULD NOT GET IT
```

A failed HTTP request is not evidence of absence. Neither is a successful
request against the wrong surface. During this audit the public 국민안전24 alert
search returned `전체 0 건` — HTTP 200, valid query, empty result — for the entire
target window. Taken at face value that reads as *no emergency alerts were
issued during the March 2025 Gyeongbuk wildfires*. It is false. The same
ministry's data platform publishes hundreds of them, with send times to the
second.

That is why every acquisition attempt here carries one of fourteen explicit
access statuses, and why only one of them — `NO_RELEVANT_RECORD`, which requires
a **successful query against the correct dataset** — is allowed to say anything
about what exists in the world.

---

## What the audit found

| | |
|---|---|
| **Primary alert records** | Obtained without any credential, second-precision send times, full message text, including explicit 「(대피명령 발령)」 evacuation orders |
| **Observation availability** | 635 of 650 probed GK2A L2 Forest Fire slots across 15 consecutive days; all 15 misses fall inside the documented instrument gap |
| **Satellite fire detections** | `CREDENTIAL_REQUIRED` — endpoints verified live and gated, not absent |
| **Physical fire arrival** | Not established. No source places fire at a named locality at minute scale |
| **Warning lead time** | See [`reports/LEAD_TIME_RESULTS.md`](reports/LEAD_TIME_RESULTS.md) |

Start with [`reports/FRESH_REBUILD_VERDICT.md`](reports/FRESH_REBUILD_VERDICT.md).

---

## Install and run

```bash
pip install -e .
wg-alert-audit sources          # every source, its access status, how to unlock it
wg-alert-audit retrieve gk2a --start 2025-03-25 --end 2025-03-26
wg-alert-audit parse "영덕군 지품면에 대피명령이 내려졌다"
wg-alert-audit verify           # re-hash the stored corpus
wg-alert-audit report           # list generated reports
```

Credentials, if you have them, go in `.env` (gitignored). Copy `.env.example`,
which contains variable **names only**. The primary names deliberately match the
main WildfireGuardian repository's, so an existing `.env` works here unchanged.
No credential value is ever printed, logged, stored, or committed — every
emitted URL passes through `redact()`.

---

## How to read the code

| Module | What it refuses to do |
|---|---|
| `core/intervals.py` | Collapse a minute-resolution source into an instant; average two conflicting times |
| `core/model.py` | Let a news article supply an `ALERT_SEND_TIME`, or an agency blog supply a `SENSOR_ACQUISITION_TIME` |
| `core/access.py` | Report a network failure, a redirect, or a gated dataset as absent data |
| `core/geography.py` | Read `서산영덕고속도로` as evidence of 영덕군; assign every timestamp in a sentence to the first place named |
| `core/korean.py` | Classify `재발화` as `발화`, or a mention of `대피` as a `대피명령` |
| `core/lead_time.py` | Pair a county-wide alert with an arbitrary in-county detection; treat a satellite detection as fire arrival |
| `core/provenance.py` | Silently overwrite changed web content |

The rules those modules enforce are written down first, in `docs/`, and were
committed **before any data was touched** — the first commit contains no
parsers and no data, so the ordering is checkable in `git log`.

---

## Layout

```
docs/       the protocol: research question, evidence model, time ontology,
            access-status model, inclusion/exclusion rules, claim rules,
            20 named failure modes, and a decisions log
tasks/      roadmap, current state, completed work
src/        the audit engine, adapters and CLI
tests/      one or more tests per named failure mode
data/       raw/ (content-addressed + provenance ledger), normalized/, timeline/
reports/    the findings
visualizations/
```

---

## Testing

```bash
python -m pytest -q
```

Every failure mode in [`docs/FAILURE_MODES.md`](docs/FAILURE_MODES.md) has at
least one test. Two real bugs were caught this way and are worth knowing about
if you touch `core/geography.py`:

- `안동시로` ("to Andong City") parsed as a road, because `로` is simultaneously
  the directional particle and the commonest road suffix.
- `서산영덕고속도로` nearly parsed as the province `경상북도`, because `고속도`
  ends in the same `도`.

---

## Licence

MIT. Retrieved source material remains under its original terms; the MOIS
alert data is 공공저작물 제4유형 (출처표시, 상업적 이용금지, 변경금지).
