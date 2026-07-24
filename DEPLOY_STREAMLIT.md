# Streamlit Cloud 배포 설정

Streamlit 앱의 **Manage app → Settings → Secrets**에 아래 형식으로 입력합니다.

```toml
[spotify]
client_id = "SPOTIFY_DEVELOPER_DASHBOARD_CLIENT_ID"
redirect_uri = "https://dpc-setlab.streamlit.app"

[app]
oauth_state_secret = "24자 이상의 충분히 긴 임의 문자열"

[lastfm]
api_key = "LASTFM_API_KEY"

[discogs]
token = ""
```

`oauth_state_secret`은 Spotify Client Secret이 아닙니다. OAuth 요청의 state 값을 서명하는 DPC SetLab 전용 문자열입니다. 외부에 공개하거나 GitHub에 올리지 말고 Streamlit Secrets에만 저장하세요.

간단한 예시 형식:

```toml
[app]
oauth_state_secret = "dpc-setlab-2026-my-private-random-key-83"
```

Spotify Developer Dashboard의 Redirect URI에는 아래 주소를 정확히 등록합니다.

```text
https://dpc-setlab.streamlit.app
```

설정 저장 후 Streamlit 앱을 Reboot하고, 앱에서 `저장된 Spotify 로그인 삭제`를 누른 뒤 다시 연결합니다.
