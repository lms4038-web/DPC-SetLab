from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from song_structure import safe_cues, select_structure_window


ROLE_WEIGHTS = {
    "opening": 1.35,
    "warmup": 1.10,
    "build": 1.00,
    "bridge": 0.78,
    "peak": 1.28,
    "closing": 1.38,
}

ROLE_LABELS = {
    "opening": "오프닝",
    "warmup": "웜업",
    "build": "빌드업",
    "bridge": "브리지",
    "peak": "피크",
    "closing": "클로징",
}


@dataclass
class PerformancePlanSettings:
    average_play_sec: int = 90
    tolerance_sec: int = 15
    transition_bars: int = 16
    phrase_bars: int = 16
    variable_timing: bool = True


def seconds_per_bar(bpm: float, beats_per_bar: int = 4) -> float:
    if bpm <= 0:
        return 2.0
    return (60.0 / bpm) * beats_per_bar


def infer_performance_role(position: int, total: int, energy: float, comments: str = "") -> str:
    p = position / max(total - 1, 1)
    text = (comments or "").lower()
    if position == 0:
        return "opening"
    if position == total - 1:
        return "closing"
    if any(k in text for k in ("bridge", "transition", "브리지", "전환")):
        return "bridge"
    if any(k in text for k in ("peak", "banger", "anthem", "피크", "메인")) or energy >= 8.3:
        return "peak"
    if p < 0.25:
        return "warmup"
    if 0.25 <= p < 0.62:
        return "build"
    if p >= 0.62 and energy >= 7.2:
        return "peak"
    return "bridge" if p >= 0.75 else "build"


def _role_target_seconds(role: str, settings: PerformancePlanSettings) -> float:
    if not settings.variable_timing:
        return float(settings.average_play_sec)
    return settings.average_play_sec * ROLE_WEIGHTS.get(role, 1.0)


