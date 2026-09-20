"""Korean emergency-alert (긴급재난문자 / CBS) adapter.

This is the highest-value target in the audit, because the original alert
record is the only ``PRIMARY_OPERATIONAL`` evidence for *first public warning*.
Everything else - a news article, an official retrospective, a Wikipedia
summary - can only report what the alert record says.

The adapter supports three routes and treats them as equals:

1. the MOIS disaster-safety data platform API (credential-gated);
2. the 공공데이터포털 open-API mirror (credential-gated);
3. **manual import** of a legitimately downloaded CSV/JSON export.

Route 3 is not a fallback. Several Korean government systems only release
historical alert data through an authenticated UI, so making automated access a
prerequisite would make the research impossible for no methodological gain.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from ..core import credentials
from ..core.intervals import TimeInterval
from ..core.model import AccessStatus

KST = timezone(timedelta(hours=9))

#: Candidate service endpoints. Recorded as candidates because which one is
#: authoritative for historical records is itself a research finding, logged in
#: reports/SOURCE_ACCESS_STATUS.md.
ENDPOINTS: dict[str, dict[str, str]] = {
    "safetydata_dssp": {
        "name": "행정안전부 긴급재난문자 (safetydata.go.kr, dataSn=228)",
        "base": "https://www.safetydata.go.kr/V2/api/DSSP-IF-00247",
        "credential": "SAFETYDATA_API_KEY",
        "param": "serviceKey",  # capital K; the platform rejects serviceKey spelled otherwise
        "portal": "https://www.safetydata.go.kr/disaster-data/view?dataSn=228",
        "register": "https://www.safetydata.go.kr/registMember_1",
        "role": "CURRENT AUTHORITATIVE record-level source",
        "verified": "2026-09-20: live call with an invalid key returns HTTP 200 and "
                    "resultCode 30 SERVICE KEY IS NOT REGISTERED ERROR",
    },
    "data_go_kr_link": {
        "name": "공공데이터포털 행정안전부_긴급재난문자 (15134001)",
        "base": "https://www.data.go.kr/data/15134001/openapi.do",
        "credential": "DATA_GO_KR_SERVICE_KEY",
        "param": "serviceKey",
        "portal": "https://www.data.go.kr/data/15134001/openapi.do",
        "register": "https://www.data.go.kr/",
        "role": "catalogue POINTER ONLY (API 유형: LINK) - resolves to safetydata_dssp",
        "verified": "2026-09-20: catalogue page retrieved; not an independent endpoint",
    },
    "safekorea_ui": {
        "name": "국민안전24 재난문자 조회 (public web UI, no credential)",
        "base": "https://www.safekorea.go.kr/safekorea-kor/ctim/cmsg/calamitySms.do",
        "credential": "",
        "param": "",
        "portal": "https://www.safekorea.go.kr/safekorea-kor/ctim/cmsg/calamitySms.do?menuSn=34&firstYn=Y",
        "register": "",
        "role": "public search UI; max one-month window",
        "verified": "2026-09-20: returns 전체 0 건 for 2025-03-21..2025-03-31. That is a "
                    "property of THIS SURFACE's retention, not of the MOIS store",
    },
    "disastermsg3_legacy": {
        "name": "행정안전부_재난문자방송 발령현황 (legacy DisasterMsg3)",
        "base": "https://apis.data.go.kr/1741000/DisasterMsg3/getDisasterMsg1List",
        "credential": "DATA_GO_KR_SERVICE_KEY",
        "param": "serviceKey",
        "portal": "https://www.data.go.kr/",
        "register": "https://www.data.go.kr/",
        "role": "SUPERSEDED - officially '조회가 제한되며 향후 폐기될 예정'",
        "verified": "2026-09-20: superseded by safetydata_dssp per the official notice",
    },
}

#: Documented result codes for the safetydata platform. 30 is the one that
#: matters most here: it proves the dataset is gated, not that it is empty.
RESULT_CODES: dict[str, str] = {
    "00": "NORMAL SERVICE",
    "01": "APPLICATION ERROR",
    "02": "TIMEOUT ERROR",
    "10": "INVALID_REQUEST_PARAMETER_ERROR",
    "11": "INDENT REQUEST PARAMETER ERROR",
    "12": "NO OPENAPI SERVICE ERROR (service absent or discarded)",
    "13": "INVALID METHOD REQUEST ERROR",
    "20": "SERVICE ACCESS DENIED ERROR",
    "22": "LIMITED NUMBER OF SERVICE REQUESTS EXCEEDS ERROR",
    "30": "SERVICE KEY IS NOT REGISTERED ERROR",
    "31": "DEADLINE HAS EXPIRED ERROR",
    "32": "UNREGISTERED IP ERROR",
    "33": "NO SERVICE KEY ERROR",
    "34": "DOZEN SERVICE KEY ERROR",
    "99": "UNKNOWN ERROR",
}

#: Request parameters of DSSP-IF-00247, from the official spec table.
#: Note there is no documented END-date parameter: crtDt is a start date, so a
#: bounded window needs paging plus client-side truncation.
REQUEST_PARAMS: dict[str, str] = {
    "serviceKey": "required; capital K",
    "numOfRows": "rows per page",
    "pageNo": "page number",
    "returnType": "json | xml",
    "crtDt": "start date, YYYYMMDD (no documented end-date parameter)",
    "rgnNm": "region name (시도명 or 시군구명), e.g. 경상북도",
}

#: Canonical field names this audit requires from any alert source.
REQUIRED_FIELDS: tuple[str, ...] = (
    "record_id",
    "send_time",
    "message_text",
    "issuing_authority",
    "target_geography",
    "source_system",
    "retrieval_provenance",
)

#: Known source-field spellings mapped onto the canonical names. Korean alert
#: APIs have used several generations of column names.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    # Names verified 2026-09-20 against the official DSSP-IF-00247 spec table
    # AND a real 100-row sample CSV are listed FIRST. The MD101_SN-era spellings
    # are retained for legacy imports but are unverified, so they rank last.
    "record_id": ("SN", "MD101_SN", "md101Sn", "record_id", "id", "일련번호"),
    "send_time": (
        "CRT_DT", "crtDt", "CREATE_DATE", "createDate", "send_time",
        "생성일시", "발송시각", "등록일시",
    ),
    "message_text": ("MSG_CN", "msgCn", "MSG", "message_text", "메시지내용", "내용"),
    "issuing_authority": (
        "SEND_PLATFORM", "sendPlatform", "issuing_authority", "송출기관", "발송기관",
    ),
    "target_geography": (
        "RCPTN_RGN_NM", "rcptnRgnNm", "RECEIVE_AREA_NM", "target_geography",
        "수신지역명",
    ),
    "target_geography_id": ("RCPTN_RGN_ID", "rcptnRgnId", "수신지역ID"),
    "emergency_step": ("EMRG_STEP_NM", "emrgStepNm", "emergency_step", "긴급단계명"),
    "disaster_type": ("DST_SE_NM", "dstSeNm", "disaster_type", "재해구분명"),
    "registered_date": ("REG_YMD", "regYmd", "등록일자"),
    "modified_date": ("MDFCN_YMD", "mdfcnYmd", "수정일자"),
}

#: Values of EMRG_STEP_NM, per the official spec. Only these three exist.
EMERGENCY_STEPS: tuple[str, ...] = ("위급재난", "긴급재난", "안전안내")

#: The DST_SE_NM value this audit filters on.
WILDFIRE_DISASTER_TYPE: str = "산불"

@dataclass(slots=True)
class AlertRecord:
    """One emergency-alert record, normalised, with the original text kept."""

    record_id: str
    send_time_raw: str
    message_text: str
    issuing_authority: str
    target_geography: str
    source_system: str
    retrieval_provenance: str
    emergency_step: str = ""
    disaster_type: str = ""
    #: Parsed send time as an interval. Resolution follows the source.
    send_interval: TimeInterval | None = field(default=None)
    tz_assumed: bool = True

    def to_json(self) -> dict:
        d = asdict(self)
        d.pop("send_interval", None)
        d["send_interval"] = (
            self.send_interval.format(KST) if self.send_interval else None
        )
        return d


def _pick(row: dict, canonical: str) -> str:
    for alias in FIELD_ALIASES.get(canonical, ()):
        for key in row:
            if key.strip().upper() == alias.strip().upper():
                v = row[key]
                return str(v).strip() if v is not None else ""
    return ""


def parse_send_time(raw: str) -> tuple[TimeInterval | None, bool]:
    """Parse a Korean alert send time. Returns ``(interval, tz_assumed)``.

    Resolution is preserved: a source giving seconds yields a point, a source
    giving minutes yields a whole-minute interval (FM-20). KST is assumed for
    these domestic systems and the assumption is returned so it can be recorded.
    """
    s = raw.strip().replace("T", " ").replace("/", "-")
    for fmt, resolution in (
        ("%Y-%m-%d %H:%M:%S", "second"),
        ("%Y-%m-%d %H:%M", "minute"),
        ("%Y%m%d%H%M%S", "second"),
        ("%Y%m%d%H%M", "minute"),
    ):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=KST)
        except ValueError:
            continue
        return (
            TimeInterval.at_second(dt) if resolution == "second"
            else TimeInterval.at_minute(dt)
        ), True
    return None, True


def normalise_rows(rows: list[dict], *, source_system: str, provenance: str) -> list[AlertRecord]:
    """Map heterogeneous source rows onto the canonical alert schema."""
    out: list[AlertRecord] = []
    for r in rows:
        raw_time = _pick(r, "send_time")
        interval, tz_assumed = parse_send_time(raw_time)
        out.append(
            AlertRecord(
                record_id=_pick(r, "record_id"),
                send_time_raw=raw_time,
                message_text=_pick(r, "message_text"),
                issuing_authority=_pick(r, "issuing_authority"),
                target_geography=_pick(r, "target_geography"),
                emergency_step=_pick(r, "emergency_step"),
                disaster_type=_pick(r, "disaster_type"),
                source_system=source_system,
                retrieval_provenance=provenance,
                send_interval=interval,
                tz_assumed=tz_assumed,
            )
        )
    return out


def load_manual_export(path: str, *, source_system: str = "manual_import") -> list[AlertRecord]:
    """Ingest a legitimately downloaded alert export (CSV or JSON).

    Imported artifacts receive exactly the same provenance treatment as
    automatically retrieved ones - same schema, same normalisation, same
    ledger. The only difference recorded is ``acquisition_method``.
    """
    with open(path, "r", encoding="utf-8-sig") as fh:
        text = fh.read()
    rows: list[dict]
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict):
            for key in ("body", "data", "items", "DisasterMsg", "response"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
            else:
                data = [data]
        rows = [r for r in data if isinstance(r, dict)]
    else:
        rows = list(csv.DictReader(io.StringIO(text)))
    return normalise_rows(
        rows, source_system=source_system, provenance=f"manual_import:{path}"
    )


def credential_report() -> list[dict[str, str]]:
    """Which alert routes are usable right now, and how to unlock the others."""
    lookup = {
        "SAFETYDATA_API_KEY": "safetydata",
        "DATA_GO_KR_SERVICE_KEY": "data_go_kr",
    }
    out = []
    for key, ep in ENDPOINTS.items():
        cred = ep["credential"]
        st = credentials.status(lookup[cred]).value if cred else "n/a (public web UI)"
        out.append(
            {
                "route": key,
                "name": ep["name"],
                "role": ep["role"],
                "credential_env_var": cred or "-",
                "credential_status": st,
                "portal": ep["portal"],
                "verified": ep["verified"],
            }
        )
    return out


def status_without_credential(route: str) -> tuple[AccessStatus, str]:
    """What to record when a route cannot be exercised for lack of a key."""
    ep = ENDPOINTS[route]
    if not ep["credential"]:
        return (
            AccessStatus.MANUAL_DOWNLOAD_AVAILABLE,
            f"{ep['name']} is an interactive web UI; a human can retrieve records "
            "there and import them with `wg-alert-audit import`",
        )
    return (
        AccessStatus.API_KEY_REQUIRED,
        f"{ep['name']} requires {ep['credential']}. The dataset exists and is "
        "gated; this is a credential gap, not data absence (FM-01). Obtain access "
        f"at {ep['portal']}",
    )
