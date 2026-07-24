# DPC SetLab 3.0 Streamlit 배포

Streamlit Cloud의 App settings → Secrets에 다음을 입력합니다.

```toml
[spotify]
client_id = "YOUR_SPOTIFY_CLIENT_ID"
redirect_uri = "https://dpc-setlab.streamlit.app"

[lastfm]
api_key = "YOUR_LASTFM_API_KEY"

[discogs]
token = "OPTIONAL"
```

Spotify Developer Dashboard의 Redirect URIs에는 아래 두 주소를 모두 유지합니다.

- `https://dpc-setlab.streamlit.app`
- `http://127.0.0.1:8888/callback`

웹에서는 PKCE 토큰을 브라우저 세션에만 보관합니다. 로컬에서는 기존 `.spotify_token.json`을 사용합니다.
