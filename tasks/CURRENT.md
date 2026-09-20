# Current

**Phases 0–3 complete.** Protocol written before any data was touched; engine,
adapters and CLI implemented with 196 tests; source discovery run across four
independent tracks; corpus built and the timeline constructed.

**Corpus as it stands**

| | |
|---|---|
| Emergency alert records harvested | 1,688 (264 about this fire) |
| Claims in the timeline | 311, across 5 counties |
| Formal 대피명령 / evacuation directives | 132 / 181 |
| GK2A L2 FF observation slots | 635 retrieved of 650 probed |
| Tests | 196 passing |

**Phase 4 in progress.** Two independent roles are running against the finished
corpus: manual verification of a pre-registered 50-claim random sample (seed
20250322), and an adversarial audit of the repository's own conclusions.

**Known open items**

- No PR is open. The target repository was empty, so this branch became the
  default branch and there is no base to merge into. Raised with the user
  rather than fabricating a base branch.
- `reports/MANUAL_VERIFICATION.md` and `reports/FRESH_REBUILD_VERDICT.md` are
  pending the two verification passes.
