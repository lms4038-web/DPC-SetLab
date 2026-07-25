import pandas as pd
from pathlib import Path
from xml.etree import ElementTree as ET

from dpc_core import analyze_rekordbox_xml, assess_rekordbox_sync, parse_rekordbox_xml, sync_rekordbox_xml


def sample_bytes():
    return Path('samples/sample_rekordbox.xml').read_bytes()


def test_analyze_rekordbox_xml():
    info = analyze_rekordbox_xml(sample_bytes())
    assert info['valid'] is True
    assert info['collection_count'] > 0


def test_sync_preserves_collection_and_adds_playlist():
    original = sample_bytes()
    collection, _ = parse_rekordbox_xml(original)
    set_df = collection.head(2).copy()
    set_df['order'] = [1, 2]
    before = len(ET.fromstring(original).findall('.//COLLECTION/TRACK'))
    updated = sync_rekordbox_xml(original, set_df, 'Patch 06 Test')
    root = ET.fromstring(updated)
    after = len(root.findall('.//COLLECTION/TRACK'))
    assert before == after
    playlists = [n for n in root.findall(".//PLAYLISTS//NODE[@Type='1']") if n.attrib.get('Name') == 'Patch 06 Test']
    assert len(playlists) == 1
    assert len(playlists[0].findall('TRACK')) == 2


def test_sync_assessment_marks_unknown_track():
    original = sample_bytes()
    unknown = pd.DataFrame([{'order': 1, 'track_id': '99999999', 'title': 'Unknown', 'artist': 'Nobody', 'location': ''}])
    result = assess_rekordbox_sync(original, unknown)
    assert result.iloc[0]['status'] == 'NOT IN LIBRARY'
