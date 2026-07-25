import pandas as pd

from dpc_core import BuildSettings, recalculate_set_sequence


def test_reorder_recalculates_order_and_transitions():
    df = pd.DataFrame([
        {"order": 1, "title": "A", "artist": "DJ", "bpm": 120.0, "camelot": "8A", "duration_sec": 180, "energy": 4},
        {"order": 2, "title": "B", "artist": "DJ", "bpm": 124.0, "camelot": "9A", "duration_sec": 200, "energy": 7},
        {"order": 3, "title": "C", "artist": "DJ", "bpm": 126.0, "camelot": "10A", "duration_sec": 220, "energy": 8},
    ])
    reordered = df.iloc[[2, 0, 1]].reset_index(drop=True)
    settings = BuildSettings(target_minutes=30, overlap_sec=45)
    result = recalculate_set_sequence(reordered, settings)
    assert result["title"].tolist() == ["C", "A", "B"]
    assert result["order"].tolist() == [1, 2, 3]
    assert result["bpm_change"].tolist() == [0.0, -6.0, 4.0]
    assert result.iloc[0]["key_transition"] == "시작"
    assert result.attrs["estimated_duration_sec"] > 0
