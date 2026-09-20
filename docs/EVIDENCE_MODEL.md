# Evidence model

Status: normative.

## Evidence classes

Every source-derived record carries **exactly one** primary evidence class.

| Class | Meaning | Examples |
|---|---|---|
| `PRIMARY_OPERATIONAL` | A record produced *by the operational system itself, at the time*, as part of doing the thing. | The original CBS / 긴급재난문자 record; an original official dispatch record; a timestamped operational bulletin issued during the event. |
| `REMOTE_SENSING` | An actual sensor or sensor-product record carrying a real acquisition time. | A VIIRS/MODIS active-fire detection row; a GK2A AMI L2 product granule; any sensor record with a genuine acquisition timestamp. |
| `OFFICIAL_RETROSPECTIVE` | An official body's account written *after* the event. | KFS/NIFoS/MOIS/KMA post-event report; an official chronology compiled later; a statistics yearbook entry. |
| `NEWS_REPORT` | Journalism. | Yonhap, KBS, MBC, SBS, newspapers, broadcasters. |
| `TERTIARY` | Aggregation without original reporting. | Wikipedia; unsourced summaries; aggregators. |
| `DERIVED` | A calculation performed by this repository. | An interval difference; a coverage metric; a normalised geography assignment. |

## Promotion rules (hard)

1. **A news article never becomes `PRIMARY_OPERATIONAL` by quoting an official.**
   A quotation is reportage about a record, not the record.
2. **Tertiary never becomes primary.** Wikipedia citing Yonhap citing KFS remains
   `TERTIARY` for the Wikipedia node. Each node in the chain keeps its own class.
3. **A press article describing satellite imagery is not `REMOTE_SENSING`.**
   Only an actual sensor/product record qualifies. An article about GK2A imagery
   is `NEWS_REPORT` (or `OFFICIAL_RETROSPECTIVE` if the agency published it).
4. **A NASA/agency web article without an explicit acquisition timestamp cannot
   supply remote-sensing *timing* evidence.** It may supply a publication time only.
5. **`OFFICIAL_RETROSPECTIVE` does not outrank `PRIMARY_OPERATIONAL`** merely because
   it is official. Retrospective reconstruction is a different epistemic object from
   an operational-at-the-time record, and the distinction is recorded explicitly on
   every official item (`operational_at_time: true|false`).
6. Class is a property of **the artifact**, not of the claim it carries. One artifact
   may carry many claims; all inherit that artifact's class.

## Source-upgrade graph

Evidence is stored as a DAG, not a flat list. Discovering a stronger source
**never deletes** the weaker one; it adds an edge.

```
TERTIARY            Wikipedia says alert at 15:30
     | cites
NEWS_REPORT         Yonhap reports alert at 15:30
     | quotes official / yields record ID
PRIMARY_OPERATIONAL CBS record shows 15:30:17
```

Each edge is typed: `CITES`, `QUOTES`, `REPRODUCES`, `SUPERSEDES`, `CONTRADICTS`,
`CORROBORATES`. The graph is the audit trail; the strongest node is the *current
best evidence*, and the chain that reached it stays attached to the claim.

## Incident identity

Incidents get explicit IDs (`INC-<county>-<nnn>`). Two records are placed on the
same incident only when evidence supports it. Where sources disagree about whether
two reports describe one fire or two, both readings are retained and the conflict
is logged in `reports/CONTRADICTIONS.md`.

`재발화` (re-ignition / flare-up) is **never** silently merged into the initial
ignition of the same incident; it is a distinct event on the incident timeline.

## Claim object

A claim is the atomic unit of the audit:

```
claim_id
incident_id
quantity          # one of the distinct quantities below
time_interval     # see TIME_ONTOLOGY.md; may be unbounded or unknown
time_role         # what kind of time this is
geography         # normalised, with match relation and uncertainty
evidence_class    # inherited from the artifact
source_id         # -> artifact with full provenance
raw_text          # verbatim original, Korean preserved
confidence_notes
```

## Distinct quantities — never conflated

```
ignition
reported ignition
first sensor detection
first official awareness
first public warning
fire arrival (physical)
road impact
evacuation order
containment
re-ignition
```

Some of these may remain permanently unobservable from public evidence.
That is an acceptable and expected result.
