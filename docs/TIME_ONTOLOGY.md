# Time ontology

Status: normative.

Every timestamp in this repository carries a **role**. A timestamp without a role
is not admissible evidence. One role is never silently substituted for another.

## Roles

| Role | Meaning |
|---|---|
| `PHYSICAL_EVENT_TIME` | When the physical thing happened in the world (fire arrived, ignition occurred). Rarely directly observed. |
| `ALERT_SEND_TIME` | When an alerting system actually transmitted a message. |
| `REPORTED_ALERT_SEND_TIME` | When a *secondary source says* an alert was sent. Not the same as `ALERT_SEND_TIME`. |
| `SENSOR_ACQUISITION_TIME` | When a sensor observed the scene. |
| `PROCESSING_TIME` | When a product was generated from sensor data. |
| `PUBLICATION_TIME` | When a document/article/page was published. |
| `REPORT_TIME` | The time a retrospective report *assigns* to an event. |
| `RETRIEVAL_TIME` | When this repository fetched the artifact. |

## Worked examples (these are tested — see `tests/test_time_semantics.py`)

**A NASA article published at 18:00 saying a satellite observed a fire earlier:**

```
18:00 = PUBLICATION_TIME
```

...and nothing else. Unless the original acquisition time is explicitly given,
**no `SENSOR_ACQUISITION_TIME` is created.** The article does not become
remote-sensing timing evidence.

**A news article published 15:40 reporting "an alert was sent at 15:30":**

```
15:30 = REPORTED_ALERT_SEND_TIME   (evidence class NEWS_REPORT)
15:40 = PUBLICATION_TIME           (evidence class NEWS_REPORT)
```

The 15:30 value remains `NEWS_REPORT` evidence until the original alert record is
obtained. Obtaining the original record adds a `PRIMARY_OPERATIONAL` node with
role `ALERT_SEND_TIME`; it does not retroactively reclassify the news node.

## Timezone

- Canonical internal representation: **UTC**, ISO 8601 with explicit offset.
- Korean sources are overwhelmingly **KST = UTC+09:00**, with no DST in the
  modern era. KST is *assumed* for Korean-language domestic sources only when
  the source is domestic and the value is a wall-clock time; the assumption is
  recorded on the record as `tz_assumed: true`.
- **NASA FIRMS `acq_date`/`acq_time` are UTC.** Converting them to KST adds 9 h
  and frequently changes the calendar date. Failing to do this is a known,
  tested failure mode (`docs/FAILURE_MODES.md` FM-02).
- Any timestamp whose timezone cannot be established is stored as
  `tz_unknown` and is **not** compared against a timestamp in another zone.

## Interval representation

Point times are the exception, not the rule. The canonical representation is a
closed/half-open interval with optionally infinite bounds:

```
[11:24, 11:25]     bounded
(-inf, 15:30]      "before 15:30"
[14:00, +inf)      "at or after 14:00"
unknown            no constraint at all
```

A source stating "11:24" at minute resolution yields `[11:24:00, 11:24:59]`,
not the point `11:24:00`. Resolution is part of the datum.

## Prohibited operations

- **Do not average conflicting times.** `11:24` and `11:25` from two sources do
  not become `11:24:30`. They remain two conflicting records, both retained,
  logged in `reports/CONTRADICTIONS.md`. The only admissible combination is an
  explicitly labelled `DERIVED` analysis with a stated justification.
- Do not narrow an interval using a source that does not constrain it.
- Do not promote a `REPORTED_ALERT_SEND_TIME` to `ALERT_SEND_TIME`.
- Do not treat `SENSOR_ACQUISITION_TIME` as `PHYSICAL_EVENT_TIME`. A satellite
  detection time is when the sensor saw something, not when fire arrived.

## Interval arithmetic

Implemented in `src/wg_alert_audit/core/intervals.py` over the extended reals.
Difference of two intervals `F - A` where `F = [f_L, f_U]`, `A = [a_L, a_U]`:

```
L = [f_L - a_U,  f_U - a_L]
```

with infinite bounds propagating. `(+inf) - (+inf)` is undefined and yields
`unknown` rather than a number.
