# Completed

## Phase 0 — 2026-09-20

- Confirmed the target repository was empty (`git ls-remote` returned no refs;
  no local commits). No prior implementation existed to archive or inherit.
- Wrote the full protocol set in `docs/` **before** inspecting any prior work:
  `RESEARCH_QUESTION`, `EVIDENCE_MODEL`, `TIME_ONTOLOGY`, `SOURCE_STRATEGY`,
  `ACCESS_STATUS_MODEL`, `INCLUSION_RULES`, `EXCLUSION_RULES`, `CLAIM_RULES`,
  `FAILURE_MODES`, `DECISIONS`.
- Established `tasks/ROADMAP.md`, `tasks/CURRENT.md`, `tasks/COMPLETED.md`.
- Credential discovery against the main WildfireGuardian repository: identified
  `FIRMS_MAP_KEY` / `NASA_FIRMS_MAP_KEY`, `KMA_API_KEY`, `CDSAPI_KEY`,
  `MAPBOX_TOKEN` as the established names and the env-var mechanism as the
  established supply route (D-002).
- Credential exposure audit over the full 1000-commit history: no exposed
  credential found (D-004).

## Phase 1 — source discovery — 2026-09-20

- Four independent research tracks: Korean emergency alerts, NASA FIRMS archive
  semantics, GK2A/NMSC, and KFS/NIFoS/MOIS/KMA official records.
- Identified `DSSP-IF-00247` on safetydata.go.kr as the current authoritative
  alert source; confirmed the legacy SafeKorea paths are migrated, not retired.
- Established that March 2025 needs the FIRMS **SP** archive, not NRT, and that
  an empty NRT result for that date is a rolling-window artefact.
- Confirmed the GK2A L2 Forest Fire product (`ff`) exists, with `FF`/`DQF_FF`
  NetCDF variables, and found its **credential-free** rendered product tree.
- Credential exposure audit of the main repository: no finding (D-004).

## Phase 2 — implementation — 2026-09-20

- Core: intervals, evidence classes, time roles, access status, geography,
  Korean semantics, provenance, lead-time engine, CLI.
- 196 tests, at least one per named failure mode.
- Two real parser bugs caught by tests rather than by review: the 로 particle
  vs road suffix collision, and 고속도 ending in the same 도 as 경상북도.

## Phase 3 — corpus and timeline — 2026-09-20

- Harvested 1,688 alert records; 264 about this fire; 311 claims.
- Probed 650 GK2A observation slots; 635 retrieved; all 15 misses inside the
  documented 00:40–00:50 UTC instrument gap, reproduced on three sampled days.
- Three transient `SERVER_ERROR` slots re-probed and all three available —
  three false absences avoided.
- Computed the alert-timing intervals the evidence supports, and established
  that no warning lead time is defensible for any locality.
