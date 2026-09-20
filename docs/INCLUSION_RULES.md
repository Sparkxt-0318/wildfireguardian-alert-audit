# Inclusion rules

Status: normative. A record enters the corpus only if it satisfies **all** of these.

## I-1 Provenance complete
The artifact records `source_id`, URL (or manual-import origin), `retrieval_time`,
`sha256`, `content_type`, `evidence_class`, `language`, `access_status`, and
`publication_time` where knowable. Missing `sha256` or `retrieval_time` is
disqualifying.

## I-2 Raw text preserved
The original bytes are stored immutably under `data/raw/`. For a claim, the
verbatim source span (Korean preserved, unnormalised) is attached.

## I-3 Time role assigned
Every timestamp carries an explicit role from `docs/TIME_ONTOLOGY.md`. A bare
timestamp is not admissible.

## I-4 Temporal relevance
The claim bears on the target interval **2025-03-21T00:00:00+09:00 through
2025-04-05T00:00:00+09:00** (inclusive-exclusive), or on the access status of a
dataset covering it. Sources outside the window are admissible only as
*methodological* evidence (e.g. API documentation), never as event evidence.

## I-5 Spatial relevance
The claim bears on Gyeongsangbuk-do (경상북도) or on a named locality within it,
or on a sensor footprint intersecting it. Geographic assignment must survive the
token/context-aware matcher (`docs/EXCLUSION_RULES.md` X-3).

## I-6 Evidence class assignable
Exactly one primary class applies and is justifiable from the artifact itself.

## I-7 Incident attributable — or explicitly not
Either the claim is attributed to a specific incident ID, or it is explicitly
recorded as `incident_id: UNRESOLVED`. Silent attribution to the nearest
incident is forbidden.

## Admissibility for lead-time computation (stricter)

A claim may enter a lead-time calculation only if additionally:

- both sides have compatible **time roles** (`docs/CLAIM_RULES.md` C-4);
- geography compatibility is `EXACT_LOCALITY`, `SAME_EUP_MYEON`, or
  `SENSOR_FOOTPRINT_INTERSECTS` — `SAME_COUNTY` alone is **not** sufficient;
- the alert side is `PRIMARY_OPERATIONAL` **or** the result is explicitly
  labelled as resting on reported (news) alert times;
- any use of non-detection as a bound is backed by a `DetectionAssumption`.
