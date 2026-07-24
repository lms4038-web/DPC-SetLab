## 4.0.5-dev — Sprint 1A Patch 05

- EXPORT CENTER에 Rekordbox Playlist 내보내기 추가
- 현재 세트 순서를 유지하는 Rekordbox XML 생성 및 다운로드
- 범용 로컬 플레이리스트 M3U8 생성 및 다운로드
- 다운로드 전 READY, PATH MISSING, STREAMING ONLY 상태 검사
- 누락되는 곡 목록과 원인 표시
- XML과 M3U8 용도 및 가져오기 방법 안내 추가

## 4.0.4-dev — Sprint 1A Patch 04

- Spotify 자동 매칭 오류를 사용자가 직접 검색하고 정확한 곡으로 교체하는 Manual Rematch 기능 추가
- 직접 교체한 곡은 신뢰도 1.0, 상태 `직접 수정`, 플레이리스트 포함 상태로 저장
- 부족 시간 보충용 Spotify 장르 검색을 텍스트 입력에서 다중 선택 버튼으로 변경
- 수동 Spotify 검색 결과에 아티스트, 앨범, 길이, 확인 링크 표시

## 4.0.3-dev — Sprint 1A Patch 03
- Current Set preview now displays the full set in a scrollable table instead of only six tracks.
- Added a Spotify Set Player to the left sidebar.
  - Before export: audition matched set tracks one at a time.
  - After playlist export: play the full exported playlist in sequence.
- Moved Spotify, Last.fm and Redirect URI connection controls into Settings.
- Sidebar now focuses on session information and playback.

## 4.0.2-dev — Sprint 1A Patch 02

- 상단 메뉴와 Session Workflow 이름 통일
- Start a session을 동적 Session Guide로 교체
- 현재 단계, 진행률, 다음 행동, 체크리스트 표시
- DJ 프로필, 세션 스냅샷, 연결 상태를 포함한 제품형 사이드바 적용
- Windows safe-area 및 기존 OAuth 기능 유지

# Changelog

## 4.0.1-dev · Sprint 1A Patch 01

- Windows의 Streamlit Share/Settings 상단 바와 탭이 겹치는 문제 수정
- OS와 브라우저 높이에 대응하는 상단 Safe Area 추가
- 탭 내비게이션을 sticky control deck 형태로 변경
- 탭 명칭을 DJ 워크플로 중심으로 재정리
- Home Hero에 퍼포먼스 커브를 연상시키는 레이어 효과 추가
- 작은 화면에서 탭이 가로 스크롤되도록 반응형 처리

## 4.0.0-dev · Sprint 1A

- Added the ORCHESTRA shared design system.
- Added a new DJ-product-style Home dashboard.
- Added live session status cards and workflow position detection.
- Split UI code into reusable `ui/` modules.
- Preserved all 3.2 planner, metadata, Spotify OAuth, and history features.
- Updated app branding and version labels for the 4.0 development line.

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