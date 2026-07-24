from __future__ import annotations

import io
import json
import math
import random
import re
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

STANDARD_COLUMNS = [
    "track_id", "title", "artist", "album", "bpm", "key", "camelot",
    "duration_sec", "rating", "energy", "genre", "comments", "play_count",
    "location", "spotify_uri", "cue_points", "use", "role"
]

ROLE_NORMAL = "일반"
ROLE_MUST = "필수"
ROLE_START = "시작"
ROLE_END = "마지막"
ROLE_OPTIONS = [ROLE_NORMAL, ROLE_MUST, ROLE_START, ROLE_END]

# Camelot wheel mapping.
CAMELOT_TO_KEY = {
    "1A": "G#/Ab minor", "1B": "B major",
    "2A": "D#/Eb minor", "2B": "F#/Gb major",
    "3A": "A#/Bb minor", "3B": "C#/Db major",
    "4A": "F minor", "4B": "G#/Ab major",
    "5A": "C minor", "5B": "D#/Eb major",
    "6A": "G minor", "6B": "A#/Bb major",
    "7A": "D minor", "7B": "F major",
    "8A": "A minor", "8B": "C major",
    "9A": "E minor", "9B": "G major",
    "10A": "B minor", "10B": "D major",
    "11A": "F#/Gb minor", "11B": "A major",
    "12A": "C#/Db minor", "12B": "E major",
}

KEY_TO_CAMELOT: dict[str, str] = {}


def _key_variants(root: str, minor: bool) -> list[str]:
    roots = {
        "C#": ["c#", "db"], "D#": ["d#", "eb"], "F#": ["f#", "gb"],
        "G#": ["g#", "ab"], "A#": ["a#", "bb"],
    }.get(root, [root.lower()])
    suffixes = ["m", "min", "minor", "-"] if minor else ["", "maj", "major", "+"]
    out = []
    for r in roots:
        for suffix in suffixes:
            out.extend([f"{r}{suffix}", f"{r} {suffix}".strip()])
    return out


for camelot, label in CAMELOT_TO_KEY.items():
    minor = camelot.endswith("A")
    root = label.split("/")[0].split()[0]
    for variant in _key_variants(root, minor):
        KEY_TO_CAMELOT[variant] = camelot
    if "/" in label:
        alt_root = label.split("/")[1].split()[0]
        for variant in _key_variants(alt_root, minor):
            KEY_TO_CAMELOT[variant] = camelot


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def normalize_key_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("♯", "#").replace("♭", "b")
    text = text.replace("sharp", "#").replace("flat", "b")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def to_camelot(value: Any) -> str:
    text = normalize_key_text(value)
    if not text:
        return ""
    compact = re.sub(r"\s+", "", text).upper()
    if re.fullmatch(r"(?:[1-9]|1[0-2])[AB]", compact):
        return compact
    # Open Key notation: 1m..12m, 1d..12d. Convert to Camelot by +7 steps.
    m = re.fullmatch(r"([1-9]|1[0-2])([MD])", compact)
    if m:
        n = ((int(m.group(1)) + 6) % 12) + 1
        return f"{n}{'A' if m.group(2) == 'M' else 'B'}"
    return KEY_TO_CAMELOT.get(text, KEY_TO_CAMELOT.get(text.replace(" ", ""), ""))


def parse_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = clean_text(value).replace(",", "")
    if not text:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else default


def parse_duration(value: Any, default: float = 240.0) -> float:
    if value is None or clean_text(value) == "":
        return default
    if isinstance(value, (int, float)) and not pd.isna(value):
        number = float(value)
        # Excel-style day fraction or raw seconds.
        return number * 86400 if 0 < number < 1 else number
    text = clean_text(value)
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    parts = text.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return default
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return default


def rating_to_five(value: Any) -> float:
    rating = parse_number(value, 0.0)
    if rating > 5:
        rating = rating / 51.0 if rating <= 255 else rating / 20.0
    return max(0.0, min(5.0, rating))


