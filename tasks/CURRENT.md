# Current

**All phases complete.** Protocol written before any data was touched; engine,
adapters and CLI implemented; four source-discovery tracks run; corpus built;
two independent verification rounds and one adversarial audit completed and
acted on.

## Final state

| | |
|---|---|
| Emergency alert records harvested | 1,688 (264 about this fire) |
| Claims in the timeline | 296, six quantities, five complex counties |
| Formal 대피명령 / evacuation directives | 152 / 208 |
| GK2A L2 FF observation slots | 635 retrieved of 650 probed, all byte-unique |
| Tests | **253**, including integration against the committed corpus |
| Named failure modes | **32** (12 discovered by review, not design) |
| Manual verification discrepancy rate | 34.0 %, 95 % CI [22.4 %, 47.8 %] |

## Open items, stated rather than closed

- **리-level geography** is modelled in `Geography` but not carried in the
  timeline schema (round-2 NEW-5).
- **Duplicate and superseding alert linkage** — `EdgeType.SUPERSEDES` exists
  but is unused for alert pairs, so 「(정정)」 corrections are counted as
  separate records (round-2 NEW-7).
- **진화율 → containment** is covered by unit test but has never appeared in a
  verification sample, so the guard is unexercised by sampling.
- **A third verification round** would very likely find a further ~30 % in
  classes not yet named. That is how this method behaves; it is not a sign the
  corpus is unusable, but the rate must not be read as a quality certificate.
- **No PR is open.** The target repository was empty, so this branch became the
  default branch and there is no base to merge into. Raised with the user
  rather than fabricating a base branch.
