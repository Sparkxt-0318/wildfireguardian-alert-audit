# Access status model

Status: normative.

Every acquisition attempt — automated or manual — records exactly one status.

| Status | Meaning | Typical signal |
|---|---|---|
| `RETRIEVED` | Content obtained and stored. | 2xx with usable body |
| `AUTHENTICATION_REQUIRED` | A login/session is needed. | 401/403 with login redirect; HTML login form |
| `API_KEY_REQUIRED` | A key/token parameter is needed or was rejected. | FIRMS `Invalid MAP_KEY`; `SERVICE KEY IS NOT REGISTERED ERROR` |
| `REGISTRATION_REQUIRED` | Access needs an account/approval that does not yet exist. | Portal requires 활용신청 / approval workflow |
| `ENDPOINT_MIGRATED` | The service moved. | 301/302 cross-host redirect; 서비스 종료/이전 안내 notice |
| `MANUAL_DOWNLOAD_AVAILABLE` | Data exists and is obtainable by a human through a UI, but not by this agent automatically. | Interactive archive request form; JS-only portal |
| `TEMPORARY_NETWORK_FAILURE` | Transport failed. | DNS failure, connection reset, timeout |
| `SERVER_ERROR` | The server failed. | 5xx |
| `RATE_LIMITED` | Throttled. | 429; quota message |
| `ACCESS_DENIED` | Authenticated but not permitted, or geo/robots blocked. | 403 without login affordance |
| `NOT_FOUND` | The specific resource genuinely is not at that address. | 404 on a well-formed request to a live service |
| `FORMAT_UNSUPPORTED` | Retrieved, but this repository cannot parse it. | Proprietary/binary format without a reader |
| `NO_RELEVANT_RECORD` | The correct dataset was **successfully queried** and contains nothing matching. | 200 + empty result set |
| `UNKNOWN` | Genuinely undetermined. | — |

## Hard rules

1. **`NO_RELEVANT_RECORD` requires a successful query against the appropriate
   dataset.** It is a statement about the dataset's contents, not about the
   network. If the query did not succeed, this status is forbidden.
2. **`NOT_FOUND` is not for service failures.** A 404 from a dead host, a
   404 served by a generic error page, or a 404 after a migration is
   `ENDPOINT_MIGRATED` or `TEMPORARY_NETWORK_FAILURE`, not `NOT_FOUND`.
3. **`API_KEY_REQUIRED` is not data absence.** FIRMS returning
   `Invalid MAP_KEY` means the dataset exists and is gated. It is recorded as
   `API_KEY_REQUIRED`, and the corresponding gap in
   `reports/EVIDENCE_GAPS.md` is `CREDENTIAL_REQUIRED`, never
   `OBSERVATION_DOES_NOT_EXIST`.
4. **Only after the escalation ladder is exhausted** may a gap be classified at
   all. The ladder (`docs/SOURCE_STRATEGY.md` §Escalation) is: migration →
   agency data platform → API docs → downloadable archives → alternate official
   domains → access documentation → manual import path → *then* classify.
5. `DATA_ABSENT` is a **conclusion**, not an access status, and it may only be
   reached when none of the above apply and a successful query was made.

## Relationship to evidence gaps

Access status describes *one attempt*. `reports/EVIDENCE_GAPS.md` describes the
*quantity* and aggregates across attempts, using:

```
AVAILABLE | PARTIALLY_AVAILABLE | CREDENTIAL_REQUIRED
MANUAL_DOWNLOAD_REQUIRED | NOT_RETRIEVED
OBSERVATION_DOES_NOT_EXIST | UNKNOWN
```

`OBSERVATION_DOES_NOT_EXIST` is the strongest claim in this repository and
requires an affirmative argument, not a failed fetch.
