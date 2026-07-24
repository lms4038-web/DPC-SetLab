import xml.etree.ElementTree as ET
import pandas as pd

from dpc_core import assess_rekordbox_export, export_m3u8, export_rekordbox_xml


def sample_set():
    return pd.DataFrame([
        {"order": 1, "track_id": "12", "title": "Local A", "artist": "DJ A", "album": "", "genre": "House", "duration_sec": 240, "bpm": 124, "key": "8A", "comments": "", "location": "C:/Music/A.mp3", "spotify_uri": "", "cue_points": "[]"},
        {"order": 2, "track_id": "", "title": "Stream B", "artist": "DJ B", "duration_sec": 210, "location": "", "spotify_uri": "spotify:track:abc"},
    ])


def test_assessment_separates_local_and_streaming():
    result = assess_rekordbox_export(sample_set())
    assert result["status"].tolist() == ["READY", "STREAMING ONLY"]
    assert result["include"].tolist() == [True, False]


def test_rekordbox_xml_contains_only_local_tracks():
    data = export_rekordbox_xml(sample_set(), "My Set")
    root = ET.fromstring(data)
    assert root.find("COLLECTION").attrib["Entries"] == "1"
    assert root.find(".//COLLECTION/TRACK").attrib["Name"] == "Local A"
    playlist = root.find(".//PLAYLISTS/NODE/NODE/NODE")
    assert playlist.attrib["Name"] == "My Set"
    assert playlist.attrib["Entries"] == "1"


def test_m3u8_contains_extended_metadata_and_path():
    text = export_m3u8(sample_set()).decode("utf-8-sig")
    assert text.startswith("#EXTM3U")
    assert "#EXTINF:240,DJ A - Local A" in text
    assert "C:/Music/A.mp3" in text
    assert "Stream B" not in text
