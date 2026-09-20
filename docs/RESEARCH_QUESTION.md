# Research question

Status: normative. Written before any inspection of prior work on this repository.

## Primary question

> What can publicly or legitimately accessible evidence establish about the timing
> of wildfire progression, official emergency alerts, and observation availability
> during the March 2025 Gyeongbuk wildfires?

## Secondary question

> Can we defensibly estimate warning lead-time intervals for any affected locality
> without inventing minute-scale fire-arrival truth?

## What this project is

A **historical evidence audit**. Its output is a provenance-preserving record of
what evidence exists, what it says, how strong it is, and what remains unobserved.

## What this project is NOT

- Not a wildfire simulator.
- Not an evacuation counterfactual model.
- Not permitted to infer "lives saved" or any casualty counterfactual.
- Not a scoring exercise on the emergency response.

An empty or negative result is a legitimate and publishable outcome of this audit.
The project is optimised for *the strongest result the evidence actually supports*,
not for producing a positive result.

## Question hierarchy

Answered strictly in order. Q4 is not attempted before Q1-Q3 are settled.

| # | Question |
|---|---|
| Q1 | What relevant evidence actually exists and is accessible? |
| Q2 | What timestamps and locations can be established directly? |
| Q3 | What event times can only be bounded? |
| Q4 | For which localities can alert-vs-observation lead intervals be calculated? |
| Q5 | Which quantities remain genuinely unobserved? |

Jumping directly to Q4 is a protocol violation. Any lead-time number produced
without a completed Q1-Q3 chain is void.

## Scope of the event

Initial target: the **March 2025 Gyeongbuk wildfire complex and major associated
fires**. Potentially relevant municipalities include Uiseong (의성), Andong (안동),
Cheongsong (청송), Yeongyang (영양), Yeongdeok (영덕), and other directly affected
municipalities *where supported by evidence*.

It is **not assumed** that all reports refer to the same ignition, the same fire
complex, or the same local incident. Explicit incident/event IDs are maintained
(`docs/EVIDENCE_MODEL.md`), and records are only merged onto a shared incident
when evidence supports the merge.

## Core epistemic rule

The following are **distinct states** and must never be collapsed into one another:

```
DATA DOES NOT EXIST
DATA EXISTS BUT REQUIRES CREDENTIALS
ENDPOINT MIGRATED
AUTOMATED ACCESS FAILED
NETWORK FAILURE
TEMPORARY SERVICE FAILURE
DATA EXISTS BUT WAS NOT RETRIEVED
DATA EXISTS ONLY THROUGH MANUAL DOWNLOAD
DATA EXISTS BUT GEOGRAPHY/TIME IS INSUFFICIENT
```

A failed HTTP request is **not** evidence of data absence. Every acquisition
attempt classifies its outcome (`docs/ACCESS_STATUS_MODEL.md`).
