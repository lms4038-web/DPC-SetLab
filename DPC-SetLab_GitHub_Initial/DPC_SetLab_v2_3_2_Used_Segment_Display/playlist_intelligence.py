from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class PlaylistDiagnosis:
    score: int
    grade: str
    verdict: str
    strengths: list[str]
    warnings: list[str]


def _clean(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def playlist_summary(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "track_count": 0, "total_seconds": 0.0, "avg_bpm": 0.0,
            "min_bpm": 0.0, "max_bpm": 0.0, "avg_energy": 0.0,
            "key_coverage": 0.0, "genre_coverage": 0.0,
            "camelot_counts": {}, "genre_counts": {},
        }
    bpm = pd.to_numeric(df.get("bpm", 0), errors="coerce")
    energy = pd.to_numeric(df.get("energy", 0), errors="coerce")
    durations = pd.to_numeric(df.get("duration_sec", 0), errors="coerce").fillna(0).clip(lower=0)
    camelot = _clean(df.get("camelot", pd.Series(index=df.index, dtype=str)))
    genre = _clean(df.get("genre", pd.Series(index=df.index, dtype=str)))
    valid_bpm = bpm[bpm > 0]
    valid_energy = energy[energy.between(1, 10)]
    return {
        "track_count": int(len(df)),
        "total_seconds": float(durations.sum()),
        "avg_bpm": float(valid_bpm.mean()) if not valid_bpm.empty else 0.0,
        "min_bpm": float(valid_bpm.min()) if not valid_bpm.empty else 0.0,
        "max_bpm": float(valid_bpm.max()) if not valid_bpm.empty else 0.0,
        "avg_energy": float(valid_energy.mean()) if not valid_energy.empty else 0.0,
        "key_coverage": float((camelot != "").mean()),
        "genre_coverage": float((genre != "").mean()),
        "camelot_counts": camelot[camelot != ""].value_counts().to_dict(),
        "genre_counts": genre[genre != ""].value_counts().head(10).to_dict(),
    }


def diagnose_playlist(df: pd.DataFrame, target_minutes: int = 60, overlap_seconds: int = 25) -> PlaylistDiagnosis:
    summary = playlist_summary(df)
    count = summary["track_count"]
    total = summary["total_seconds"]
    effective = max(0.0, total - max(0, count - 1) * overlap_seconds)
    target = max(1, target_minutes) * 60

    score = 0.0
    strengths: list[str] = []
    warnings: list[str] = []

    duration_ratio = effective / target
    score += min(35.0, duration_ratio * 35.0)
    if duration_ratio >= 1.45:
        strengths.append("목표 시간보다 후보 재생시간이 충분합니다.")
    elif duration_ratio >= 1.0:
        strengths.append("목표 시간을 구성할 수 있는 재생시간이 확보됐습니다.")
    else:
        shortage = max(0, target - effective)
        warnings.append(f"예상 유효 재생시간이 목표보다 약 {int(round(shortage / 60))}분 부족합니다.")

    diversity_target = max(12, int(target_minutes / 3.5))
    score += min(20.0, count / diversity_target * 20.0)
    if count >= diversity_target:
        strengths.append("순서와 대체곡을 고를 수 있는 후보 수가 충분합니다.")
    else:
        warnings.append(f"안정적인 선택 폭을 위해 후보곡을 {max(0, diversity_target-count)}곡 정도 더 권장합니다.")

    key_cov = summary["key_coverage"]
    score += key_cov * 20.0
    if key_cov >= 0.9:
        strengths.append("대부분의 곡에 Camelot 정보가 있어 화성 연결을 평가할 수 있습니다.")
    elif key_cov < 0.6:
        warnings.append("Key 정보가 부족해 화성 믹싱 추천의 신뢰도가 낮아질 수 있습니다.")

    genre_cov = summary["genre_coverage"]
    score += genre_cov * 10.0
    if genre_cov < 0.5:
        warnings.append("장르 태그가 부족해 장르 흐름 분석이 제한됩니다.")

    bpm_span = max(0.0, summary["max_bpm"] - summary["min_bpm"])
    if count and 4 <= bpm_span <= 28:
        score += 10.0
        strengths.append("BPM 범위가 세트 전개를 만들기에 적절합니다.")
    elif bpm_span > 45:
        score += 5.0
        warnings.append("BPM 범위가 넓어 장르 전환 또는 큰 템포 점프가 필요할 수 있습니다.")
    else:
        score += 7.0

    artist_counts = _clean(df.get("artist", pd.Series(index=df.index, dtype=str))).value_counts() if count else pd.Series(dtype=int)
    max_artist_share = float(artist_counts.iloc[0] / count) if count and not artist_counts.empty else 0.0
    if max_artist_share <= 0.2:
        score += 5.0
    else:
        warnings.append("특정 아티스트 비중이 높아 세트가 반복적으로 느껴질 수 있습니다.")

    final = int(round(max(0, min(100, score))))
    grade = "매우 좋음" if final >= 85 else "좋음" if final >= 70 else "보완 필요" if final >= 50 else "부족"
    verdict = (
        f"{target_minutes}분 세트 후보로 충분합니다." if duration_ratio >= 1.15 and count >= max(10, diversity_target - 3)
        else f"{target_minutes}분 세트는 가능하지만 후보 보강을 권장합니다." if duration_ratio >= 1.0
        else f"{target_minutes}분 세트를 만들기에는 현재 후보가 부족합니다."
    )
    return PlaylistDiagnosis(final, grade, verdict, strengths[:4], warnings[:4])


def playlist_options(playlists: dict[str, list[str]]) -> list[str]:
    return ["전체 Collection"] + sorted(playlists, key=lambda p: (p.count(" / "), p.lower()))


def display_playlist_path(path: str) -> str:
    if path == "전체 Collection":
        return "🎵 전체 Collection"
    parts = [p.strip() for p in path.split(" / ") if p.strip()]
    return "   " * max(0, len(parts) - 1) + ("📂 " if len(parts) > 1 else "🎧 ") + parts[-1]
