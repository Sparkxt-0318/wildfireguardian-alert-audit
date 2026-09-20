# Roadmap

Phases run in the order of the question hierarchy (`docs/RESEARCH_QUESTION.md`).

## Phase 0 — Protocol (no data touched)
- [x] `docs/` protocol set written before any inspection of prior work
- [x] `tasks/` tracking established
- [x] Credential discovery + exposure audit of the main repository

## Phase 1 — Q1: what evidence exists and is accessible
- [ ] Source discovery: Korean emergency alerts (긴급재난문자) current access path
- [ ] Source discovery: NASA FIRMS archive semantics for March 2025
- [ ] Source discovery: GK2A AMI L2 fire product and NMSC access
- [ ] Source discovery: KFS / NIFoS / MOIS / KMA / NFA official records
- [ ] Escalation ladder run per source; `reports/SOURCE_ACCESS_STATUS.md`

## Phase 2 — implementation
- [ ] Core: intervals, time roles, evidence classes, access status
- [ ] Geography: token/context-aware Korean administrative matcher
- [ ] Korean semantics: event lexicon with negative rules
- [ ] Provenance store with SHA256 + `SOURCE_DRIFT`
- [ ] Adapters: alerts, FIRMS, GK2A, manual import
- [ ] Lead-time engine with `DetectionAssumption` + geography gate
- [ ] CLI: `sources retrieve ingest timeline verify gaps lead-time report import`
- [ ] Tests for every failure mode in `docs/FAILURE_MODES.md`

## Phase 3 — Q2/Q3: corpus and timeline
- [ ] Retrieval runs with real access-status classification
- [ ] Citation-chain crawl from tertiary to news to official
- [ ] Normalised claims + interval-censored timeline

## Phase 4 — verification
- [ ] Independent manual verification of >=50 records (separate agent role)
- [ ] Adversarial audit (separate agent role)
- [ ] `reports/CONTRADICTIONS.md`, `reports/MANUAL_VERIFICATION.md`

## Phase 5 — Q4/Q5: results and verdict
- [ ] `reports/LEAD_TIME_RESULTS.md` (may be `NO DEFENSIBLE ESTIMATE`)
- [ ] `reports/EVIDENCE_GAPS.md`, `reports/COVERAGE.md`
- [ ] `visualizations/timeline.svg`, `visualizations/evidence_map.*`
- [ ] `reports/FRESH_REBUILD_VERDICT.md` — the 13 required answers
