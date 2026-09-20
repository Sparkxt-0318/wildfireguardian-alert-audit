"""Gyeongsangbuk-do administrative gazetteer, as of March 2025.

Deliberately hand-curated and dated, because Korean administrative geography
changes: **군위군 (Gunwi) left Gyeongsangbuk-do for Daegu Metropolitan City on
2023-07-01**, so a March 2025 record naming 군위 is not a Gyeongbuk record.
Encoding that here stops it being rediscovered by accident later.
"""

from __future__ import annotations

from typing import Final

PROVINCE: Final = "경상북도"
PROVINCE_ALIASES: Final = ("경북", "경상북도")

#: si/gun of Gyeongsangbuk-do. Key = canonical full name.
SI_GUN: Final[dict[str, tuple[str, ...]]] = {
    "포항시": ("포항",),
    "경주시": ("경주",),
    "김천시": ("김천",),
    "안동시": ("안동",),
    "구미시": ("구미",),
    "영주시": ("영주",),
    "영천시": ("영천",),
    "상주시": ("상주",),
    "문경시": ("문경",),
    "경산시": ("경산",),
    "의성군": ("의성",),
    "청송군": ("청송",),
    "영양군": ("영양",),
    "영덕군": ("영덕",),
    "청도군": ("청도",),
    "고령군": ("고령",),
    "성주군": ("성주",),
    "칠곡군": ("칠곡",),
    "예천군": ("예천",),
    "봉화군": ("봉화",),
    "울진군": ("울진",),
    "울릉군": ("울릉",),
}

#: Transferred out of Gyeongbuk before the target window. Recognised so that it
#: is correctly *excluded*, rather than silently matched as a Gyeongbuk county.
FORMER_SI_GUN: Final[dict[str, str]] = {
    "군위군": "transferred to 대구광역시 on 2023-07-01; not Gyeongbuk in March 2025",
}

#: eup/myeon/dong by parent si/gun, for the municipalities in scope.
EUP_MYEON: Final[dict[str, tuple[str, ...]]] = {
    "의성군": (
        "의성읍", "단촌면", "점곡면", "옥산면", "사곡면", "춘산면", "가음면",
        "금성면", "봉양면", "비안면", "구천면", "단밀면", "단북면", "안평면",
        "안사면", "신평면", "안계면", "다인면",
    ),
    "안동시": (
        "풍산읍", "와룡면", "북후면", "서후면", "풍천면", "일직면", "남후면",
        "남선면", "임하면", "길안면", "임동면", "예안면", "도산면", "녹전면",
        "중구동", "명륜동", "용상동", "태화동", "평화동", "안기동", "강남동",
        "옥동", "송하동",
    ),
    "청송군": (
        "청송읍", "주왕산면", "부남면", "현동면", "현서면", "안덕면", "파천면",
        "진보면",
    ),
    "영양군": ("영양읍", "일월면", "수비면", "청기면", "입암면", "석보면"),
    "영덕군": (
        "영덕읍", "강구면", "남정면", "달산면", "지품면", "축산면", "영해면",
        "병곡면", "창수면",
    ),
}

#: Reverse index eup/myeon -> parent. Ambiguous names map to a tuple.
_PARENTS: dict[str, list[str]] = {}
for _gun, _names in EUP_MYEON.items():
    for _n in _names:
        _PARENTS.setdefault(_n, []).append(_gun)

EUP_MYEON_PARENT: Final[dict[str, tuple[str, ...]]] = {
    k: tuple(v) for k, v in _PARENTS.items()
}

#: Suffixes that mark a token as a ROAD on their own. Unambiguous: no ordinary
#: Korean noun-plus-particle construction ends this way.
ROAD_SUFFIXES_STRONG: Final[tuple[str, ...]] = (
    "고속도로", "고속국도", "자동차전용도로", "순환도로", "우회도로",
    "국도", "지방도", "산업로", "대로",
)

#: Suffixes that mark a road only in the presence of a place name. 로 and 길 are
#: also the directional particle and a common noun ending, so "날씨로" (because
#: of the weather) and "대피하시길" (please evacuate) end this way without being
#: roads. See ``geography._classify_token`` for why that is handled by requiring
#: a place name in the stem rather than by a longer stop-list.
ROAD_SUFFIXES_WEAK: Final[tuple[str, ...]] = ("로", "길")

#: Retained for callers that want every road-ish ending.
ROAD_SUFFIXES: Final[tuple[str, ...]] = ROAD_SUFFIXES_STRONG + ROAD_SUFFIXES_WEAK

#: Suffixes marking a token as a FACILITY / structure. Also not a locality.
FACILITY_SUFFIXES: Final[tuple[str, ...]] = (
    "나들목", "분기점", "휴게소", "톨게이트", "영업소", "터널", "대교", "육교",
    "초등학교", "중학교", "고등학교", "대학교", "학교", "병원", "보건소",
    "마을회관", "회관", "경로당", "체육관", "체육센터", "복지관", "주민센터",
    "행정복지센터", "센터", "면사무소", "읍사무소", "사무소", "저수지", "댐", "발전소", "변전소", "요양원",
    "요양병원", "사찰", "공원", "역", "터미널",
)

#: Suffixes marking a NATURAL FEATURE. A mountain name does not imply a county
#: without an explicit lookup, so these are captured but never used to infer
#: administrative geography.
NATURAL_SUFFIXES: Final[tuple[str, ...]] = (
    "산", "봉", "재", "고개", "계곡", "천", "강", "저수지", "골",
)

#: Administrative level suffixes.
ADMIN_SUFFIXES: Final[tuple[str, ...]] = ("도", "시", "군", "구", "읍", "면", "동", "리")

__all__ = [
    "PROVINCE", "PROVINCE_ALIASES", "SI_GUN", "FORMER_SI_GUN", "EUP_MYEON",
    "EUP_MYEON_PARENT", "ROAD_SUFFIXES", "FACILITY_SUFFIXES",
    "NATURAL_SUFFIXES", "ADMIN_SUFFIXES",
]
