# Exclusion rules

Status: normative. These are enforced in code and tested.

## X-1 No class promotion
A record is excluded from a role its class cannot support:
- Wikipedia may not supply `PRIMARY_OPERATIONAL` evidence.
- A news article may not stand in for an original alert record.
- An agency web article without an explicit acquisition timestamp may not supply
  `SENSOR_ACQUISITION_TIME`.

## X-2 No time-role substitution
`PUBLICATION_TIME` is never used as `PHYSICAL_EVENT_TIME`, `ALERT_SEND_TIME`, or
`SENSOR_ACQUISITION_TIME`. `SENSOR_ACQUISITION_TIME` is never used as
`PHYSICAL_EVENT_TIME`.

## X-3 No substring geography
County/municipality assignment is **token- and context-aware**. Substring
containment is not sufficient evidence of location.

Canonical tested failure:

```
서산영덕고속도로   (Seosan-Yeongdeok Expressway)
```

contains `영덕` but **must not** imply the event occurred in 영덕군
(Yeongdeok County). Road names, expressway names, facility names, and
compound proper nouns are recognised and excluded from locality inference.
Equally, `서산` in that string must not imply Seosan City.

## X-4 No first-location capture
When multiple places appear in one sentence, timestamps and events are **not**
all assigned to the first location mentioned. Clause-level attribution is used;
where clause boundaries are ambiguous, the assignment is `UNRESOLVED`, not a guess.

## X-5 No morphological over-matching
`재발화` (re-ignition) is **not** classified as initial ignition merely because it
contains `발화`. Similarly `재진화` vs `진화`, and a generic mention of `대피`
(evacuation, as a topic) is not an `대피명령` (evacuation order) or `대피 권고`
(evacuation advisory). Longest-match-first with explicit negative rules.
Original Korean text is retained alongside every normalised label.

## X-6 No averaging of conflicts
See `docs/TIME_ONTOLOGY.md`. Conflicting timestamps are retained as conflicts.

## X-7 No inference from retrieval failure
A failed fetch never produces a `DATA_ABSENT` or `OBSERVATION_DOES_NOT_EXIST`
conclusion. See `docs/ACCESS_STATUS_MODEL.md`.

## X-8 No unbacked censoring
Non-detection does not bound fire timing without an explicit `DetectionAssumption`
object. Absent one, the system refuses to emit a bound.

## X-9 No county-wide pairing
A county-wide alert is not automatically paired with a fire detection anywhere in
that county for lead-time purposes. See `docs/INCLUSION_RULES.md`.
