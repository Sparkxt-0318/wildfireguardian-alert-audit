"""GK2A AMI Level-2 Forest Fire (산불탐지, product code ``ff``) adapter.

Two access routes, deliberately kept separate:

* **NMSC public image tree** - rendered PNG twins of the operational product,
  served without any credential. These are genuine artifacts of the operational
  product run, so their *existence at a timestamp* is evidence that the fire
  detection product covered that observation slot. They are renderings, not the
  NetCDF, so they are **not** quantitative pixel data and this adapter never
  pretends otherwise (see :class:`SlotAvailability`).

* **KMA API Hub / NMSC data service** - the NetCDF with the ``FF`` and
  ``DQF_FF`` variables. Credential-gated; the adapter records that honestly and
  supports manual import of a legitimately downloaded file.

The soft-404 trap is the important operational detail: a missing object on the
NMSC tree returns **HTTP 200** with a ~1 KB ``text/html`` body, not a 404.
Keying on the status code alone would record non-existent slots as retrieved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..core.credentials import status as cred_status
from ..core.model import AccessStatus
from .http import Response, fetch

NMSC_IMG_ROOT = "https://nmsc.kma.go.kr/IMG/GK2A/AMI/L2/FF"

#: Area code -> (scene token, projection token, nominal cadence in minutes).
AREAS: dict[str, tuple[str, str, int]] = {
    "KO": ("ko", "lc", 2),    # Korean peninsula, 2 km, Lambert conformal
    "EA": ("ea", "lc", 10),   # East Asia
    "FD": ("fd", "ge", 10),   # Full disk, GEOS projection
}

#: A missing object is served as a small HTML page with HTTP 200.
SOFT_404_MAX_BYTES = 4096

#: Documented daily wheel-offload gap for the Dec-Apr period, in UTC.
KNOWN_GAP_UTC = (("00:40", "00:50"),)


def image_url(observed_utc: datetime, area: str = "KO") -> str:
    """Build the NMSC public-tree URL for one observation slot.

    The timestamp in a GK2A filename is the **observation time in UTC**, which
    is nine hours behind the Korean wall-clock times used by every domestic
    source in this audit.
    """
    if observed_utc.tzinfo is None:
        raise ValueError("observation time must be timezone-aware UTC")
    t = observed_utc.astimezone(timezone.utc)
    scene, proj, _ = AREAS[area]
    stamp = t.strftime("%Y%m%d%H%M")
    name = f"gk2a_ami_le2_ff_{scene}020{proj}_{stamp}.srv.png"
    return (
        f"{NMSC_IMG_ROOT}/{area}/{t:%Y%m}/{t:%d}/{t:%H}/{name}"
    )


@dataclass(slots=True)
class SlotAvailability:
    """Whether the operational FF product covered one observation slot.

    This is an *observation availability* record, which is one of the three
    things the research question asks about. It is deliberately NOT a fire
    detection: a rendered PNG cannot be read as pixel data without the product
    colormap, and this adapter does not attempt to.
    """

    observed_utc: datetime
    area: str
    url: str
    available: bool
    access_status: AccessStatus
    byte_length: int
    content_type: str
    sha256: str = ""
    note: str = ""

    @property
    def observed_kst(self) -> datetime:
        return self.observed_utc.astimezone(timezone(timedelta(hours=9)))


def _is_soft_404(resp: Response) -> bool:
    """NMSC serves missing objects as HTTP 200 + a small HTML page."""
    return (
        "text/html" in (resp.content_type or "").lower()
        and len(resp.body) <= SOFT_404_MAX_BYTES
    )


def probe_slot(observed_utc: datetime, area: str = "KO") -> SlotAvailability:
    """Probe one observation slot, distinguishing a real product from a soft-404."""
    url = image_url(observed_utc, area)
    resp = fetch(url, source_id=f"gk2a-ff-{area}", query_was_valid=True)

    if resp.status is AccessStatus.RETRIEVED and _is_soft_404(resp):
        # The service answered correctly; this slot simply has no product.
        # That is NO_RELEVANT_RECORD - a statement about the dataset, licensed
        # because the query was valid and the service responded.
        return SlotAvailability(
            observed_utc=observed_utc,
            area=area,
            url=url,
            available=False,
            access_status=AccessStatus.NO_RELEVANT_RECORD,
            byte_length=len(resp.body),
            content_type=resp.content_type,
            note=(
                "soft-404: HTTP 200 with a small text/html body means no product "
                "for this slot. Status-code-only logic would misread this as a "
                "successful retrieval."
            ),
        )

    if resp.ok:
        import hashlib

        return SlotAvailability(
            observed_utc=observed_utc,
            area=area,
            url=url,
            available=True,
            access_status=AccessStatus.RETRIEVED,
            byte_length=len(resp.body),
            content_type=resp.content_type,
            sha256=hashlib.sha256(resp.body).hexdigest(),
            note=(
                "operational GK2A L2 FF product rendering exists for this slot. "
                "Evidence of observation availability, NOT of a fire detection."
            ),
        )

    return SlotAvailability(
        observed_utc=observed_utc,
        area=area,
        url=url,
        available=False,
        access_status=resp.status,
        byte_length=len(resp.body),
        content_type=resp.content_type,
        note=f"not retrieved: {resp.reason}",
    )


def slots_between(
    start_utc: datetime, end_utc: datetime, area: str = "KO", *, step_minutes: int | None = None
) -> list[datetime]:
    """Nominal observation slots in a window, at the area's documented cadence."""
    step = step_minutes or AREAS[area][2]
    out, t = [], start_utc.astimezone(timezone.utc)
    while t < end_utc:
        out.append(t)
        t += timedelta(minutes=step)
    return out


def netcdf_access_note() -> dict[str, str]:
    """Describe the credential-gated route to the quantitative product."""
    return {
        "product": "GK2A AMI L2 Forest Fire (ff) NetCDF, variables FF and DQF_FF",
        "route": "KMA API Hub  https://apihub.kma.go.kr/  (GK2A LE2 FF)",
        "credential_env_var": "KMA_API_KEY (API Hub authKey) / NMSC_API_KEY",
        "credential_status": cred_status("kma").value,
        "acquisition": (
            "Register at apihub.kma.go.kr, then 활용신청 on the GK2A 기상산출물 API. "
            "Support: kmadatahub@korea.kr"
        ),
        "manual_alternative": (
            "data.kma.go.kr 기상자료개방포털 -> 원격탐사자료 -> GK2A, order via "
            "마이페이지 대용량자료신청. Or the NMSC data service at "
            "datasvc.nmsc.kma.go.kr (회원가입 -> 위성영상 자료신청)."
        ),
        "import_command": "wg-alert-audit import <file.nc> --kind gk2a",
    }
