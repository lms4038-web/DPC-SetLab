# DPC SetLab 2.2

> DJ의 판단을 대신하지 않고, 더 빠르고 더 좋은 세트 준비를 돕는 AI 워크스페이스입니다.

## v2.3.1 핵심 기능

- Rekordbox 전체 XML에서 폴더·플레이리스트 선택
- 선택 플레이리스트의 곡 수, 총 길이, BPM, Energy, Camelot, 장르 분석
- 목표 공연 시간 대비 Playlist Intelligence 진단
- 선택한 플레이리스트만 AI 세트 후보로 격리
- 기존 Spotify 보충, 온라인 보강, AI Coach 및 History 기능 유지

# DPC SetLab 2.1 Hybrid

Rekordbox 분석값과 온라인 음악 메타데이터를 결합하는 하이브리드 DJ 세트 준비 도구입니다.

## 핵심 원칙

- BPM, Key, Camelot, 길이, 에너지: Rekordbox/사용자 입력 우선
- 장르 태그, 유사 아티스트, 발매연도, 인기도: 온라인 보조 정보
- 인터넷 또는 외부 API가 실패해도 기존 세트 생성은 정상 작동
- 온라인 조회 결과는 `online_metadata_cache.json`에 로컬 저장

## 온라인 데이터 소스

- MusicBrainz: API 키 없이 발매 및 식별 정보 조회
- Last.fm: API 키 필요. 태그, 청취 지표, 유사 아티스트
- Spotify: 기존 Spotify 로그인 사용. 인기도, 앨범, 발매일
- Discogs: 선택 기능. 개인 토큰 필요. 스타일, 레이블, 국가

## 실행

Windows: `START_WINDOWS.bat`

macOS: `START_DPC_SET_BUILDER.command`

## 권장 순서

1. Rekordbox XML/CSV 불러오기
2. 후보곡 저장
3. 온라인 보강 실행
4. 공연 상황과 프리셋 선택
5. AI 1차 세트 생성
6. 부족하면 Spotify 보충
7. Rekordbox Analyze 후 XML 재수입
8. AI Final 세트 생성


## v2.3 AI Performance Planner
- 평균 곡 사용시간과 허용 오차 설정
- 곡 역할별 가변 시간 배분
- Cue 우선, BPM 추정 보조
- 8/16/32마디 단위 Mix In/Out
- 목표 세트시간 자동 보정

## v2.3.2 사용 구간 표시
AI Performance Planner 결과에서 각 곡의 실제 사용 범위를 확인할 수 있습니다.

- 사용 구간: 곡 파일 내부에서 재생하는 시작과 종료 위치
- 다음 곡 투입: 다음 트랙의 믹스를 시작할 위치
- 핵심 재생: 단독 또는 중심적으로 들려주는 부분
- 전환 구간: 다음 곡과 겹쳐 믹싱하는 부분
- 세트 타임라인: 전체 공연에서 해당 곡이 들어오고 빠지는 예상 시각

표 아래의 `곡별 사용 구간 상세 보기`를 펼치면 모든 값을 곡별로 확인할 수 있습니다.

## v2.4 설정 저장
로컬 앱에서는 `⚙️ 설정` 탭에서 Spotify Client ID와 Last.fm API Key를 한 번 저장하면 이후 자동으로 불러옵니다. 실제 값은 `config/settings.json`에 저장되며 `.gitignore`로 GitHub 업로드에서 제외됩니다.

Streamlit Community Cloud에서는 앱의 **Settings → Secrets**에 다음 형식으로 저장하세요.

```toml
[spotify]
client_id = "YOUR_CLIENT_ID"

[lastfm]
api_key = "YOUR_LASTFM_API_KEY"
```

Spotify 로그인 토큰은 로컬 PKCE 콜백(`http://127.0.0.1:8888/callback`)을 사용하므로 현재 버전의 Spotify 로그인/플레이리스트 생성 기능은 로컬 실행을 권장합니다. 온라인 앱에서는 Last.fm 분석과 저장된 Secret 자동 불러오기를 사용할 수 있습니다.
