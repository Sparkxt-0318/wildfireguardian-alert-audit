"""Credential access and redaction.

Rules (docs/DECISIONS.md D-002, D-003):

* Values come from the environment only. Never a tracked file, never a literal.
* A value is never printed, logged, written to ``data/``, written to a report,
  or committed. Every URL that leaves this process passes through :func:`redact`.
* Only *metadata* is recorded: ``AVAILABLE`` or ``ABSENT``.

The primary variable names deliberately match those already in use in the main
WildfireGuardian repository so that an existing ``.env`` works here unchanged.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final


class CredentialStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    ABSENT = "ABSENT"


@dataclass(frozen=True, slots=True)
class CredentialSpec:
    """A credential this audit knows how to use, and how to obtain it."""

    key: str
    #: Environment variable names, in priority order. First non-empty wins.
    env_names: tuple[str, ...]
    service: str
    #: Official page where a human obtains this credential.
    acquisition_url: str
    notes: str = ""


#: Every credential the audit can use. Primary names reuse the main repo's.
SPECS: Final[tuple[CredentialSpec, ...]] = (
    CredentialSpec(
        key="firms",
        env_names=("FIRMS_MAP_KEY", "NASA_FIRMS_MAP_KEY"),
        service="NASA FIRMS active-fire API (VIIRS / MODIS)",
        acquisition_url="https://firms.modaps.eosdis.nasa.gov/api/map_key/",
        notes=(
            "Primary name matches main repo src/wildfireguardian/live/firms.py; "
            "NASA_FIRMS_MAP_KEY is the alias that repo also honours."
        ),
    ),
    CredentialSpec(
        key="safetydata",
        env_names=("SAFETYDATA_API_KEY",),
        service="MOIS disaster-safety data sharing platform (긴급재난문자)",
        acquisition_url="https://www.safetydata.go.kr/",
        notes="New name; the main repository configures nothing for this service.",
    ),
    CredentialSpec(
        key="data_go_kr",
        env_names=("DATA_GO_KR_SERVICE_KEY",),
        service="공공데이터포털 data.go.kr open API service key",
        acquisition_url="https://www.data.go.kr/",
    ),
    CredentialSpec(
        key="kma",
        env_names=("KMA_API_KEY", "WILDFIREGUARDIAN_KMA_API_KEY"),
        service="Korea Meteorological Administration API",
        acquisition_url="https://apihub.kma.go.kr/",
        notes="Primary name matches the main repository's .env.example.",
    ),
    CredentialSpec(
        key="nmsc",
        env_names=("NMSC_API_KEY",),
        service="National Meteorological Satellite Center (GK2A products)",
        acquisition_url="https://nmsc.kma.go.kr/",
        notes="New name; the main repository configures nothing for this service.",
    ),
    CredentialSpec(
        key="earthdata",
        env_names=("EARTHDATA_TOKEN", "EARTHDATA_BEARER_TOKEN"),
        service="NASA Earthdata Login (archival downloads)",
        acquisition_url="https://urs.earthdata.nasa.gov/",
    ),
)

_BY_KEY: Final[dict[str, CredentialSpec]] = {s.key: s for s in SPECS}


def get(key: str) -> str | None:
    """Return the credential value, or ``None``. Callers must not log it."""
    spec = _BY_KEY[key]
    for name in spec.env_names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def status(key: str) -> CredentialStatus:
    """Metadata only. This is the *only* thing that may be recorded."""
    return CredentialStatus.AVAILABLE if get(key) else CredentialStatus.ABSENT


def status_table() -> list[dict[str, str]]:
    """Report-safe credential inventory. Contains no values, by construction."""
    return [
        {
            "service": s.service,
            "env_var": s.env_names[0],
            "aliases": ", ".join(s.env_names[1:]) or "-",
            "credential_status": status(s.key).value,
            "acquisition_url": s.acquisition_url,
        }
        for s in SPECS
    ]


def _live_values() -> list[str]:
    vals = []
    for spec in SPECS:
        v = get(spec.key)
        if v and len(v) >= 8:
            vals.append(v)
    return vals


_PARAM_RE: Final = re.compile(
    r"((?:MAP_KEY|map_key|serviceKey|service_key|authKey|auth_key|apikey|api_key|key|token)=)"
    r"([^&\s\"'<>]+)",
    re.I,
)


def redact(text: str) -> str:
    """Strip credential values from any string before it is emitted.

    Two passes, because either alone is insufficient:

    1. Replace any *live* credential value found verbatim. Catches a key that
       reached the string by a route this module does not know about.
    2. Blank the value of any credential-shaped query parameter. Catches keys
       that are not ours (a pasted URL, a key from a config we never read).

    Mirrors the main repository's ``url.replace(key, "<MAP_KEY>")`` pattern,
    widened so that it cannot be defeated by a differently-named parameter.
    """
    out = text
    for value in _live_values():
        out = out.replace(value, "<REDACTED>")
    return _PARAM_RE.sub(r"\1<REDACTED>", out)
