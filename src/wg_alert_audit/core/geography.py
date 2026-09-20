"""Token- and context-aware Korean administrative geography extraction.

The naive approach - substring search for county names - is wrong in a way that
is easy to miss and hard to detect downstream. The canonical case:

    서산영덕고속도로   "Seosan-Yeongdeok Expressway"

contains 영덕, and a substring matcher will happily place the event in 영덕군
(Yeongdeok County) even when the sentence is about somewhere else entirely.
Expressways in Korea are conventionally named for their two endpoints, so the
string is evidence of a *road*, not of a location.

The second failure this module guards is first-location capture: when a
sentence names several places, a naive extractor attaches every timestamp to
the first one. Here, extraction is per *clause*, and where a clause boundary is
ambiguous the result is UNRESOLVED rather than a guess.

See docs/EXCLUSION_RULES.md X-3/X-4, FM-05/FM-06.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import gazetteer as gz
from .model import Geography, GeoRelation

#: Clause separators. Korean connective endings are included because a single
#: orthographic sentence routinely carries several independent predications.
_CLAUSE_SPLIT = re.compile(
    r"(?:[.!?;\n]|,\s|(?<=[가-힣])(?:하고|하며|이며|으로|에서)\s|"
    r"(?<=[가-힣])(?:고|며|다가|지만|으나|나서)\s(?=[가-힣])|"
    r"\s(?:그리고|이후|이어|한편|또한|반면|다만)\s)"
)

_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")


@dataclass(slots=True)
class SpanMatch:
    """One geographic mention, with why it was accepted or rejected."""

    text: str
    start: int
    end: int
    kind: str  # province | si_gun | eup_myeon | ri | road | facility | natural
    canonical: str | None = None
    parent: str | None = None
    accepted: bool = True
    reason: str = ""


@dataclass(slots=True)
class ClauseResult:
    """Extraction for one clause.

    ``geography`` carries the finest single reading, for callers that need one.
    ``all_si_gun`` / ``all_eup_myeon`` carry **every** locality named in the
    clause. Exposing only the first was a real recall defect: a cross-county
    road-closure alert naming both 안동시 and 청송군 silently lost the second,
    which is exactly the kind of record a multi-county timeline depends on.
    """

    clause: str
    geography: Geography
    matches: list[SpanMatch] = field(default_factory=list)
    resolved: bool = True
    note: str = ""
    #: Every si/gun named in this clause, in order of appearance.
    all_si_gun: list[str] = field(default_factory=list)
    #: Every eup/myeon/dong named in this clause, in order of appearance.
    all_eup_myeon: list[str] = field(default_factory=list)
    #: Every road/facility token seen, whether or not it embedded a place name.
    all_non_localities: list[str] = field(default_factory=list)


#: Case particles that are never part of a road name, so a token ending in one
#: may be stripped and looked up bare. 에서/에 etc. attach to any noun.
_PLAIN_PARTICLES: tuple[str, ...] = (
    "에서는", "에서도", "에서", "에는", "에도", "에게", "까지", "부터", "으로는",
    "이라는", "라는", "과의", "와의", "의", "은", "는", "이", "가", "을", "를",
    "과", "와", "에", "도", "만",
)

#: Particles that collide with road suffixes. Stripping one of these is only
#: allowed when what remains carries an explicit administrative suffix, so that
#: 안동시로 ("to Andong City") resolves as a place but 영덕로 stays a road.
_ROADLIKE_PARTICLES: tuple[str, ...] = ("으로", "로")


#: Administrative suffixes unambiguous enough to license particle stripping.
#: 도 is excluded on purpose: 고속도로 ends in 도 + 로 without being a province.
_STRONG_ADMIN_SUFFIXES: tuple[str, ...] = ("시", "군", "구", "읍", "면", "동", "리")


#: Hazard nouns that attach directly to a place name in Korean headlines and
#: alerts: 의성산불 ("the Uiseong wildfire"), 안동화재. Splitting these is safe
#: in a way that general substring matching is not, because the prefix must be
#: an EXACT gazetteer name. 서산영덕고속도로 does not end in a hazard noun, so
#: the X-3 guard is untouched.
_HAZARD_NOUNS: tuple[str, ...] = ("산불", "화재", "지진", "산사태", "홍수", "폭우")


def _split_hazard_compound(tok: str) -> str | None:
    """``의성산불`` -> ``의성``. Returns ``None`` when no safe split applies."""
    for noun in _HAZARD_NOUNS:
        if tok.endswith(noun) and len(tok) > len(noun):
            stem = tok[: -len(noun)]
            if _is_direct_hit(stem):
                return stem
    return None


def _is_direct_hit(tok: str) -> bool:
    """Is this token already a gazetteer name, needing no stripping?"""
    return (
        tok in gz.EUP_MYEON_PARENT
        or tok in gz.PROVINCE_ALIASES
        or tok == gz.PROVINCE
        or _match_si_gun(tok) is not None
    )


def _base_form(tok: str) -> str:
    """Strip trailing case particles to reach the token's base form.

    Applied before both gazetteer lookup and compound classification, so that
    ``영덕로에서`` reduces to ``영덕로`` and is then correctly seen as a road.

    Two particle sets, treated differently:

    * Plain particles (에서, 에, 은/는/이/가 ...) never form part of a place or
      road name, so they are always shed.
    * 로/으로 are simultaneously the directional particle and the commonest
      road suffix. They are shed only when what remains carries an explicit
      administrative suffix, which is what separates 안동시로 ("to Andong
      City", a place) from 영덕로 ("Yeongdeok-ro", a road).

    A token that is already a gazetteer name is returned untouched, so that
    경상북도 is not mistaken for 경상북 + the particle 도.
    """
    if _is_direct_hit(tok):
        return tok

    base = tok
    for part in sorted(_PLAIN_PARTICLES, key=len, reverse=True):
        if base.endswith(part) and len(base) > len(part) + 1:
            candidate = base[: -len(part)]
            if _is_direct_hit(candidate) or not _is_direct_hit(base):
                base = candidate
            break

    if _is_direct_hit(base):
        return base

    hazard = _split_hazard_compound(base)
    if hazard:
        return hazard

    for part in sorted(_ROADLIKE_PARTICLES, key=len, reverse=True):
        if base.endswith(part) and len(base) > len(part):
            stem = base[: -len(part)]
            # Both conditions are needed. Requiring a gazetteer hit alone would
            # turn 영덕로 into 영덕 (a real county alias); requiring a suffix
            # alone would turn 서산영덕고속도로 into 서산영덕고속도, because
            # 고속도 happens to end in the 도 of 경상북도.
            if _is_direct_hit(stem) and stem.endswith(_STRONG_ADMIN_SUFFIXES):
                return stem
            break  # 영덕로: leave it for the road rules
    return base


def _contains_place_name(stem: str) -> bool:
    """Does this stem embed a gazetteer place name that could leak (X-3)?"""
    for canonical, aliases in gz.SI_GUN.items():
        if canonical in stem or any(a in stem for a in aliases):
            return True
    return any(name in stem for name in gz.EUP_MYEON_PARENT)


#: 부로 ("as of"), 으로/로 after a time expression - never a road name.
_TIME_TAIL = re.compile(r"(\d+\s*(시|분|일|월|년)|부)로$")


def _classify_token(tok: str) -> tuple[str, str] | None:
    """Return ``(kind, reason)`` if ``tok`` is a non-locality compound.

    Checked longest-suffix-first so that 고속도로 wins over its own 로 tail.

    Two constructions are screened out before the road rules, because both end
    in 로 without naming a road: a time expression plus 부로 ("as of 14:00"),
    and a facility plus the directional 로 ("to the sports centre"). Both are
    already excluded from locality inference, so this only keeps the recorded
    ``road`` field honest - but a road field full of timestamps would make the
    manual verification pass unreadable.
    """
    if _TIME_TAIL.search(tok):
        return ("other", "time expression with the particle 로, not a road")

    for suf in sorted(gz.FACILITY_SUFFIXES, key=len, reverse=True):
        for particle in ("으로", "로", ""):
            if tok.endswith(suf + particle) and len(tok) > len(suf) + len(particle) - 1:
                return ("facility", f"facility suffix {suf!r}")

    for suf in sorted(gz.ROAD_SUFFIXES_STRONG, key=len, reverse=True):
        if tok.endswith(suf) and len(tok) > len(suf):
            return ("road", f"token ends in unambiguous road suffix {suf!r}")

    # 로 and 길 only indicate a road when a place name is embedded - which is
    # precisely the case X-3 exists to catch. A token like 날씨로 carries no
    # place name and so cannot leak one, whatever it is.
    for suf in sorted(gz.ROAD_SUFFIXES_WEAK, key=len, reverse=True):
        if tok.endswith(suf) and len(tok) > len(suf) + 1:
            stem = tok[: -len(suf)]
            if _contains_place_name(stem):
                return (
                    "road",
                    f"road suffix {suf!r} on a stem containing a place name "
                    f"- excluded from locality inference (X-3)",
                )
            return ("other", f"ends in {suf!r} but embeds no place name")
    for suf in sorted(gz.FACILITY_SUFFIXES, key=len, reverse=True):
        if tok.endswith(suf) and len(tok) > len(suf):
            return ("facility", f"token ends in facility suffix {suf!r}")
    for suf in sorted(gz.NATURAL_SUFFIXES, key=len, reverse=True):
        if tok.endswith(suf) and len(tok) > len(suf):
            return ("natural", f"token ends in natural-feature suffix {suf!r}")
    return None


def extract_from_clause(clause: str) -> ClauseResult:
    """Extract administrative geography from a single clause.

    Tokens are classified before any gazetteer lookup, so a road or facility
    name is removed from consideration *as a whole token* and can never
    contribute its embedded county name.
    """
    matches: list[SpanMatch] = []
    province = si_gun = eup_myeon = ri = None
    road = facility = named_place = None
    notes: list[str] = []
    all_si_gun: list[str] = []
    all_eup_myeon: list[str] = []
    all_non_localities: list[str] = []

    for m in _TOKEN.finditer(clause):
        tok, s, e = m.group(0), m.start(), m.end()

        # 0. Reduce to a base form by shedding case particles, so that both
        #    안동시로 (place + 로) and 영덕로에서 (road + 에서) are classified on
        #    what they actually are rather than on their inflected surface.
        tok = _base_form(tok)

        # 1. Non-locality compounds are consumed whole and never mined for
        #    embedded place names. This is the 서산영덕고속도로 guard.
        compound = _classify_token(tok)
        if compound:
            kind, reason = compound
            matches.append(
                SpanMatch(tok, s, e, kind, accepted=False,
                          reason=f"not a locality: {reason}")
            )
            if kind == "other":
                continue
            if kind in ("road", "facility") and tok not in all_non_localities:
                all_non_localities.append(tok)
            if kind == "road" and road is None:
                road = tok
            elif kind == "facility" and facility is None:
                facility = tok
            elif kind == "natural" and named_place is None:
                # Captured, but deliberately NOT used to infer a county.
                named_place = tok
                notes.append(
                    f"{tok!r} is a natural feature; no county inferred from it"
                )
            continue

        # 2. Province.
        if tok in gz.PROVINCE_ALIASES or tok.startswith(gz.PROVINCE_ALIASES):
            if any(tok == a or tok == a + "도" for a in ("경북", "경상북")) or tok == gz.PROVINCE:
                province = gz.PROVINCE
                matches.append(SpanMatch(tok, s, e, "province", gz.PROVINCE,
                                         reason="province name"))
                continue

        # 3. si/gun - full form first, then bare form.
        hit = _match_si_gun(tok)
        if hit:
            canonical, how = hit
            if canonical in gz.FORMER_SI_GUN:
                matches.append(
                    SpanMatch(tok, s, e, "si_gun", canonical, accepted=False,
                              reason=f"excluded: {gz.FORMER_SI_GUN[canonical]}")
                )
                notes.append(f"{canonical} is outside Gyeongbuk in the target window")
                continue
            si_gun = si_gun or canonical
            if canonical not in all_si_gun:
                all_si_gun.append(canonical)
            matches.append(SpanMatch(tok, s, e, "si_gun", canonical, reason=how))
            continue

        # 4. eup/myeon/dong.
        if tok in gz.EUP_MYEON_PARENT:
            parents = gz.EUP_MYEON_PARENT[tok]
            eup_myeon = eup_myeon or tok
            if tok not in all_eup_myeon:
                all_eup_myeon.append(tok)
            parent = parents[0] if len(parents) == 1 else None
            if parent:
                if si_gun is None:
                    si_gun = parent
                if parent not in all_si_gun:
                    all_si_gun.append(parent)
            matches.append(
                SpanMatch(tok, s, e, "eup_myeon", tok, parent,
                          reason="gazetteer eup/myeon"
                          + ("" if parent else f"; ambiguous parent {parents}"))
            )
            continue

        # 5. ri - only with an explicit 리 suffix, and only alongside a
        #    higher level, since 리 names are not unique nationally.
        if tok.endswith("리") and len(tok) >= 3 and (eup_myeon or si_gun):
            ri = ri or tok
            matches.append(SpanMatch(tok, s, e, "ri", tok, reason="리-suffixed token"))

    geo = Geography(
        province=province or (gz.PROVINCE if si_gun in gz.SI_GUN else None),
        si_gun=si_gun,
        eup_myeon_dong=eup_myeon,
        ri=ri,
        named_place=named_place,
        road=road,
        facility=facility,
        raw=clause.strip(),
    )
    return ClauseResult(
        clause.strip(),
        geo,
        matches,
        resolved=True,
        note="; ".join(notes),
        all_si_gun=all_si_gun,
        all_eup_myeon=all_eup_myeon,
        all_non_localities=all_non_localities,
    )


def _match_si_gun(tok: str) -> tuple[str, str] | None:
    """Match a si/gun name, full or bare. Exact token equality only."""
    for canonical in list(gz.SI_GUN) + list(gz.FORMER_SI_GUN):
        if tok == canonical:
            return (canonical, "exact si/gun name")
    for canonical, aliases in list(gz.SI_GUN.items()) + [
        (k, (k[:-1],)) for k in gz.FORMER_SI_GUN
    ]:
        if tok in aliases:
            return (canonical, "bare si/gun name (no admin suffix)")
    return None


def extract(text: str) -> list[ClauseResult]:
    """Split into clauses and extract per clause.

    Returns one result per clause. Callers attach a timestamp to the clause it
    occurred in - never to the first clause's location (X-4).
    """
    parts = [p for p in _CLAUSE_SPLIT.split(text) if p and p.strip()]
    if not parts:
        parts = [text]
    return [extract_from_clause(p) for p in parts]


def attribute(text: str) -> Geography | None:
    """Single best geography for a whole text, or ``None`` if ambiguous.

    Refuses when clauses disagree about the county (X-4): a disagreement means
    the text describes more than one place, and silently choosing one of them
    is exactly the error this module exists to prevent.
    """
    results = extract(text)
    counties = {r.geography.si_gun for r in results if r.geography.si_gun}
    if len(counties) > 1:
        return None
    if not counties:
        return None
    county = counties.pop()
    finest = max(
        (r.geography for r in results if r.geography.si_gun == county),
        key=lambda g: (bool(g.ri), bool(g.eup_myeon_dong)),
    )
    return finest


def relate(a: Geography, b: Geography) -> GeoRelation:
    """Relation between two geographies, for lead-time pairing.

    Deliberately conservative: SAME_COUNTY is returned honestly but is gated
    out of lead-time computation by ``GeoRelation.sufficient_for_lead_time``
    (D-006), because a county-wide alert does not locate a fire front.
    """
    if a.si_gun and b.si_gun and a.si_gun != b.si_gun:
        return GeoRelation.INCOMPATIBLE
    if not a.si_gun or not b.si_gun:
        return GeoRelation.UNKNOWN
    if a.ri and b.ri:
        return (
            GeoRelation.EXACT_LOCALITY if a.ri == b.ri else GeoRelation.SAME_COUNTY
        )
    if a.eup_myeon_dong and b.eup_myeon_dong:
        return (
            GeoRelation.SAME_EUP_MYEON
            if a.eup_myeon_dong == b.eup_myeon_dong
            else GeoRelation.SAME_COUNTY
        )
    return GeoRelation.SAME_COUNTY
