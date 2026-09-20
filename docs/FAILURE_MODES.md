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
| FM-09 | Averaging conflicting timestamps. | No mean operation on conflicting claims; `tests/test_time_semantics.py` |
| FM-10 | Inferring a bound from non-detection without a model. | `DetectionAssumption` required; `tests/test_censoring.py` |
| FM-11 | Pairing a county-wide alert with an arbitrary in-county detection. | Geography compatibility gate; `tests/test_lead_time.py` |
| FM-12 | Equating sensor detection with physical arrival. | Distinct quantities; `tests/test_lead_time.py` |
| FM-13 | Silently overwriting changed web content. | `SOURCE_DRIFT` record on SHA256 mismatch; `tests/test_provenance_and_credentials.py` |
| FM-14 | Leaking a credential into logs/reports/URLs. | `redact()` on every emitted URL; `tests/test_provenance_and_credentials.py` |
| FM-15 | Promoting tertiary evidence to primary. | Class promotion rules; `tests/test_evidence_class.py` |
| FM-16 | Reporting an undefined coverage percentage. | Coverage metric requires an explicit definition object. |
| FM-17 | Assuming all reports describe one incident. | Explicit incident IDs; `UNRESOLVED` allowed. |
| FM-18 | Stopping the search at the first failed endpoint. | Escalation ladder recorded per source in `reports/SOURCE_ACCESS_STATUS.md`. |
| FM-19 | Using `NO_RELEVANT_RECORD` without a successful query. | Status requires a 2xx + parsed empty result. |
| FM-20 | Minute-resolution times treated as instants. | Minute values expand to `[mm:00, mm:59]`. |

## Discovered by review, not by design

These were not anticipated. Each was found by an independent reading of the
data or the code, and each now has a regression test.

| ID | Failure | Guard |
|---|---|---|
| FM-21 | A keyword filter (`"산불" in text`) selecting burn-ban boilerplate and a road-closure notice as "the first warning". | `korean.classify_alert_purpose`; `tests/test_adversarial_regressions.py` |
| FM-22 | Reporting an interval's *seconds field* as its width — "±2 s" for a 119 s interval. | `tests/test_adversarial_regressions.py::TestC2_IntervalWidthIsNotTwoSeconds` |
| FM-23 | A filter whose floor makes a metric structurally incapable of a negative result. | floor removed; `docs/DECISIONS.md` D-008 |
| FM-24 | An eup/myeon name that is not nationally unique resolving into the in-scope province (무주군 부남면 → 청송군). | out-of-scope municipality blocks parent inference; `tests/test_adversarial_regressions.py::TestM6_CrossProvinceCollision` |
| FM-25 | Korean suffix-elided coordination (「남선, 임하, 길안면」) losing all but the last conjunct. | `geography._expand_elided_suffixes` |
| FM-26 | A superlative quantity asserted hundreds of times, draining the field of information. | `PUBLIC_WARNING` added; `is_first_public_warning_for_county` holds once per county; `tests/test_corpus_integration.py` |
| FM-27 | A declared superset that is not one (orders exceeding directives). | invariant tested on the corpus |
| FM-28 | Protocol enforcement living in a library the pipeline never calls. | `tests/test_corpus_integration.py` round-trips every event through `Claim` |
| FM-29 | A truncated harvest indistinguishable from a complete one. | collected count compared with the listing's 「전체 N 건」 |
| FM-30 | A stated acceptance test that the code does not implement (`image/png` unchecked). | `gk2a.probe_slot` checks content-type |
| FM-31 | A report not regenerated from its data drifting away from it (COVERAGE Metric 2 reporting 0 % after the harvest). | reports rebuilt from the data files |
| FM-32 | An advisory *lifting* an order counted as issuing one (「대피명령을 해제」). | negative rule; tested |
