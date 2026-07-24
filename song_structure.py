from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


LABEL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("intro", ("intro", "start", "opening", "인트로", "시작")),
    ("build", ("build", "buildup", "rise", "pre drop", "프리드롭", "빌드", "상승")),
    ("break", ("break", "breakdown", "verse", "vocal", "브레이크", "벌스", "보컬")),
    ("drop", ("drop", "chorus", "hook", "main", "peak", "드롭", "후렴", "메인", "피크")),
    ("outro", ("outro", "end", "ending", "아웃트로", "엔딩", "끝")),
)

ROLE_SECTION_PREFERENCES = {
    "opening": {"intro": 5.0, "build": 2.5, "break": 1.5, "drop": 0.5, "outro": -1.0},
    "warmup": {"intro": 3.0, "build": 3.0, "break": 2.0, "drop": 1.5, "outro": 0.0},
    "build": {"intro": 0.5, "build": 4.0, "break": 2.5, "drop": 4.0, "outro": 0.0},
    "bridge": {"intro": 0.0, "build": 2.0, "break": 4.0, "drop": 1.0, "outro": 1.0},
    "peak": {"intro": -1.0, "build": 3.0, "break": 2.0, "drop": 6.0, "outro": 0.0},
    "closing": {"intro": 0.0, "build": 1.0, "break": 2.5, "drop": 2.0, "outro": 5.0},
}


@dataclass(frozen=True)
class StructurePoint:
    start: float
    label: str
    name: str = ""


def safe_cues(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def normalize_label(name: str) -> str:
    text = re.sub(r"[_\-]+", " ", str(name or "").strip().lower())
    text = re.sub(r"\s+", " ", text)
    for label, keywords in LABEL_RULES:
        if any(keyword in text for keyword in keywords):
            return label
    return "cue"


def structure_points(cues: list[dict[str, Any]], duration_sec: float) -> list[StructurePoint]:
    points: list[StructurePoint] = []
    for cue in cues:
        try:
            start = float(cue.get("start", 0))
        except (TypeError, ValueError):
            continue
        if not 0 <= start <= duration_sec:
            continue
        name = str(cue.get("name", "") or "")
        points.append(StructurePoint(start=start, label=normalize_label(name), name=name))
    # Keep one point per time, preferring a semantic label over an unnamed cue.
    merged: dict[float, StructurePoint] = {}
    for point in sorted(points, key=lambda p: p.start):
        previous = merged.get(point.start)
        if previous is None or (previous.label == "cue" and point.label != "cue"):
            merged[point.start] = point
    return list(merged.values())


def infer_structure_boundaries(cues: list[dict[str, Any]], duration_sec: float) -> list[StructurePoint]:
    points = structure_points(cues, duration_sec)
    if not any(abs(point.start) < 0.01 for point in points):
        points.insert(0, StructurePoint(0.0, "intro", "곡 시작"))
    if not any(abs(point.start - duration_sec) < 0.01 for point in points):
        points.append(StructurePoint(duration_sec, "end", "곡 종료"))
    return sorted(points, key=lambda p: p.start)


def _window_labels(points: list[StructurePoint], start: float, end: float) -> list[str]:
    labels = [point.label for point in points if start <= point.start < end and point.label not in {"cue", "end"}]
    if not labels:
        # Use the last known section at the window start.
        prior = [point.label for point in points if point.start <= start and point.label not in {"cue", "end"}]
        if prior:
            labels = [prior[-1]]
    return labels


def select_structure_window(
    cues: list[dict[str, Any]],
    duration_sec: float,
    desired_sec: float,
    role: str,
    tolerance_sec: float,
    min_sec: float = 30.0,
) -> tuple[float, float, str, str] | None:
    """Choose a semantically useful cue-to-cue window.

    Returns start, end, source-detail, confidence. It intentionally rejects windows
    that are much longer than the requested play time, preventing a few sparse cues
    from causing near-full-track playback.
    """
    points = infer_structure_boundaries(cues, duration_sec)
    semantic_count = sum(point.label not in {"cue", "end"} for point in points)
    if len(points) < 3:
        return None

    preferences = ROLE_SECTION_PREFERENCES.get(role, {})
    max_window = min(duration_sec, desired_sec + max(tolerance_sec * 2.0, desired_sec * 0.28))
    min_window = max(min_sec, desired_sec - max(tolerance_sec * 2.0, desired_sec * 0.38))
    candidates: list[tuple[float, float, float, list[str]]] = []

    for i, left in enumerate(points[:-1]):
        for right in points[i + 1:]:
            length = right.start - left.start
            if length < min_window or length > max_window:
                continue
            labels = _window_labels(points, left.start, right.start)
            duration_cost = abs(length - desired_sec) / max(desired_sec, 1.0) * 8.0
            section_score = max((preferences.get(label, 0.0) for label in labels), default=0.0)
            # Favor windows that begin on a named semantic marker.
            boundary_bonus = 1.5 if left.label not in {"cue", "end"} else 0.0
            score = section_score + boundary_bonus - duration_cost
            candidates.append((score, left.start, right.start, labels))

    if not candidates:
        return None
    score, start, end, labels = max(candidates, key=lambda item: (item[0], -abs((item[2] - item[1]) - desired_sec)))
    label_text = "+".join(dict.fromkeys(labels)) if labels else "cue"
    confidence = "높음" if semantic_count >= 3 and score >= 2.0 else "중간"
    return start, end, f"Rekordbox 구조 Cue ({label_text})", confidence
