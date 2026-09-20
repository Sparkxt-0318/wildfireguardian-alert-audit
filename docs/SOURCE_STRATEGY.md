# Source strategy

Status: normative.

## Priority order

1. `PRIMARY_OPERATIONAL` — original alert records, dispatch records, operational bulletins.
2. `REMOTE_SENSING` — VIIRS/MODIS active fire, GK2A AMI L2 products.
3. `OFFICIAL_RETROSPECTIVE` — KFS / NIFoS / MOIS / KMA / NFA / BAI / National Assembly.
4. `NEWS_REPORT` — Yonhap, KBS, MBC, SBS, major newspapers, local government releases.
5. `TERTIARY` — **discovery aid only**, never a terminal source.

## Highest-priority target: Korean emergency alerts

The official historical emergency-alert record (긴급재난문자 / CBS) is the single
most valuable artifact for this audit, because it is the only `PRIMARY_OPERATIONAL`
evidence for `first public warning`.

Investigation does **not stop** at a stale SafeKorea URL. The search covers:
service migration notices; replacement APIs; current data-sharing portals
(공공데이터포털 `data.go.kr`, 재난안전데이터공유플랫폼 `safetydata.go.kr`,
국민재난안전포털 `safekorea.go.kr`); bulk downloads; CSV exports; API application
procedures; historical search interfaces; official documentation.

Required alert fields where available:

```
record_id  send_time  message_text  issuing_authority
target_geography  source_system  retrieval_provenance
```

Manual import of legitimately downloaded alert data is a first-class path
(`docs/` §manual import, `wg-alert-audit import`). Automated web access is **not**
a prerequisite for the research.

## Citation-chain crawling

Tertiary sources are discovery aids. The crawl walks:

```
Wikipedia -> Yonhap citation -> official quoted source -> primary record if obtainable
```

Cited Korean sources are followed systematically. Stopping after retrieving
Wikipedia, when it links to a stronger source, is a protocol violation.

## Escalation ladder (required before classifying any gap)

When an official source fails:

1. search for migration;
2. search the agency's current data platform;
3. search API documentation;
4. search downloadable archives;
5. search official alternate domains;
6. search documentation describing access;
7. implement manual import if authentication blocks automation;
8. record the actual access status.

Only then classify the gap. Stopping after the first failed endpoint is a
protocol violation.

## Credentials

Credentials are supplied **only** through environment variables, reusing the
names already established in the main WildfireGuardian repository where they
exist. See `docs/DECISIONS.md` D-002. No credential value is ever printed,
logged, committed, placed in a report, or embedded in a fixture. URLs carrying
keys are redacted before any output.
