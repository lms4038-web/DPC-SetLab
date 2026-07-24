import json

import pandas as pd

from dpc_core import parse_rekordbox_xml
from performance_planner import PerformancePlanSettings, apply_performance_plan, seconds_per_bar


def test_seconds_per_bar():
    assert round(seconds_per_bar(120), 2) == 2.0


def test_xml_position_marks_are_parsed():
    xml = b'''<?xml version="1.0"?><DJ_PLAYLISTS><COLLECTION>
    <TRACK TrackID="1" Name="Cue Song" Artist="DJ" AverageBpm="120" TotalTime="180">
      <POSITION_MARK Name="Intro" Type="0" Start="0.000" Num="-1"/>
      <POSITION_MARK Name="Drop" Type="0" Start="64.000" Num="0"/>
      <POSITION_MARK Name="Outro" Type="0" Start="128.000" Num="1"/>
    </TRACK></COLLECTION><PLAYLISTS/></DJ_PLAYLISTS>'''
    df, _ = parse_rekordbox_xml(xml)
    cues = json.loads(df.iloc[0]["cue_points"])
    assert len(cues) == 3
    assert cues[1]["name"] == "Drop"
    assert cues[1]["start"] == 64.0


def test_performance_plan_uses_phrase_bars_and_target():
    df = pd.DataFrame([
        {"title": f"Track {i}", "artist": "DJ", "bpm": 120, "duration_sec": 240,
         "energy": 4 + i, "comments": "peak" if i == 2 else "", "cue_points": "[]"}
        for i in range(4)
    ])
    settings = PerformancePlanSettings(average_play_sec=90, tolerance_sec=20, transition_bars=16, phrase_bars=16)
    result = apply_performance_plan(df, settings, target_sec=360)
    assert set(["performance_role", "mix_in_sec", "mix_out_sec", "play_bars", "confidence"]).issubset(result.columns)
    assert all(result["play_bars"] % 16 == 0)
    assert abs(result.attrs["estimated_duration_sec"] - 360) <= 40


def test_target_correction_never_stretches_tracks_beyond_user_tolerance():
    import pandas as pd
    from performance_planner import PerformancePlanSettings, apply_performance_plan

    df = pd.DataFrame([
        {"title": f"Track {i}", "artist": "DJ", "bpm": 120, "duration_sec": 300, "energy": 5, "cue_points": ""}
        for i in range(13)
    ])
    settings = PerformancePlanSettings(
        average_play_sec=90,
        tolerance_sec=15,
        transition_bars=16,
        phrase_bars=16,
        variable_timing=False,
    )
    result = apply_performance_plan(df, settings, target_sec=3600)
    assert result["planned_play_sec"].max() <= 105.1
    assert result.attrs["target_gap_sec"] > 0


def test_used_segment_display_fields_are_generated():
    df = pd.DataFrame([
        {"title": f"Track {i}", "artist": "DJ", "bpm": 120, "duration_sec": 240,
         "energy": 5, "comments": "", "cue_points": "[]"}
        for i in range(4)
    ])
    settings = PerformancePlanSettings(average_play_sec=90, tolerance_sec=15, transition_bars=16, phrase_bars=16)
    result = apply_performance_plan(df, settings, target_sec=300)
    expected = {
        "play_start_time", "next_track_in_time", "play_end_time", "used_range",
        "main_range", "transition_range", "planned_play_time",
        "set_start_time", "set_next_mix_time", "set_end_time", "set_range",
    }
    assert expected.issubset(result.columns)
    assert result.iloc[0]["used_range"].count("→") == 1
    assert result.iloc[0]["main_range"].count("→") == 1
    assert result.iloc[0]["transition_range"].count("→") == 1
    assert result.iloc[0]["set_range"].count("→") == 1
    assert result.iloc[0]["next_track_in_sec"] <= result.iloc[0]["mix_out_sec"]
    assert result.iloc[0]["next_track_in_sec"] >= result.iloc[0]["mix_in_sec"]


def test_named_structure_cues_prefer_drop_for_peak_role():
    cues = json.dumps([
        {"name": "Intro", "start": 0.0},
        {"name": "Break", "start": 48.0},
        {"name": "Drop 1", "start": 80.0},
        {"name": "Break 2", "start": 144.0},
        {"name": "Drop 2", "start": 176.0},
        {"name": "Outro", "start": 240.0},
    ])
    df = pd.DataFrame([
        {"title": "Warm", "artist": "DJ", "bpm": 120, "duration_sec": 300, "energy": 5, "cue_points": "[]"},
        {"title": "Peak", "artist": "DJ", "bpm": 120, "duration_sec": 300, "energy": 9, "comments": "peak", "cue_points": cues},
        {"title": "Close", "artist": "DJ", "bpm": 120, "duration_sec": 300, "energy": 5, "cue_points": "[]"},
    ])
    settings = PerformancePlanSettings(average_play_sec=90, tolerance_sec=15, transition_bars=16, phrase_bars=16)
    result = apply_performance_plan(df, settings)
    peak = result.iloc[1]
    assert peak["mix_in_sec"] >= 70
    assert "drop" in peak["structure_source"]
    assert peak["planned_play_sec"] <= peak["target_play_sec"] + 32.1


def test_sparse_cues_do_not_force_near_full_track_playback():
    cues = json.dumps([
        {"name": "Intro", "start": 0.0},
        {"name": "Outro", "start": 260.0},
    ])
    df = pd.DataFrame([
        {"title": "Sparse", "artist": "DJ", "bpm": 120, "duration_sec": 300, "energy": 5, "cue_points": cues},
        {"title": "End", "artist": "DJ", "bpm": 120, "duration_sec": 300, "energy": 5, "cue_points": "[]"},
    ])
    settings = PerformancePlanSettings(
        average_play_sec=90,
        tolerance_sec=15,
        transition_bars=16,
        phrase_bars=16,
        variable_timing=False,
    )
    result = apply_performance_plan(df, settings)
    assert result.iloc[0]["planned_play_sec"] <= 106
    assert result.iloc[0]["structure_source"] == "BPM 기반 추정"
