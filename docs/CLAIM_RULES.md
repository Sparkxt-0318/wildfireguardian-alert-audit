# Claim rules

Status: normative.

## C-1 Permitted claim forms

Acceptable, when the evidence chain supports them:

> We reconstructed a provenance-preserving timeline from multiple evidence classes.

> Official alert-send records and satellite acquisition records permit
> interval-based timing comparisons for selected localities.

> Some historical quantities remain unobservable from public evidence.

## C-2 Forbidden claims

Forbidden **without** the specific evidence each would require — and in several
cases forbidden outright because this project cannot produce that evidence:

| Forbidden claim | Why |
|---|---|
| "Residents had exactly X minutes." | Requires physical fire-arrival truth at minute scale. Not available. |
| "The government alert was X minutes late." | Requires a defensible normative baseline *and* arrival truth. Out of scope. |
| "Fire reached this road at exactly 14:32." | Point-time physical arrival. Not observed. |
| "No alert was sent because we could not retrieve one." | Retrieval failure is not absence (X-7). |
| "Satellite detection equals physical fire arrival." | Distinct quantities (X-2). |
| "A retrieval failure proves a dataset does not exist." | X-7. |
| "X lives would have been saved." | Counterfactual casualty inference — out of scope, permanently. |

## C-3 Hedging is not a workaround
Prefixing a forbidden claim with "approximately", "roughly", "our analysis
suggests" does not make it admissible. The constraint is on the *quantity*, not
the phrasing.

## C-4 Lead-time claims must name their kind

Two different quantities, never interchangeable:

```
ALERT -> FIRST SENSOR DETECTION LEAD
ALERT -> PHYSICAL FIRE ARRIVAL LEAD
```

Any lead-time result states which one it is, in the same sentence as the number.
A result that does not name its kind is void. In practice this repository expects
to be able to speak only to the first kind, and only where geography is compatible.

## C-5 Negative results are results
`reports/LEAD_TIME_RESULTS.md` may legitimately read `NO DEFENSIBLE ESTIMATE` for
some or all localities. Numbers are not forced. An empty result table with a
correct account of why is a successful outcome.

## C-6 Coverage claims must be defined
Any coverage percentage states its target interval, the evidence classes counted,
the spatial requirement, the overlap handling, and the denominator. "Percentage of
the event documented" is not a defined quantity and is forbidden;
"retrieved-corpus temporal coverage" with a stated definition is permitted.
See `reports/COVERAGE.md`.

## C-7 Every claim carries its chain
A claim in any report links to its evidence chain. Claims whose strongest support
is `TERTIARY` or `NEWS_REPORT` say so inline, not in a footnote.
