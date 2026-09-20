# Failure modes

Status: normative. Each has a test. IDs are referenced from code and tests.

| ID | Failure | Guard |
|---|---|---|
| FM-01 | Treating a failed HTTP request as data absence. | `AccessStatus` classifier; `tests/test_access_semantics.py` |
| FM-02 | Using FIRMS UTC `acq_date`/`acq_time` as KST wall-clock. | Explicit tz on ingest; `tests/test_time_semantics.py` |
| FM-03 | Treating a news-reported alert time as the alert record. | `REPORTED_ALERT_SEND_TIME` role; `tests/test_evidence_class.py` |
| FM-04 | Treating an article's publication time as an acquisition time. | Role separation; `tests/test_time_semantics.py` |
| FM-05 | Substring county matching (`서산영덕고속도로` -> 영덕군). | Token/context matcher; `tests/test_geography.py` |
| FM-06 | Assigning all times in a sentence to the first-mentioned place. | Clause-level attribution; `tests/test_geography.py` |
| FM-07 | `재발화` classified as initial ignition. | Longest-match + negative rules; `tests/test_korean_semantics.py` |
| FM-08 | Generic `대피` mention read as `대피명령`. | Explicit order/advisory lexicon; `tests/test_korean_semantics.py` |
| FM-09 | Averaging conflicting timestamps. | No mean operation on conflicting claims; `tests/test_intervals.py` |
| FM-10 | Inferring a bound from non-detection without a model. | `DetectionAssumption` required; `tests/test_censoring.py` |
| FM-11 | Pairing a county-wide alert with an arbitrary in-county detection. | Geography compatibility gate; `tests/test_lead_time.py` |
| FM-12 | Equating sensor detection with physical arrival. | Distinct quantities; `tests/test_lead_time.py` |
| FM-13 | Silently overwriting changed web content. | `SOURCE_DRIFT` record on SHA256 mismatch; `tests/test_provenance.py` |
| FM-14 | Leaking a credential into logs/reports/URLs. | `redact()` on every emitted URL; `tests/test_credentials.py` |
| FM-15 | Promoting tertiary evidence to primary. | Class promotion rules; `tests/test_evidence_class.py` |
| FM-16 | Reporting an undefined coverage percentage. | Coverage metric requires an explicit definition object. |
| FM-17 | Assuming all reports describe one incident. | Explicit incident IDs; `UNRESOLVED` allowed. |
| FM-18 | Stopping the search at the first failed endpoint. | Escalation ladder recorded per source in `reports/SOURCE_ACCESS_STATUS.md`. |
| FM-19 | Using `NO_RELEVANT_RECORD` without a successful query. | Status requires a 2xx + parsed empty result. |
| FM-20 | Minute-resolution times treated as instants. | Minute values expand to `[mm:00, mm:59]`. |