def _percentile_norm(series: pd.Series, default: float = 0.5) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty or valid.nunique() <= 1:
        return pd.Series([default] * len(series), index=series.index, dtype=float)
    low, high = valid.quantile(0.05), valid.quantile(0.95)
    if high <= low:
        low, high = valid.min(), valid.max()
    return ((numeric.fillna(valid.median()) - low) / max(high - low, 1e-9)).clip(0, 1)


def infer_energy(df: pd.DataFrame) -> pd.Series:
    bpm_component = _percentile_norm(df.get("bpm", pd.Series(index=df.index, dtype=float)), 0.5)
    rating_component = pd.to_numeric(df.get("rating", 0), errors="coerce").fillna(0).clip(0, 5) / 5
    play_component = _percentile_norm(
        pd.to_numeric(df.get("play_count", 0), errors="coerce").fillna(0).map(lambda x: math.log1p(max(x, 0))),
        0.3,
    )
    comments = (df.get("comments", "").fillna("").astype(str) + " " + df.get("genre", "").fillna("").astype(str)).str.lower()
    high_words = r"peak|banger|anthem|hard|club|festival|피크|강함|터짐|폭발|메인"
    low_words = r"warm|intro|chill|opening|downtempo|웜업|잔잔|오프닝|마무리"
    keyword = pd.Series(0.5, index=df.index, dtype=float)
    keyword = keyword.mask(comments.str.contains(high_words, regex=True), 1.0)
    keyword = keyword.mask(comments.str.contains(low_words, regex=True), 0.1)
    energy = 1 + 9 * (0.48 * bpm_component + 0.30 * rating_component + 0.14 * play_component + 0.08 * keyword)
    return energy.round(1).clip(1, 10)


def _empty_standard_df() -> pd.DataFrame:
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def finalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in STANDARD_COLUMNS:
        if col not in out:
            if col == "use":
                out[col] = True
            elif col == "role":
                out[col] = ROLE_NORMAL
            else:
                out[col] = ""
    out["track_id"] = out["track_id"].astype(str)
    out["title"] = out["title"].map(clean_text)
    out["artist"] = out["artist"].map(clean_text)
    out["album"] = out["album"].map(clean_text)
    out["cue_points"] = out["cue_points"].map(lambda x: x if isinstance(x, list) else clean_text(x))
    out["bpm"] = out["bpm"].map(lambda x: parse_number(x, 0.0)).round(2)
    out["key"] = out["key"].map(clean_text)
    out["camelot"] = out.apply(lambda row: clean_text(row.get("camelot")) or to_camelot(row.get("key")), axis=1)
    out["duration_sec"] = out["duration_sec"].map(parse_duration).round(1)
    out["rating"] = out["rating"].map(rating_to_five).round(1)
    out["play_count"] = out["play_count"].map(lambda x: int(parse_number(x, 0)))
    out["use"] = out["use"].map(lambda x: bool(x) if not isinstance(x, str) else x.strip().lower() not in {"false", "0", "no", "아니오", "n"})
    out["role"] = out["role"].map(lambda x: x if x in ROLE_OPTIONS else ROLE_NORMAL)
    supplied_energy = pd.to_numeric(out["energy"], errors="coerce")
    inferred = infer_energy(out)
    out["energy"] = supplied_energy.where(supplied_energy.between(1, 10), inferred).round(1)
    # Remove blank rows and exact duplicates while preserving first occurrence.
    out = out[(out["title"] != "") | (out["artist"] != "")]
    out = out.drop_duplicates(subset=["title", "artist", "location"], keep="first").reset_index(drop=True)
    return out[STANDARD_COLUMNS]


