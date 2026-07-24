# Changelog

## 2.2.0 - Playlist Intelligence
- Added nested Rekordbox playlist selection.
- Added playlist metrics and Camelot/genre distributions.
- Added target-duration readiness score and explainable diagnosis.
- Isolated candidate state when switching playlists.
- Added unit tests for playlist summary and diagnosis.

## v2.3.0 — AI Performance Planner
- Rekordbox XML `POSITION_MARK` Hot Cue/Memory Cue 파싱
- 곡 역할별 가변 재생시간 배분
- 8·16·32마디 프레이즈 단위 Mix In/Out 계획
- 믹싱 중첩을 반영한 실제 세트시간 계산
- 목표 공연시간에 맞춘 프레이즈 단위 오차 보정
- Cue 기반/추정 기반 구조 출처와 신뢰도 표시

## v2.3.1 — Performance Duration Fix
- 곡당 평균 사용시간을 세트 선곡 수 계산에 반영
- 목표시간 보정이 곡을 전체 길이까지 늘리던 문제 수정
- 역할별 목표시간과 사용자 허용 오차를 곡별 상한/하한으로 적용
- 후보곡이 부족하면 곡을 강제로 늘리지 않고 부족 시간과 권장 추가 곡 수 표시
- 회귀 테스트 추가

## v2.3.2 — Used Segment Display
- 곡 내부의 사용 시작, 다음 곡 투입, 사용 종료 시각을 읽기 쉬운 형식으로 표시
- 핵심 재생 구간과 전환 구간을 분리 표시
- 전체 세트 타임라인의 진입, 믹스 시작, 이탈 시각 추가
- 곡별 상세 구간 펼쳐보기 UI 추가
- CSV에 사람이 읽는 시간값과 원시 초 단위 값을 함께 포함
- 사용 구간 회귀 테스트 추가

## v2.4.0 — Settings & UX
- Spotify Client ID, Last.fm API Key, Discogs Token을 `config/settings.json`에 한 번 저장하고 자동 불러오기
- 기존 `config.json` 설정 자동 마이그레이션
- 환경변수 및 Streamlit Cloud Secrets 지원
- 별도 Settings 탭과 연결 상태 대시보드 추가
- Spotify 저장 로그인 자동 확인 및 연결 테스트 추가
- Last.fm API Key 유효성 검사 추가
- 민감한 로컬 설정 파일 Git 제외

## 3.0.0
- Streamlit Cloud용 Spotify Authorization Code + PKCE 지원
- 웹/로컬 Redirect URI 자동 분기
- 웹 토큰을 Streamlit session_state에 저장
- Streamlit Secrets의 redirect_uri 지원
- 설정 화면과 진단 정보 v3.0 업데이트
