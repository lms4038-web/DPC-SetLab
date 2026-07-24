import pandas as pd
from playlist_intelligence import diagnose_playlist, playlist_summary


def sample_df(n=20):
    return pd.DataFrame({
        "title": [f"Track {i}" for i in range(n)],
        "artist": [f"Artist {i%8}" for i in range(n)],
        "bpm": [120 + i % 8 for i in range(n)],
        "camelot": [f"{(i%12)+1}A" for i in range(n)],
        "energy": [3 + (i % 7) for i in range(n)],
        "duration_sec": [240] * n,
        "genre": ["House"] * n,
    })


def test_summary_counts_and_duration():
    summary = playlist_summary(sample_df(10))
    assert summary["track_count"] == 10
    assert summary["total_seconds"] == 2400
    assert summary["key_coverage"] == 1.0


def test_diagnosis_flags_short_playlist():
    diagnosis = diagnose_playlist(sample_df(5), target_minutes=60)
    assert diagnosis.score < 70
    assert "부족" in diagnosis.verdict


def test_diagnosis_accepts_healthy_playlist():
    diagnosis = diagnose_playlist(sample_df(25), target_minutes=60)
    assert diagnosis.score >= 70
    assert "충분" in diagnosis.verdict
