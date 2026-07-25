# v5.0.1 Wizard Hotfix

- Fixed v5 Wizard CSS being rendered as visible source text.
- Spotify hosted OAuth now opens in the current tab instead of a new tab.
- After Spotify callback, onboarding automatically enters the workspace and requests Library.
- Restored styled workflow progress and wizard cards.
- Hardened automatic top-tab navigation for Library/Candidates/Generate/Edit/Export.

## 5.0.0 · Wizard Experience

- Home을 단계 안내 전용 Wizard 화면으로 단순화
- Spotify → Library → Candidates → Generate → Edit → Export 6단계 진행 표시
- Home의 불필요한 통계, 시스템 상태, Quick Start, 연결 해제·초기화 UI 제거
- 현재 단계에 맞춰 `LIBRARY 열기`, `CANDIDATES 열기`, `GENERATE 열기`, `EDIT 열기`, `EXPORT 열기` 버튼 제공
- 상단 탭은 유지해 사용자가 언제든 원하는 단계로 직접 이동 가능
- AI 기능을 제품의 핵심 가치로 유지하고 Wizard는 초보 사용자의 접근성을 지원

# Changelog

## 4.0.8-dev · Sprint 2 · Patch 08

### First-run Landing / Information Architecture Reset

- Added a true isolated landing page before the workspace loads.
- The first screen no longer renders the sidebar, navigation tabs, dashboard cards, analytics, or system checks.
- Added a single primary `시작하기` action and a secondary `기존 작업 공간 열기` action.
- Added Spotify-first onboarding directly on the landing flow.
- Added a `Spotify 없이 둘러보기` path for Rekordbox-only evaluation.
- Added a five-step visual path: Spotify → Library → Generate → Edit → Export.
- Added `첫 시작 화면 다시 보기` in Settings.
- Preserved the existing Patch 07 workspace and all Patch 06 XML Sync/backup/health-check behavior.

### Validation

- Python syntax compilation passed.
- Existing automated tests: 23 passed.

## 4.0.7-dev · Sprint 2 · Patch 07

### UX Overhaul
- Home을 Spotify-first 온보딩 화면으로 개편
- Spotify → XML → Generate → Edit → Export 5단계 Quick Start 적용
- Rekordbox XML 생성 가이드를 Library 업로드 위치로 이동
- Planner를 Generate와 Edit 흐름으로 분리
- Set Editor와 공연 전 검토 체크리스트 추가
- Help Center와 Rekordbox 후속 절차 문구 정리
- 버전·Sprint 표기와 Home 상태 추적 갱신

## 4.0.6-dev — Sprint 1B Patch 06

- Added Rekordbox XML Sync that preserves the uploaded Collection and existing playlists.
- Added XML Health Check, original XML backup download, and missing-track report.
- Added READY / NOT IN LIBRARY / PATH MISSING validation.
- Added an in-app Rekordbox export/import tutorial and six-step setup checklist.
- Kept M3U8 export as a universal local-playlist option.

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
## 4.0.7 Home Fix
- HOME을 기존 세션 대시보드가 아닌 전용 시작 화면으로 재구성
- 현재 진행 상황을 Spotify / Rekordbox XML / AI Set / Edit / Export 5단계로 표시
- 첫 사용자용 대형 `시작하기` 버튼과 단계별 Quick Start 안내 추가
- 시작 전에는 Spotify 설정 영역을 숨겨 첫 화면의 정보 밀도를 낮춤

## 4.0.9-dev · Sprint 2 · Patch 09
- Fixed raw HTML appearing in the Home progress list.
- Spotify OAuth completion now advances directly to Library.
- Added guided tab transitions: Library → Candidates → Generate → Edit.
- Candidate save advances to Candidates in wizard mode.
- Generate completion advances to Edit in wizard mode.
- Added a Candidates → Generate continuation action.
