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