def _nearest_phrase_duration(target_sec: float, bpm: float, phrase_bars: int, tolerance_sec: int, max_sec: float) -> tuple[int, float]:
    bar_sec = seconds_per_bar(bpm)
    phrase_bars = max(4, int(phrase_bars))
    candidates = []
    for multiplier in range(1, 17):
        bars = phrase_bars * multiplier
        sec = bars * bar_sec
        if sec <= max_sec + tolerance_sec:
            candidates.append((bars, sec))
    if not candidates:
        bars = max(phrase_bars, int(max_sec / max(bar_sec, 0.1) // phrase_bars) * phrase_bars)
        return bars, min(max_sec, bars * bar_sec)
    within = [c for c in candidates if abs(c[1] - target_sec) <= tolerance_sec]
    pool = within or candidates
    return min(pool, key=lambda x: abs(x[1] - target_sec))


def _cue_candidates(cues: list[dict[str, Any]], duration_sec: float) -> list[float]:
    values = []
    for cue in cues:
        try:
            start = float(cue.get("start", 0))
        except (TypeError, ValueError):
            continue
        if 0 <= start <= duration_sec:
            values.append(start)
    return sorted(set(values))


def _select_window_from_cues(cue_times: list[float], desired_sec: float, duration_sec: float, tolerance_sec: int) -> tuple[float, float] | None:
    if len(cue_times) < 2:
        return None
    best = None
    best_cost = float("inf")
    boundaries = sorted(set([0.0, *cue_times, duration_sec]))
    for i, start in enumerate(boundaries[:-1]):
        for end in boundaries[i + 1:]:
            length = end - start
            if length < 20:
                continue
            cost = abs(length - desired_sec)
            if cost < best_cost:
                best = (start, end)
                best_cost = cost
    if best and best_cost <= max(tolerance_sec * 2, desired_sec * 0.35):
        return best
    return None


def plan_track(row: pd.Series, position: int, total: int, settings: PerformancePlanSettings) -> dict[str, Any]:
    bpm = float(row.get("bpm", 0) or 0)
    duration_sec = float(row.get("duration_sec", 0) or 0)
    energy = float(row.get("energy", 5) or 5)
    role = infer_performance_role(position, total, energy, str(row.get("comments", "")))
    desired = _role_target_seconds(role, settings)
    desired = min(max(30.0, desired), max(30.0, duration_sec))
    cues = safe_cues(row.get("cue_points", ""))
    cue_times = _cue_candidates(cues, duration_sec)
    structure_window = select_structure_window(
        cues=cues,
        duration_sec=duration_sec,
        desired_sec=desired,
        role=role,
        tolerance_sec=settings.tolerance_sec,
    )

    bar_sec = seconds_per_bar(bpm)
    if structure_window:
        start, suggested_end, source, confidence = structure_window
        available = max(0.0, suggested_end - start)
        raw_bars = max(
            settings.phrase_bars,
            round(available / bar_sec / settings.phrase_bars) * settings.phrase_bars,
        )
        # Never let a sparse cue span silently expand a 90-second request into a full track.
        max_allowed = min(duration_sec - start, desired + max(settings.tolerance_sec, settings.phrase_bars * bar_sec))
        play_sec = min(available, raw_bars * bar_sec, max_allowed)
        end = min(duration_sec, start + play_sec)
        raw_bars = max(settings.phrase_bars, int(round((end - start) / bar_sec / settings.phrase_bars)) * settings.phrase_bars)
    else:
        bars, play_sec = _nearest_phrase_duration(desired, bpm, settings.phrase_bars, settings.tolerance_sec, duration_sec)
        start = 0.0
        if role in {"bridge", "peak"} and duration_sec > play_sec + 20:
            # Without phrase data, start near the first third but remain on a phrase boundary.
            target_start = min(duration_sec - play_sec, duration_sec * 0.22)
            start_bars = max(0, round(target_start / bar_sec / settings.phrase_bars) * settings.phrase_bars)
            start = start_bars * bar_sec
        end = min(duration_sec, start + play_sec)
        raw_bars = bars
        source = "BPM 기반 추정"
        confidence = "낮음"

    transition_bars = min(settings.transition_bars, max(8, raw_bars // 2))
    transition_sec = transition_bars * bar_sec
    effective_sec = max(20.0, (end - start) - (0 if position == 0 else transition_sec))
    reason = f"{ROLE_LABELS[role]} 역할에 맞춰 {raw_bars}마디 사용"
    if source.startswith("Rekordbox 구조 Cue"):
        reason += ", 이름이 지정된 Cue와 역할별 선호 구간을 함께 적용"
    else:
        reason += ", 정확한 phrase 정보가 없어 BPM 기준 추정"

    return {
        "performance_role": ROLE_LABELS[role],
        "priority": 5 if role in {"opening", "peak", "closing"} else 3 if role in {"warmup", "build"} else 2,
        "mix_in_sec": round(start, 1),
        "mix_out_sec": round(end, 1),
        "play_bars": int(raw_bars),
        "transition_bars": int(transition_bars),
        "planned_play_sec": round(end - start, 1),
        "target_play_sec": round(desired, 1),
        "min_play_sec": round(max(30.0, desired - settings.tolerance_sec), 1),
        "max_play_sec": round(min(duration_sec, desired + settings.tolerance_sec), 1),
        "effective_set_sec": round(effective_sec, 1),
        "structure_source": source,
        "confidence": confidence,
        "plan_reason": reason,
    }


def apply_performance_plan(df: pd.DataFrame, settings: PerformancePlanSettings, target_sec: int | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy().reset_index(drop=True)
    plans = [plan_track(out.loc[i], i, len(out), settings) for i in range(len(out))]
    for key in plans[0]:
        out[key] = [p[key] for p in plans]

    # Small global correction: extend or shorten phrase blocks until target error is minimized.
    if target_sec and target_sec > 0:
        for _ in range(200):
            current = float(out["effective_set_sec"].sum())
            error = target_sec - current
            if abs(error) <= settings.tolerance_sec:
                break
            candidates = []
            for i, row in out.iterrows():
                bar_sec = seconds_per_bar(float(row.get("bpm", 0) or 0))
                delta = settings.phrase_bars * bar_sec
                next_play = float(row["planned_play_sec"]) + (delta if error > 0 else -delta)
                if (
                    error > 0
                    and next_play <= float(row.get("max_play_sec", row["planned_play_sec"])) + 0.1
                    and row["mix_out_sec"] + delta <= float(row.get("duration_sec", 0) or 0)
                ):
                    candidates.append((abs(error - delta), i, delta))
                elif (
                    error < 0
                    and next_play >= float(row.get("min_play_sec", 30)) - 0.1
                ):
                    candidates.append((abs(error + delta), i, -delta))
            if not candidates:
                break
            _, i, delta = min(candidates)
            out.at[i, "mix_out_sec"] = round(float(out.at[i, "mix_out_sec"]) + delta, 1)
            out.at[i, "planned_play_sec"] = round(float(out.at[i, "planned_play_sec"]) + delta, 1)
            out.at[i, "effective_set_sec"] = round(float(out.at[i, "effective_set_sec"]) + delta, 1)
            bars_delta = settings.phrase_bars if delta > 0 else -settings.phrase_bars
            out.at[i, "play_bars"] = int(out.at[i, "play_bars"] + bars_delta)

    # Build human-readable used-segment markers after every duration correction.
    transition_seconds = []
    next_mix_in_seconds = []
    for _, row in out.iterrows():
        bar_sec = seconds_per_bar(float(row.get("bpm", 0) or 0))
        transition_sec = min(
            float(row.get("planned_play_sec", 0) or 0),
            int(row.get("transition_bars", 0) or 0) * bar_sec,
        )
        transition_seconds.append(round(transition_sec, 1))
        next_mix_in_seconds.append(
            round(max(float(row["mix_in_sec"]), float(row["mix_out_sec"]) - transition_sec), 1)
        )

    out["transition_sec"] = transition_seconds
    out["next_track_in_sec"] = next_mix_in_seconds
    out["play_start_time"] = out["mix_in_sec"].map(_format_seconds)
    out["next_track_in_time"] = out["next_track_in_sec"].map(_format_seconds)
    out["play_end_time"] = out["mix_out_sec"].map(_format_seconds)
    out["used_range"] = out["play_start_time"] + " → " + out["play_end_time"]
    out["main_range"] = out["play_start_time"] + " → " + out["next_track_in_time"]
    out["transition_range"] = out["next_track_in_time"] + " → " + out["play_end_time"]
    out["planned_play_time"] = out["planned_play_sec"].map(_format_seconds)

    # Set timeline is distinct from the time position inside each audio file.
    set_starts = []
    set_ends = []
    set_transition_starts = []
    elapsed = 0.0
    for _, row in out.iterrows():
        start = elapsed
        end = start + float(row.get("planned_play_sec", 0) or 0)
        transition_start = max(start, end - float(row.get("transition_sec", 0) or 0))
        set_starts.append(round(start, 1))
        set_ends.append(round(end, 1))
        set_transition_starts.append(round(transition_start, 1))
        elapsed += float(row.get("effective_set_sec", 0) or 0)

    out["set_start_sec"] = set_starts
    out["set_next_mix_sec"] = set_transition_starts
    out["set_end_sec"] = set_ends
    out["set_start_time"] = out["set_start_sec"].map(_format_seconds)
    out["set_next_mix_time"] = out["set_next_mix_sec"].map(_format_seconds)
    out["set_end_time"] = out["set_end_sec"].map(_format_seconds)
    out["set_range"] = out["set_start_time"] + " → " + out["set_end_time"]

    cumulative = out["effective_set_sec"].cumsum()
    out["set_time"] = cumulative.map(_format_seconds)
    out.attrs.update(df.attrs)
    out.attrs["estimated_duration_sec"] = float(out["effective_set_sec"].sum())
    out.attrs["performance_plan_enabled"] = True
    out.attrs["target_duration_sec"] = float(target_sec or 0)
    out.attrs["target_gap_sec"] = float((target_sec or 0) - out["effective_set_sec"].sum()) if target_sec else 0.0
    return out


def _format_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{sec:02d}" if hours else f"{minutes}:{sec:02d}"