def parse_rekordbox_xml(data: bytes) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    root = ET.fromstring(data)
    rows: list[dict[str, Any]] = []
    for track in root.findall(".//COLLECTION/TRACK"):
        a = track.attrib
        location = urllib.parse.unquote(a.get("Location", ""))
        rows.append({
            "track_id": a.get("TrackID", ""),
            "title": a.get("Name", ""),
            "artist": a.get("Artist", ""),
            "album": a.get("Album", ""),
            "bpm": a.get("AverageBpm", ""),
            "key": a.get("Tonality", ""),
            "duration_sec": a.get("TotalTime", ""),
            "rating": a.get("Rating", ""),
            "genre": a.get("Genre", ""),
            "comments": a.get("Comments", ""),
            "play_count": a.get("PlayCount", ""),
            "location": location,
            "spotify_uri": "",
            "cue_points": json.dumps([
                {
                    "name": mark.attrib.get("Name", ""),
                    "type": mark.attrib.get("Type", ""),
                    "start": parse_number(mark.attrib.get("Start", 0), 0.0),
                    "num": mark.attrib.get("Num", ""),
                }
                for mark in track.findall("POSITION_MARK")
            ], ensure_ascii=False),
            "use": True,
            "role": ROLE_NORMAL,
        })
    collection = finalize_dataframe(pd.DataFrame(rows)) if rows else _empty_standard_df()

    playlists: dict[str, list[str]] = {}
    playlists_root = root.find(".//PLAYLISTS")

    def walk(node: ET.Element, parents: list[str]) -> None:
        name = node.attrib.get("Name", "").strip()
        node_type = node.attrib.get("Type", "0")
        path = parents + ([name] if name and name.upper() != "ROOT" else [])
        if node_type == "1":
            ids = [t.attrib.get("Key", "") for t in node.findall("TRACK") if t.attrib.get("Key")]
            playlists[" / ".join(path) or "Unnamed Playlist"] = ids
        else:
            for child in node.findall("NODE"):
                walk(child, path)

    if playlists_root is not None:
        for node in playlists_root.findall("NODE"):
            walk(node, [])
    return collection, playlists


COLUMN_ALIASES = {
    "track_id": ["trackid", "id", "트랙id"],
    "title": ["title", "name", "tracktitle", "trackname", "곡명", "제목", "트랙제목"],
    "artist": ["artist", "artists", "아티스트", "가수"],
    "album": ["album", "앨범"],
    "bpm": ["bpm", "averagebpm", "평균bpm", "tempo", "템포"],
    "key": ["key", "tonality", "키", "조성"],
    "camelot": ["camelot", "카멜롯"],
    "duration_sec": ["duration", "durationsec", "totaltime", "length", "time", "재생시간", "길이"],
    "rating": ["rating", "stars", "평점", "별점"],
    "energy": ["energy", "에너지"],
    "genre": ["genre", "장르"],
    "comments": ["comments", "comment", "코멘트", "메모"],
    "play_count": ["playcount", "plays", "재생횟수"],
    "location": ["location", "filepath", "path", "파일경로", "위치"],
    "spotify_uri": ["spotifyuri", "spotify_uri", "스포티파이uri"],
    "use": ["use", "include", "사용", "선택"],
    "role": ["role", "역할"],
}


def _norm_col(name: Any) -> str:
    return re.sub(r"[^a-z0-9가-힣]", "", str(name).lower())


