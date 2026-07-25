from unittest.mock import patch

import pytest

from spotify_client import build_web_authorization, verify_web_state, verify_web_state_details


CLIENT_ID = "abc123client"
REDIRECT = "https://dpc-setlab.streamlit.app"
SECRET = "this-is-a-long-test-secret-value-12345"


def _state_from_url(url: str) -> str:
    from urllib.parse import parse_qs, urlparse
    return parse_qs(urlparse(url).query)["state"][0]


def test_signed_state_survives_without_session_state():
    flow = build_web_authorization(CLIENT_ID, REDIRECT, SECRET)
    verifier = verify_web_state(_state_from_url(flow["url"]), CLIENT_ID, REDIRECT, SECRET)
    assert len(verifier) >= 43


def test_state_rejects_tampering():
    flow = build_web_authorization(CLIENT_ID, REDIRECT, SECRET)
    state = _state_from_url(flow["url"])
    tampered = state[:-1] + ("A" if state[-1] != "A" else "B")
    with pytest.raises(ValueError):
        verify_web_state(tampered, CLIENT_ID, REDIRECT, SECRET)


def test_state_rejects_wrong_redirect():
    flow = build_web_authorization(CLIENT_ID, REDIRECT, SECRET)
    with pytest.raises(ValueError):
        verify_web_state(_state_from_url(flow["url"]), CLIENT_ID, REDIRECT + "/", SECRET)


def test_state_expires():
    with patch("spotify_client.time.time", return_value=1000):
        flow = build_web_authorization(CLIENT_ID, REDIRECT, SECRET)
    with patch("spotify_client.time.time", return_value=2000):
        with pytest.raises(ValueError):
            verify_web_state(_state_from_url(flow["url"]), CLIENT_ID, REDIRECT, SECRET, max_age_sec=600)


def test_signed_state_preserves_browser_session_id():
    session_id = "a" * 32
    flow = build_web_authorization(CLIENT_ID, REDIRECT, SECRET, session_id=session_id)
    details = verify_web_state_details(_state_from_url(flow["url"]), CLIENT_ID, REDIRECT, SECRET)
    assert details["sid"] == session_id
