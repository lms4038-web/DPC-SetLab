# Changelog

## v3.2.0 — Performance Planner 2.0

- Rekordbox Cue 이름에서 Intro, Build, Break, Drop, Outro 구조를 인식하는 `Song Structure Engine` 추가
- 오프닝·웜업·빌드·브리지·피크·클로징 역할에 따라 선호 구조 구간을 다르게 선택
- Cue 간격이 너무 넓을 때 곡 전체를 사용하던 문제 방지
- 구조 Cue가 부족하면 기존 BPM·마디 기반 추정으로 자동 전환
- 구조 분석 출처와 신뢰도를 곡별 상세 화면에 표시
- 구조 선택 및 과도한 재생시간 방지 테스트 추가

## v3.1.0 — OAuth Stable

- Streamlit Cloud용 Spotify PKCE OAuth 안정화
- 서명된 OAuth state와 만료 검증 추가