def parse_csv(data: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    raw: pd.DataFrame | None = None
    for encoding in ["utf-8-sig", "utf-16", "cp949", "euc-kr", "latin1"]:
        try:
            raw = pd.read_csv(io.BytesIO(data), encoding=encoding, sep=None, engine="python")
            if len(raw.columns) >= 2:
                break
        except Exception as exc:
            last_error = exc
    if raw is None:
        raise ValueError(f"CSV를 읽을 수 없습니다: {last_error}")
    normalized = {_norm_col(c): c for c in raw.columns}
    mapped: dict[str, Any] = {}
    for standard, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _norm_col(alias) in normalized:
                mapped[standard] = raw[normalized[_norm_col(alias)]]
                break
    if "title" not in mapped or "artist" not in mapped:
        raise ValueError("CSV에서 제목(title/name)과 아티스트(artist) 열을 찾지 못했습니다.")
    return finalize_dataframe(pd.DataFrame(mapped))


def filter_playlist(collection: pd.DataFrame, playlists: dict[str, list[str]], playlist_name: str) -> pd.DataFrame:
    if playlist_name == "전체 Collection" or playlist_name not in playlists:
        return collection.copy()
    ids = set(map(str, playlists[playlist_name]))
    return collection[collection["track_id"].astype(str).isin(ids)].copy().reset_index(drop=True)


def curve_value(curve: str, position: float, start: float, peak: float, end: float) -> float:
    p = max(0.0, min(1.0, position))
    if curve == "꾸준히 상승":
        return start + (end - start) * p
    if curve == "초반 피크":
        peak_at = 0.35
    elif curve == "파도형":
        # Piecewise wave with three lifts. It starts/ends at the requested values
        # and reaches the requested peak around the latter half of the set.
        anchors = [
            (0.00, start),
            (0.20, start + (peak - start) * 0.72),
            (0.40, start + (end - start) * 0.45),
            (0.68, peak),
            (0.84, end + (peak - end) * 0.42),
            (1.00, end),
        ]
        for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
            if p <= x1:
                t = (p - x0) / max(x1 - x0, 1e-9)
                # Smoothstep keeps the turns less mechanical.
                t = t * t * (3 - 2 * t)
                return max(1.0, min(10.0, y0 + (y1 - y0) * t))
        return max(1.0, min(10.0, end))
    elif curve == "일정하게":
        return start
    else:  # 중후반 피크
        peak_at = 0.72
    if p <= peak_at:
        return start + (peak - start) * (p / max(peak_at, 1e-9))
    return peak + (end - peak) * ((p - peak_at) / max(1 - peak_at, 1e-9))


def camelot_parts(key: str) -> tuple[int, str] | None:
    match = re.fullmatch(r"([1-9]|1[0-2])([AB])", clean_text(key).upper())
    return (int(match.group(1)), match.group(2)) if match else None


def wheel_distance(a: int, b: int) -> int:
    diff = abs(a - b)
    return min(diff, 12 - diff)


def harmonic_cost(key_a: str, key_b: str) -> float:
    pa, pb = camelot_parts(key_a), camelot_parts(key_b)
    if not pa or not pb:
        return 0.45
    na, la = pa
    nb, lb = pb
    d = wheel_distance(na, nb)
    if na == nb and la == lb:
        return 0.0
    if na == nb and la != lb:
        return 0.12
    if d == 1 and la == lb:
        return 0.10
    if d == 1 and la != lb:
        return 0.32
    return min(1.0, 0.42 + 0.12 * d + (0.08 if la != lb else 0.0))


def harmonic_relation(key_a: str, key_b: str) -> str:
    pa, pb = camelot_parts(key_a), camelot_parts(key_b)
    if not pa or not pb:
        return "키 정보 없음"
    na, la = pa
    nb, lb = pb
    d = wheel_distance(na, nb)
    if na == nb and la == lb:
        return "동일 키"
    if na == nb and la != lb:
        return "상대조"
    if d == 1 and la == lb:
        return "인접 키"
    if d == 1 and la != lb:
        return "대각선 이동"
    return "큰 키 이동"


def effective_bpm_diff(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        return 3.0
    return min(abs(a - b), abs(a * 2 - b), abs(a - b * 2))


def primary_artist(text: str) -> str:
    return re.split(r",|&| feat\.? | featuring | x ", clean_text(text).lower())[0].strip()


@dataclass
class BuildSettings:
    target_minutes: int = 60
    overlap_sec: int = 45
    curve: str = "중후반 피크"
    start_energy: float = 3.0
    peak_energy: float = 9.0
    end_energy: float = 7.0
    start_bpm: float | None = None
    end_bpm: float | None = None
    max_bpm_step: float = 4.0
    harmonic_weight: float = 0.65
    energy_weight: float = 0.65
    bpm_weight: float = 0.75
    artist_gap: int = 3
    seed: int = 42
    iterations: int = 7000
    performance_average_play_sec: int | None = None
    performance_transition_bars: int = 16


def seconds_per_bar(bpm: float, beats_per_bar: int = 4) -> float:
    if bpm <= 0:
        return 2.0
    return (60.0 / bpm) * beats_per_bar


def estimate_track_count(
    df: pd.DataFrame,
    target_minutes: int,
    overlap_sec: int,
    planned_play_sec: int | None = None,
    transition_bars: int = 16,
) -> int:
    if planned_play_sec:
        bpms = pd.to_numeric(df.get("bpm", pd.Series(dtype=float)), errors="coerce")
        valid_bpms = bpms[bpms > 0]
        median_bpm = float(valid_bpms.median()) if not valid_bpms.empty else 120.0
        transition_sec = seconds_per_bar(median_bpm) * max(0, int(transition_bars))
        effective = max(20.0, float(planned_play_sec) - transition_sec)
        count = math.ceil(max(60.0, target_minutes * 60) / effective)
    else:
        durations = pd.to_numeric(df["duration_sec"], errors="coerce").dropna()
        median = float(durations.median()) if not durations.empty else 240.0
        effective = max(60.0, median - overlap_sec)
        count = math.ceil(max(60.0, target_minutes * 60 - overlap_sec) / effective)
    return max(3, min(len(df), count))


def _target_profiles(n: int, settings: BuildSettings, df: pd.DataFrame) -> tuple[list[float], list[float]]:
    positions = [i / max(n - 1, 1) for i in range(n)]
    energy = [curve_value(settings.curve, p, settings.start_energy, settings.peak_energy, settings.end_energy) for p in positions]
    bpms = pd.to_numeric(df["bpm"], errors="coerce")
    valid = bpms[bpms > 0]
    auto_start = float(valid.quantile(0.25)) if not valid.empty else 120.0
    auto_end = float(valid.quantile(0.75)) if not valid.empty else 128.0
    start_bpm = settings.start_bpm if settings.start_bpm and settings.start_bpm > 0 else auto_start
    end_bpm = settings.end_bpm if settings.end_bpm and settings.end_bpm > 0 else auto_end
    bpm = [start_bpm + (end_bpm - start_bpm) * p for p in positions]
    return energy, bpm


def _individual_fit(row: pd.Series, target_energy: float, target_bpm: float, settings: BuildSettings) -> float:
    energy_cost = abs(float(row["energy"]) - target_energy) / 9.0
    bpm = float(row["bpm"] or 0)
    bpm_cost = effective_bpm_diff(bpm, target_bpm) / 15.0 if bpm > 0 else 0.4
    return settings.energy_weight * energy_cost + settings.bpm_weight * bpm_cost


def _sequence_score(rows: list[pd.Series], target_energy: list[float], target_bpm: list[float], settings: BuildSettings) -> float:
    score = 0.0
    for i, row in enumerate(rows):
        score += _individual_fit(row, target_energy[i], target_bpm[i], settings)
        if i == 0:
            continue
        prev = rows[i - 1]
        diff = effective_bpm_diff(float(prev["bpm"]), float(row["bpm"]))
        if diff <= settings.max_bpm_step:
            bpm_transition = (diff / max(settings.max_bpm_step, 0.5)) ** 2 * 0.25
        else:
            bpm_transition = 0.25 + ((diff - settings.max_bpm_step) / max(settings.max_bpm_step, 0.5)) ** 2 * 1.8
        score += settings.bpm_weight * bpm_transition
        score += settings.harmonic_weight * harmonic_cost(str(prev["camelot"]), str(row["camelot"]))
        current_artist = primary_artist(str(row["artist"]))
        if current_artist:
            for distance in range(1, min(settings.artist_gap, i) + 1):
                if current_artist == primary_artist(str(rows[i - distance]["artist"])):
                    score += 1.2 / distance
    return score


def build_set(df: pd.DataFrame, settings: BuildSettings) -> pd.DataFrame:
    candidates = finalize_dataframe(df)
    candidates = candidates[candidates["use"]].reset_index(drop=True)
    if len(candidates) < 3:
        raise ValueError("사용할 후보곡을 최소 3곡 선택해주세요.")
    starts = candidates.index[candidates["role"] == ROLE_START].tolist()
    ends = candidates.index[candidates["role"] == ROLE_END].tolist()
    if len(starts) > 1:
        raise ValueError("'시작' 곡은 한 곡만 지정할 수 있습니다.")
    if len(ends) > 1:
        raise ValueError("'마지막' 곡은 한 곡만 지정할 수 있습니다.")
    forced_indices = set(candidates.index[candidates["role"].isin([ROLE_MUST, ROLE_START, ROLE_END])].tolist())
    n = max(estimate_track_count(candidates, settings.target_minutes, settings.overlap_sec, settings.performance_average_play_sec, settings.performance_transition_bars), len(forced_indices))
    n = min(n, len(candidates))
    target_energy, target_bpm = _target_profiles(n, settings, candidates)
    rng = random.Random(settings.seed)

    positions: list[int | None] = [None] * n
    fixed_positions: set[int] = set()
    if starts:
        positions[0] = starts[0]
        fixed_positions.add(0)
    if ends:
        positions[-1] = ends[0]
        fixed_positions.add(n - 1)

    already = {x for x in positions if x is not None}
    must = [idx for idx in forced_indices if idx not in already]
    open_positions = [i for i, value in enumerate(positions) if value is None]
    # Place forced tracks where their BPM/energy fit best.
    for idx in sorted(must, key=lambda x: float(candidates.loc[x, "energy"])):
        best_pos = min(open_positions, key=lambda pos: _individual_fit(candidates.loc[idx], target_energy[pos], target_bpm[pos], settings))
        positions[best_pos] = idx
        open_positions.remove(best_pos)
        already.add(idx)

    available = [idx for idx in candidates.index if idx not in already]
    # Fill remaining positions with a little seeded variation to produce alternate versions.
    for pos in open_positions:
        scored = []
        for idx in available:
            noise = rng.random() * 0.035
            scored.append((_individual_fit(candidates.loc[idx], target_energy[pos], target_bpm[pos], settings) + noise, idx))
        _, chosen = min(scored)
        positions[pos] = chosen
        available.remove(chosen)

    sequence = [int(x) for x in positions if x is not None]
    selected = set(sequence)
    unused = [idx for idx in candidates.index if idx not in selected]
    current_rows = [candidates.loc[idx] for idx in sequence]
    current_score = _sequence_score(current_rows, target_energy, target_bpm, settings)
    best_seq, best_score = sequence[:], current_score
    movable = [i for i in range(n) if i not in fixed_positions]

    temperature = 0.22
    for iteration in range(max(500, settings.iterations)):
        proposal = sequence[:]
        proposal_unused = unused[:]
        replace_allowed_positions = [p for p in movable if proposal[p] not in forced_indices]
        do_replace = bool(proposal_unused and replace_allowed_positions and rng.random() < 0.28)
        if do_replace:
            pos = rng.choice(replace_allowed_positions)
            new_idx = rng.choice(proposal_unused)
            old_idx = proposal[pos]
            proposal[pos] = new_idx
            proposal_unused.remove(new_idx)
            proposal_unused.append(old_idx)
        elif len(movable) >= 2:
            i, j = rng.sample(movable, 2)
            proposal[i], proposal[j] = proposal[j], proposal[i]
        else:
            break
        proposal_rows = [candidates.loc[idx] for idx in proposal]
        proposal_score = _sequence_score(proposal_rows, target_energy, target_bpm, settings)
        delta = proposal_score - current_score
        progress = iteration / max(settings.iterations - 1, 1)
        temp = max(0.006, temperature * (1 - progress))
        if delta < 0 or rng.random() < math.exp(-delta / temp):
            sequence, unused, current_score = proposal, proposal_unused, proposal_score
            if current_score < best_score:
                best_seq, best_score = sequence[:], current_score

    rows = candidates.loc[best_seq].copy().reset_index(drop=True)
    rows.insert(0, "order", range(1, len(rows) + 1))
    rows["target_energy"] = [round(x, 1) for x in target_energy]
    rows["target_bpm"] = [round(x, 1) for x in target_bpm]
    rows["bpm_change"] = [0.0] + [round(float(rows.loc[i, "bpm"]) - float(rows.loc[i - 1, "bpm"]), 1) for i in range(1, len(rows))]
    rows["key_transition"] = ["시작"] + [harmonic_relation(str(rows.loc[i - 1, "camelot"]), str(rows.loc[i, "camelot"])) for i in range(1, len(rows))]
    rows["transition_score"] = [100] + [round(100 * (1 - harmonic_cost(str(rows.loc[i - 1, "camelot"]), str(rows.loc[i, "camelot"]))), 0) for i in range(1, len(rows))]
    cumulative = []
    total = 0.0
    for i, duration in enumerate(rows["duration_sec"].astype(float)):
        total += duration if i == 0 else max(30.0, duration - settings.overlap_sec)
        cumulative.append(total)
    rows["set_time"] = [format_seconds(x) for x in cumulative]
    rows.attrs["score"] = best_score
    rows.attrs["estimated_duration_sec"] = total
    return rows


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    hours, rem = divmod(seconds, 3600)
    minutes, sec = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{sec:02d}" if hours else f"{minutes}:{sec:02d}"


def export_set_csv(df: pd.DataFrame) -> bytes:
    columns = [
        "order", "title", "artist", "performance_role", "priority",
        "play_start_time", "next_track_in_time", "play_end_time", "used_range",
        "main_range", "transition_range", "planned_play_time",
        "mix_in_sec", "next_track_in_sec", "mix_out_sec", "planned_play_sec",
        "play_bars", "transition_bars", "structure_source", "confidence", "plan_reason",
        "set_start_time", "set_next_mix_time", "set_end_time", "set_range",
        "set_start_sec", "set_next_mix_sec", "set_end_sec",
        "bpm", "key", "camelot", "energy", "target_energy", "bpm_change",
        "key_transition", "transition_score", "duration_sec", "set_time",
        "genre", "comments", "location", "spotify_uri"
    ]
    usable = [c for c in columns if c in df.columns]
    return df[usable].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def _location_to_uri(value: Any) -> str:
    """Return a Rekordbox-compatible file URI when possible."""
    text = clean_text(value)
    if not text:
        return ""
    if text.lower().startswith("file:"):
        return text
    normalized = text.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", normalized):
        return "file://localhost/" + urllib.parse.quote(normalized, safe="/:~!$&'()*+,;=@")
    try:
        path = Path(text).expanduser()
        return path.resolve(strict=False).as_uri()
    except Exception:
        return ""


def _location_to_path(value: Any) -> str:
    """Convert a Rekordbox file URI to a local path for M3U8 output."""
    text = clean_text(value)
    if not text:
        return ""
    if not text.lower().startswith("file:"):
        return text
    parsed = urllib.parse.urlparse(text)
    path = urllib.parse.unquote(parsed.path or "")
    if parsed.netloc and parsed.netloc.lower() not in {"", "localhost"}:
        path = f"//{parsed.netloc}{path}"
    if re.match(r"^/[A-Za-z]:/", path):
        path = path[1:]
    return path


def assess_rekordbox_export(set_df: pd.DataFrame) -> pd.DataFrame:
    """Classify each set row by whether it can be exported as a playable local track."""
    rows: list[dict[str, Any]] = []
    for pos, (_, row) in enumerate(set_df.iterrows(), start=1):
        location = clean_text(row.get("location"))
        spotify_uri = clean_text(row.get("spotify_uri"))
        if location and _location_to_uri(location):
            status = "READY"
            reason = "로컬 파일 경로 확인됨"
            include = True
        elif spotify_uri.startswith("spotify:track:"):
            status = "STREAMING ONLY"
            reason = "Spotify 곡은 로컬 파일 경로가 없어 Rekordbox 파일로 내보낼 수 없습니다."
            include = False
        else:
            status = "PATH MISSING"
            reason = "로컬 파일 위치가 없거나 경로 형식을 해석할 수 없습니다."
            include = False
        rows.append({
            "order": int(row.get("order", pos) or pos),
            "title": clean_text(row.get("title")),
            "artist": clean_text(row.get("artist")),
            "location": location,
            "status": status,
            "reason": reason,
            "include": include,
        })
    return pd.DataFrame(rows)


def _safe_track_id(value: Any, fallback: int, used: set[int]) -> int:
    try:
        candidate = int(float(clean_text(value)))
    except Exception:
        candidate = fallback
    while candidate in used or candidate <= 0:
        candidate += 1
    used.add(candidate)
    return candidate


def export_rekordbox_xml(set_df: pd.DataFrame, playlist_name: str = "DPC DJ Set") -> bytes:
    """Create a Rekordbox XML collection containing playable local tracks in set order."""
    assessment = assess_rekordbox_export(set_df)
    ready_orders = set(assessment.loc[assessment["include"], "order"].astype(int).tolist())
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
    ET.SubElement(root, "PRODUCT", Name="DPC SetLab", Version="4.0.5-dev", Company="DPC")
    collection = ET.SubElement(root, "COLLECTION")
    playlist_tracks: list[int] = []
    used_ids: set[int] = set()

    ready_rows = []
    for pos, (_, row) in enumerate(set_df.iterrows(), start=1):
        order = int(row.get("order", pos) or pos)
        if order not in ready_orders:
            continue
        ready_rows.append(row)
    collection.set("Entries", str(len(ready_rows)))

    for pos, row in enumerate(ready_rows, start=1):
        track_id = _safe_track_id(row.get("track_id"), 100000 + pos, used_ids)
        playlist_tracks.append(track_id)
        attrs = {
            "TrackID": str(track_id),
            "Name": clean_text(row.get("title")),
            "Artist": clean_text(row.get("artist")),
            "Album": clean_text(row.get("album")),
            "Genre": clean_text(row.get("genre")),
            "TotalTime": str(int(round(parse_duration(row.get("duration_sec"), 0)))),
            "AverageBpm": f"{parse_number(row.get('bpm'), 0):.2f}",
            "Tonality": clean_text(row.get("key")),
            "Comments": clean_text(row.get("comments")),
            "Location": _location_to_uri(row.get("location")),
        }
        track = ET.SubElement(collection, "TRACK", **attrs)
        cue_raw = row.get("cue_points")
        try:
            cues = json.loads(cue_raw) if isinstance(cue_raw, str) and cue_raw.strip() else cue_raw
        except Exception:
            cues = []
        if isinstance(cues, list):
            for cue in cues:
                if not isinstance(cue, dict):
                    continue
                cue_attrs = {
                    "Name": clean_text(cue.get("name")),
                    "Type": clean_text(cue.get("type")) or "0",
                    "Start": f"{parse_number(cue.get('start'), 0):.3f}",
                    "Num": clean_text(cue.get("num")) or "-1",
                }
                ET.SubElement(track, "POSITION_MARK", **cue_attrs)

    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT", Count="1")
    folder = ET.SubElement(root_node, "NODE", Type="0", Name="DPC SetLab", Count="1")
    playlist = ET.SubElement(
        folder, "NODE", Type="1", Name=clean_text(playlist_name) or "DPC DJ Set",
        KeyType="0", Entries=str(len(playlist_tracks))
    )
    for track_id in playlist_tracks:
        ET.SubElement(playlist, "TRACK", Key=str(track_id))

    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    buffer = io.BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


def export_m3u8(set_df: pd.DataFrame) -> bytes:
    """Create an extended UTF-8 M3U playlist containing playable local tracks."""
    assessment = assess_rekordbox_export(set_df)
    ready_orders = set(assessment.loc[assessment["include"], "order"].astype(int).tolist())
    lines = ["#EXTM3U"]
    for pos, (_, row) in enumerate(set_df.iterrows(), start=1):
        order = int(row.get("order", pos) or pos)
        if order not in ready_orders:
            continue
        duration = int(round(parse_duration(row.get("duration_sec"), 0)))
        label = " - ".join(x for x in [clean_text(row.get("artist")), clean_text(row.get("title"))] if x)
        lines.append(f"#EXTINF:{duration},{label}")
        lines.append(_location_to_path(row.get("location")))
    return ("\ufeff" + "\n".join(lines) + "\n").encode("utf-8")
