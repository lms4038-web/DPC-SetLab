from spotify_client import search_manual_tracks


class FakeAPI:
    def search_discovery_tracks(self, query, limit=10, offset=0):
        assert query == "Original Mix Artist"
        return [{
            "name": "Original Mix",
            "artists": [{"name": "Artist"}],
            "album": {"name": "Single"},
            "duration_ms": 245000,
            "uri": "spotify:track:abc",
            "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
        }]


def test_manual_search_returns_selectable_result():
    result = search_manual_tracks(FakeAPI(), "Original Mix Artist")
    assert len(result) == 1
    assert result.iloc[0]["title"] == "Original Mix"
    assert result.iloc[0]["duration"] == "4:05"
    assert result.iloc[0]["spotify_uri"] == "spotify:track:abc"
