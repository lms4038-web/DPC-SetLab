# Changelog

## 3.1.0 — OAuth Stable

- Streamlit Cloud에서 외부 로그인 후 새 세션이 열려도 Spotify PKCE 인증이 유지되도록 변경
- `st.session_state`에 의존하던 OAuth state/verifier 저장 제거
- HMAC 서명된 self-contained OAuth state 도입
- OAuth 요청 10분 만료 및 Client ID/Redirect URI 바인딩 추가
- Streamlit Secrets의 `[app].oauth_state_secret` 지원
- OAuth state 변조·만료·Redirect URI 불일치 테스트 추가
- 앱 버전 표기를 3.1.0으로 변경
