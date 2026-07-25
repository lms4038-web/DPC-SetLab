from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from dpc_core import (
    BuildSettings, ROLE_OPTIONS, ROLE_NORMAL, ROLE_START, ROLE_END, build_set, curve_value, export_set_csv, export_rekordbox_xml, export_m3u8, assess_rekordbox_export, filter_playlist,
    analyze_rekordbox_xml, assess_rekordbox_sync, sync_rekordbox_xml,
    finalize_dataframe, format_seconds, parse_csv, parse_rekordbox_xml,
)
from dpc_insights import (
    VENUE_PRESETS, AUDIENCE_PRESETS, MOOD_PRESETS, apply_context, explain_set,
    recommend_next_tracks, analyze_history, save_style_profile, load_style_profile, make_html_report,
)
from online_metadata import enrich_dataframe, test_lastfm_connection
from playlist_intelligence import diagnose_playlist, display_playlist_path, playlist_options, playlist_summary
from performance_planner import PerformancePlanSettings, apply_performance_plan
from settings_manager import load_settings, save_settings
from ui.design_system import apply_design_system
from ui.home import render_first_run_landing, render_home
from ui.sidebar import render_session_snapshot, render_set_player, render_sidebar_footer, render_sidebar_header

from spotify_client import (
    api_from_token, authorize, build_web_authorization, discover_fill_tracks,
    exchange_web_code, get_valid_token, get_valid_token_data, match_set, search_manual_tracks, verify_web_state,
    reset_token, test_spotify_connection,
)



TAB_LABELS = {
    "home": "HOME",
    "library": "LIBRARY",
    "candidates": "CANDIDATES",
    "generate": "GENERATE",
    "edit": "EDIT",
    "export": "EXPORT",
}

def request_tab(target: str) -> None:
    st.session_state["wizard_target_tab"] = target

def apply_requested_tab() -> None:
    target = st.session_state.pop("wizard_target_tab", None)
    if not target:
        return
    label = TAB_LABELS.get(target, target).upper()
    components.html(
        f"""<script>
        const wanted = {label!r};
        const clickTarget = () => {{
          const doc = window.parent.document;
          const tabs = [...doc.querySelectorAll('button[data-baseweb="tab"]')];
          const match = tabs.find(el => (el.innerText || '').toUpperCase().includes(wanted));
          if (match) {{ match.click(); match.scrollIntoView({{block:'nearest', inline:'center'}}); return true; }}
          return false;
        }};
        if (!clickTarget()) {{ setTimeout(clickTarget, 120); setTimeout(clickTarget, 450); }}
        </script>""",
        height=0,
    )

SAMPLE_XML = Path("samples/sample_rekordbox.xml")
SAMPLE_CSV = Path("samples/sample_tracks.csv")

PRESET_CONFIGS = {
    "warmup_peak": {
        "label": "🌅 웜업 → 피크",
        "description": "여유 있게 시작해 중후반에 가장 강하게 올리고, 마지막은 살짝 숨을 고릅니다.",
        "curve": "중후반 피크", "start_energy": 2.5, "peak_energy": 8.5, "end_energy": 6.5,
        "max_bpm_step": 3.0, "harmonic_weight": 0.80, "energy_weight": 0.75, "bpm_weight": 0.75, "artist_gap": 3,
        "summary": "낮게 시작 · 중후반 피크 · 부드러운 착지",
    },
    "classic_build": {
        "label": "🚀 정석 빌드업",
        "description": "처음부터 끝까지 꾸준히 상승하는 가장 무난한 클럽 세트 전개입니다.",
        "curve": "꾸준히 상승", "start_energy": 3.5, "peak_energy": 9.0, "end_energy": 9.0,
        "max_bpm_step": 4.0, "harmonic_weight": 0.68, "energy_weight": 0.80, "bpm_weight": 0.80, "artist_gap": 3,
        "summary": "꾸준한 상승 · 안정적인 BPM · 정석 전개",
    },
    "peak_time": {
        "label": "🔥 피크타임",
        "description": "초반부터 강하게 밀어붙이고 높은 에너지를 유지하는 메인 타임용 전개입니다.",
        "curve": "초반 피크", "start_energy": 7.0, "peak_energy": 10.0, "end_energy": 8.2,
        "max_bpm_step": 5.0, "harmonic_weight": 0.60, "energy_weight": 0.88, "bpm_weight": 0.72, "artist_gap": 2,
        "summary": "빠른 점화 · 최고조 유지 · 강한 마무리",
    },
    "wave": {
        "label": "🌊 파도형",
        "description": "긴장과 이완을 반복해 지루하지 않게 흐르는 변화가 많은 전개입니다.",
        "curve": "파도형", "start_energy": 4.5, "peak_energy": 9.2, "end_energy": 6.5,
        "max_bpm_step": 4.5, "harmonic_weight": 0.72, "energy_weight": 0.90, "bpm_weight": 0.62, "artist_gap": 3,
        "summary": "상승과 이완 반복 · 변화감 · 긴 세트에 적합",
    },
    "high_hold": {
        "label": "⚡ 고강도 유지",
        "description": "처음부터 끝까지 높은 에너지를 유지하는 짧고 집중적인 파티 세트입니다.",
        "curve": "일정하게", "start_energy": 8.5, "peak_energy": 8.8, "end_energy": 8.5,
        "max_bpm_step": 4.0, "harmonic_weight": 0.64, "energy_weight": 0.92, "bpm_weight": 0.68, "artist_gap": 2,
        "summary": "높은 에너지 유지 · 짧은 피크 세트 · 쉬는 구간 최소",
    },
    "closing": {
        "label": "🌙 피크 후 마무리",
        "description": "중후반에 가장 크게 터뜨린 뒤 마지막 구간에서 감정을 정리하며 내려옵니다.",
        "curve": "중후반 피크", "start_energy": 4.0, "peak_energy": 9.5, "end_energy": 3.5,
        "max_bpm_step": 3.5, "harmonic_weight": 0.78, "energy_weight": 0.82, "bpm_weight": 0.68, "artist_gap": 3,
        "summary": "중후반 절정 · 명확한 엔딩 · 감정적인 마무리",
    },
    "custom": {
        "label": "🎛️ 직접 설정",
        "description": "프리셋 없이 에너지, BPM, 화성 믹싱 비중을 직접 조절합니다.",
        "curve": "중후반 피크", "start_energy": 3.0, "peak_energy": 9.0, "end_energy": 7.0,
        "max_bpm_step": 4.0, "harmonic_weight": 0.65, "energy_weight": 0.65, "bpm_weight": 0.75, "artist_gap": 3,
        "summary": "모든 값을 직접 조정",
    },
}

st.set_page_config(page_title="DPC SetLab 4.0.9-dev", page_icon="◈", layout="wide")
apply_design_system()


def load_uploaded(name: str, data: bytes):
    if name.lower().endswith(".xml"):
        collection, playlists = parse_rekordbox_xml(data)
        st.session_state["raw_collection"] = collection
        st.session_state["playlists"] = playlists
        st.session_state["source_type"] = "xml"
        st.session_state["rekordbox_xml_bytes"] = data
        st.session_state["rekordbox_xml_name"] = name
        st.session_state["rekordbox_xml_health"] = analyze_rekordbox_xml(data)
    elif name.lower().endswith(".csv"):
        collection = parse_csv(data)
        st.session_state["raw_collection"] = collection
        st.session_state["playlists"] = {}
        st.session_state["source_type"] = "csv"
        st.session_state.pop("rekordbox_xml_bytes", None)
        st.session_state.pop("rekordbox_xml_name", None)
        st.session_state.pop("rekordbox_xml_health", None)
    else:
        raise ValueError("XML 또는 CSV 파일만 지원합니다.")
    st.session_state.pop("candidate_df", None)
    st.session_state.pop("candidate_source_playlist", None)
    st.session_state.pop("candidate_selection_signature", None)
    st.session_state.pop("set_df", None)
    st.session_state.pop("spotify_matches", None)


settings = load_settings(getattr(st, "secrets", None))


client_id = str(settings.get("spotify", {}).get("client_id", "")).strip()
redirect_uri = str(settings.get("spotify", {}).get("redirect_uri", "http://127.0.0.1:8888/callback")).strip()
oauth_state_secret = str(settings.get("app", {}).get("oauth_state_secret", "")).strip()
is_web_spotify = redirect_uri.lower().startswith("https://")
lastfm_api_key = str(settings.get("lastfm", {}).get("api_key", "")).strip()
discogs_token = str(settings.get("discogs", {}).get("token", "")).strip()
default_playlist_name = str(settings.get("preferences", {}).get("playlist_name", "DPC DJ Set"))
default_public = bool(settings.get("preferences", {}).get("public_playlist", False))
auto_connect = bool(settings.get("preferences", {}).get("auto_connect", True))

# Spotify hosted OAuth callback processing. Web tokens stay in this browser session;
# local tokens continue to use .spotify_token.json on the user's computer.
if is_web_spotify and client_id:
    oauth_error = st.query_params.get("error")
    oauth_code = st.query_params.get("code")
    oauth_state = st.query_params.get("state")
    if oauth_error:
        st.error(f"Spotify 승인이 취소되었거나 실패했습니다: {oauth_error}")
        st.query_params.clear()
    elif oauth_code:
        try:
            verifier = verify_web_state(
                str(oauth_state or ""), client_id, redirect_uri, oauth_state_secret
            )
            st.session_state["spotify_web_token"] = exchange_web_code(
                client_id, redirect_uri, str(oauth_code), verifier
            )
            st.query_params.clear()
            st.success("Spotify 연결이 완료되었습니다.")
            st.rerun()
        except Exception as exc:
            st.query_params.clear()
            st.error(f"Spotify 로그인 처리 실패: {exc}")


def current_spotify_token():
    if not client_id:
        return None
    if is_web_spotify:
        refreshed = get_valid_token_data(client_id, st.session_state.get("spotify_web_token"))
        if refreshed:
            st.session_state["spotify_web_token"] = refreshed
        else:
            st.session_state.pop("spotify_web_token", None)
        return refreshed
    return get_valid_token(client_id)


def require_spotify_token():
    active = current_spotify_token()
    if active:
        return active
    if is_web_spotify:
        raise RuntimeError("먼저 왼쪽의 ‘Spotify 연결’ 버튼으로 로그인해주세요.")
    return authorize(client_id)


token = current_spotify_token()

if is_web_spotify and client_id and not token and oauth_state_secret:
    st.session_state["spotify_oauth_url"] = build_web_authorization(
        client_id, redirect_uri, oauth_state_secret
    )["url"]

# Patch 08: true first-run experience. Until the user enters the workspace,
# no sidebar, tab bar, dashboard cards, or advanced modules are rendered.
workspace_entered = bool(st.session_state.get("workspace_entered", False))
if not workspace_entered:
    render_first_run_landing(spotify_connected=bool(token))

    if not st.session_state.get("landing_started", False):
        c1, c2 = st.columns([1.35, 1])
        with c1:
            if st.button("시작하기", type="primary", use_container_width=True, key="landing_start"):
                st.session_state["landing_started"] = True
                st.rerun()
        with c2:
            if st.button("기존 작업 공간 열기", use_container_width=True, key="landing_skip"):
                st.session_state["workspace_entered"] = True
                st.session_state["home_wizard_started"] = True
                st.rerun()
        st.caption("처음 사용한다면 ‘시작하기’를 눌러 Spotify 연결부터 진행하세요.")
        st.stop()

    # Spotify OAuth가 끝났다면 중간 진행표를 보여주지 않고 Library로 바로 이동합니다.
    if token:
        st.session_state["workspace_entered"] = True
        st.session_state["home_wizard_started"] = True
        st.session_state["wizard_mode"] = True
        request_tab("library")
        st.rerun()

    st.markdown('<div class="dpc-onboarding-stage">', unsafe_allow_html=True)
    st.markdown("#### STEP 1 · Spotify 연결")
    st.caption("음악 검색과 Export를 위해 Spotify를 먼저 연결합니다. Rekordbox 기능만 살펴보려면 건너뛸 수 있습니다.")

    if token:
        st.success("Spotify 연결이 완료되었습니다.")
    elif not client_id:
        st.warning("Spotify Client ID가 설정되지 않았습니다. 아래에서 빠르게 입력하거나 Spotify 없이 작업 공간을 열 수 있습니다.")
        with st.expander("Spotify 빠른 설정", expanded=True):
            quick_client_id = st.text_input("Spotify Client ID", value="", key="landing_client_id")
            quick_redirect = st.text_input("Redirect URI", value=redirect_uri, key="landing_redirect_uri")
            if st.button("설정 저장", use_container_width=True, key="landing_save_spotify"):
                settings.setdefault("spotify", {})["client_id"] = quick_client_id.strip()
                settings["spotify"]["redirect_uri"] = quick_redirect.strip()
                save_settings(settings)
                st.success("저장했습니다. 앱을 새로고침하면 연결 버튼이 활성화됩니다.")
    elif is_web_spotify:
        oauth_url = st.session_state.get("spotify_oauth_url")
        if oauth_url:
            st.link_button("Spotify 계정 연결", oauth_url, type="primary", use_container_width=True)
        else:
            st.warning("OAuth State Secret을 Settings 또는 Streamlit Secrets에 설정해야 합니다.")
    else:
        if st.button("Spotify 계정 연결", type="primary", use_container_width=True, key="landing_spotify_connect"):
            try:
                with st.spinner("브라우저에서 Spotify 접근을 승인해주세요."):
                    authorize(client_id)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    n1, n2 = st.columns([1.35, 1])
    with n1:
        if st.button("다음 · Rekordbox XML", type="primary", use_container_width=True, disabled=not bool(token), key="landing_continue"):
            st.session_state["workspace_entered"] = True
            st.session_state["home_wizard_started"] = True
            st.session_state["wizard_mode"] = True
            request_tab("library")
            st.rerun()
    with n2:
        if st.button("Spotify 없이 둘러보기", use_container_width=True, key="landing_continue_without_spotify"):
            st.session_state["workspace_entered"] = True
            st.session_state["home_wizard_started"] = True
            st.session_state["wizard_mode"] = True
            request_tab("library")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

with st.sidebar:
    render_sidebar_header()
    render_session_snapshot()
    render_set_player()
    render_sidebar_footer()

home_tab, load_tab, online_tab, build_tab, edit_tab, spotify_tab, coach_tab, history_tab, settings_tab, guide_tab = st.tabs([
    "⌂ HOME", "♫ LIBRARY", "✦ CANDIDATES", "＋ GENERATE", "✎ EDIT", "⇧ EXPORT", "AI ASSISTANT", "▥ ANALYTICS", "⚙ SETTINGS", "? HELP"
])
apply_requested_tab()

with home_tab:
    render_home(
        spotify_connected=bool(token),
        lastfm_configured=bool(lastfm_api_key),
        xml_loaded=isinstance(st.session_state.get("raw_collection"), pd.DataFrame),
        set_ready=isinstance(st.session_state.get("set_df"), pd.DataFrame),
    )

    if st.session_state.get("home_wizard_started", False) or bool(token):
        st.markdown("### 1. Spotify 연결")
        if token:
            st.success("Spotify가 연결되어 있습니다. 다음으로 LIBRARY에서 Rekordbox XML을 불러오세요.")
            if st.button("Spotify 연결 해제", key="home_spotify_disconnect", use_container_width=True):
                if is_web_spotify:
                    st.session_state.pop("spotify_web_token", None)
                else:
                    reset_token()
                st.rerun()
        elif not client_id:
            st.warning("Spotify Client ID가 없습니다. SETTINGS에서 Client ID를 저장한 뒤 HOME으로 돌아오세요.")
        elif is_web_spotify:
            oauth_url = st.session_state.get("spotify_oauth_url")
            if oauth_url:
                st.link_button("Spotify 연결", oauth_url, type="primary", use_container_width=True)
            else:
                st.warning("OAuth State Secret을 SETTINGS 또는 Streamlit Secrets에 설정해주세요.")
        else:
            if st.button("Spotify 연결", type="primary", key="home_spotify_connect", use_container_width=True):
                try:
                    with st.spinner("브라우저에서 Spotify 접근을 승인해주세요."):
                        authorize(client_id)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        q1, q2 = st.columns(2)
        with q1:
            if st.button("다음 단계 · LIBRARY", use_container_width=True, disabled=not bool(token)):
                st.session_state["wizard_mode"] = True
                request_tab("library")
                st.rerun()
        with q2:
            if st.button("처음부터 다시 안내", use_container_width=True):
                st.session_state["show_first_run"] = True
                st.rerun()
with load_tab:
    st.subheader("Rekordbox 라이브러리 불러오기")
    st.caption("전체 Collection XML을 한 번 불러온 뒤, DPC SetLab 안에서 사용할 플레이리스트를 선택합니다.")
    with st.expander("❓ Rekordbox XML 만드는 방법", expanded=not bool(st.session_state.get("raw_collection"))):
        st.markdown("""
1. Rekordbox를 실행합니다.
2. 상단 메뉴에서 **File → Export Collection in xml format**을 선택합니다.
3. 찾기 쉬운 위치에 XML을 저장합니다.
4. 아래 업로드 영역에 XML을 끌어놓거나 **Browse files**를 누릅니다.

> DPC SetLab은 업로드한 XML의 Collection과 기존 Playlist를 보존하고, Export 단계에서 새 DPC SetLab Playlist를 추가합니다.
""")
        st.caption("CSV는 테스트와 간단한 후보곡 작업용이며, Rekordbox Sync와 XML Backup은 XML 업로드에서만 사용할 수 있습니다.")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        uploaded = st.file_uploader("Rekordbox XML 또는 CSV", type=["xml", "csv"], help="Rekordbox: File > Export Collection in xml format")
    with c2:
        if st.button("샘플 XML 열기", use_container_width=True):
            try:
                load_uploaded(SAMPLE_XML.name, SAMPLE_XML.read_bytes())
                st.success("샘플 XML을 불러왔습니다.")
            except Exception as exc:
                st.error(str(exc))
    with c3:
        if st.button("샘플 CSV 열기", use_container_width=True):
            try:
                load_uploaded(SAMPLE_CSV.name, SAMPLE_CSV.read_bytes())
                st.success("샘플 CSV를 불러왔습니다.")
            except Exception as exc:
                st.error(str(exc))
    if uploaded is not None:
        signature = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("upload_signature") != signature:
            try:
                load_uploaded(uploaded.name, uploaded.getvalue())
                st.session_state["upload_signature"] = signature
                st.success(f"{uploaded.name}을 불러왔습니다.")
            except Exception as exc:
                st.error(str(exc))

    if "raw_collection" in st.session_state:
        raw = st.session_state["raw_collection"]
        playlists = st.session_state.get("playlists", {})
        st.success(f"Collection {len(raw):,}곡 · 플레이리스트 {len(playlists):,}개를 확인했습니다.")
        health = st.session_state.get("rekordbox_xml_health")
        if health:
            st.markdown("#### XML Health Check")
            h1, h2, h3, h4 = st.columns(4)
            h1.metric("상태", "정상" if health.get("valid") else "확인 필요")
            h2.metric("Collection", f"{health.get('collection_count', 0):,}곡")
            h3.metric("Playlists", f"{health.get('playlist_count', 0):,}개")
            h4.metric("경로 누락", f"{health.get('missing_locations', 0):,}곡")
            if health.get("music_folder"):
                st.caption(f"대표 음악 폴더: `{health['music_folder']}`")
            for warning in health.get("warnings", []):
                st.warning(warning)

        left, right = st.columns([1, 2])
        with left:
            options = playlist_options(playlists) if playlists else ["전체 Collection"]
            selected_playlist = st.selectbox(
                "사용할 플레이리스트", options,
                format_func=display_playlist_path,
                key="selected_rekordbox_playlist",
                help="폴더 안 플레이리스트는 들여쓰기로 표시됩니다.",
            )
            target_for_diagnosis = st.number_input("진단 기준 공연 시간(분)", min_value=15, max_value=360, value=60, step=5)
        candidate = filter_playlist(raw, playlists, selected_playlist)
        summary = playlist_summary(candidate)
        diagnosis = diagnose_playlist(candidate, int(target_for_diagnosis))

        with right:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("후보곡", f"{summary['track_count']:,}곡")
            m2.metric("총 재생시간", format_seconds(summary["total_seconds"]))
            m3.metric("평균 BPM", f"{summary['avg_bpm']:.1f}" if summary['avg_bpm'] else "-")
            m4.metric("평균 Energy", f"{summary['avg_energy']:.1f}" if summary['avg_energy'] else "-")
            st.markdown(f"### Playlist Intelligence · {diagnosis.score}점 ({diagnosis.grade})")
            st.info(diagnosis.verdict)
            dc1, dc2 = st.columns(2)
            with dc1:
                st.markdown("**강점**")
                for text in diagnosis.strengths or ["분석 가능한 강점이 아직 충분하지 않습니다."]:
                    st.write(f"✓ {text}")
            with dc2:
                st.markdown("**보완 포인트**")
                for text in diagnosis.warnings or ["현재 기준에서 큰 보완점이 없습니다."]:
                    st.write(f"• {text}")

        d1, d2 = st.columns(2)
        with d1:
            st.markdown("**Camelot 분포**")
            if summary["camelot_counts"]:
                st.bar_chart(pd.Series(summary["camelot_counts"], name="곡 수"))
            else:
                st.caption("Camelot 정보가 없습니다.")
        with d2:
            st.markdown("**장르 분포**")
            if summary["genre_counts"]:
                st.bar_chart(pd.Series(summary["genre_counts"], name="곡 수"))
            else:
                st.caption("장르 정보가 없습니다.")

        st.info(f"선택한 플레이리스트에서 {len(candidate)}곡을 찾았습니다. 사용 여부와 역할, 에너지를 수정한 뒤 저장하세요.")
        show_cols = ["use", "role", "title", "artist", "bpm", "key", "camelot", "energy", "rating", "duration_sec", "genre", "comments"]
        with st.form("candidate_editor_form"):
            edited = st.data_editor(
                candidate[show_cols], use_container_width=True, height=480, hide_index=True,
                disabled=["title", "artist", "bpm", "key", "camelot", "rating", "duration_sec", "genre", "comments"],
                column_config={
                    "use": st.column_config.CheckboxColumn("사용"),
                    "role": st.column_config.SelectboxColumn("역할", options=ROLE_OPTIONS),
                    "title": "제목", "artist": "아티스트", "bpm": st.column_config.NumberColumn("BPM", format="%.1f"),
                    "key": "Key", "camelot": "Camelot", "energy": st.column_config.NumberColumn("에너지", min_value=1.0, max_value=10.0, step=0.5, format="%.1f"),
                    "rating": "별점", "duration_sec": "길이(초)", "genre": "장르", "comments": "코멘트",
                }, num_rows="fixed",
            )
            submitted = st.form_submit_button("이 플레이리스트를 후보곡으로 저장", use_container_width=True)
        selection_signature = f"{st.session_state.get('upload_signature', 'sample')}::{selected_playlist}"
        if submitted:
            updated = candidate.copy()
            for col in ["use", "role", "energy"]:
                updated[col] = edited[col].values
            st.session_state["candidate_df"] = finalize_dataframe(updated)
            st.session_state["candidate_source_playlist"] = selected_playlist
            st.session_state["candidate_selection_signature"] = selection_signature
            st.session_state.pop("set_df", None)
            st.session_state.pop("spotify_matches", None)
            st.success(f"{selected_playlist}에서 후보곡 {int(updated['use'].sum())}곡을 저장했습니다.")
            if st.session_state.get("wizard_mode"):
                request_tab("candidates")
                st.rerun()
        elif st.session_state.get("candidate_selection_signature") != selection_signature:
            st.session_state["candidate_df"] = candidate
            st.session_state["candidate_source_playlist"] = selected_playlist
            st.session_state["candidate_selection_signature"] = selection_signature
            st.session_state.pop("set_df", None)
            st.session_state.pop("spotify_matches", None)


with online_tab:
    st.subheader("온라인 메타데이터 보강")
    st.caption("Rekordbox의 BPM·Key·길이·에너지는 기준 데이터로 유지하고, 온라인 정보는 장르 태그·유사 아티스트·발매정보·인기도만 보조합니다.")
    candidates = st.session_state.get("candidate_df")
    if candidates is None or candidates.empty:
        st.info("먼저 1. 후보곡에서 Rekordbox XML 또는 CSV를 불러오고 후보곡을 저장하세요.")
    else:
        source_cols = st.columns(4)
        with source_cols[0]: use_mb = st.checkbox("MusicBrainz", value=True, help="발매연도, 국가, 레이블, 식별정보")
        with source_cols[1]: use_lfm = st.checkbox("Last.fm", value=bool(lastfm_api_key.strip()), disabled=not bool(lastfm_api_key.strip()), help="태그, 청취량, 유사 아티스트")
        with source_cols[2]: use_sp = st.checkbox("Spotify", value=bool(token), disabled=not bool(token), help="인기도, 앨범, 발매일, Spotify 링크")
        with source_cols[3]: use_dc = st.checkbox("Discogs", value=False, disabled=not bool(discogs_token.strip()), help="장르, 스타일, 레이블, 발매국가")
        only_used = st.checkbox("사용 체크된 곡만 보강", value=True)
        force = st.checkbox("캐시를 무시하고 다시 조회", value=False)
        base = candidates[candidates["use"]].copy() if only_used and "use" in candidates else candidates.copy()
        st.info(f"조회 대상: {len(base)}곡 · MusicBrainz를 사용하면 공개 API 제한 준수를 위해 곡당 약 1초 간격으로 조회합니다.")
        if st.button("온라인 정보 가져오기", type="primary", use_container_width=True, disabled=base.empty):
            api = None
            if use_sp and token:
                try: api = api_from_token(token)
                except Exception: api = None
            bar = st.progress(0.0)
            status = st.empty()
            def update_progress(pos, total, label):
                bar.progress(pos / max(1, total))
                status.caption(f"{pos}/{total} · {label}")
            try:
                enriched = enrich_dataframe(
                    base,
                    lastfm_api_key=lastfm_api_key.strip(), discogs_token=discogs_token.strip(), spotify_api=api,
                    use_musicbrainz=use_mb, use_lastfm=use_lfm, use_discogs=use_dc, use_spotify=use_sp,
                    force_refresh=force, progress_callback=update_progress,
                )
                merged = candidates.copy()
                for col in enriched.columns:
                    if col not in merged.columns:
                        merged[col] = None
                    merged.loc[enriched.index, col] = enriched[col]
                st.session_state["candidate_df"] = merged
                st.session_state["online_enriched_df"] = enriched
                status.empty(); bar.empty()
                st.success(f"{len(enriched)}곡의 온라인 보강을 완료했습니다. Rekordbox 분석값은 변경하지 않았습니다.")
            except Exception as exc:
                st.error(f"온라인 보강 중 오류: {exc}")
        enriched_view = st.session_state.get("online_enriched_df")
        if enriched_view is not None and not enriched_view.empty:
            view_cols = [c for c in ["title", "artist", "bpm", "camelot", "genre", "online_tags_text", "release_year", "spotify_popularity", "lastfm_listeners", "online_sources_text", "online_status"] if c in enriched_view.columns]
            st.dataframe(enriched_view[view_cols], use_container_width=True, hide_index=True)
            st.caption("온라인 태그는 장르 필터와 AI 코치의 보조 신호로 활용할 수 있으며, BPM·Key 충돌 시에는 Rekordbox 값이 항상 우선됩니다.")

        if st.session_state.get("wizard_mode"):
            st.markdown("---")
            if st.button("다음 · Generate", type="primary", use_container_width=True, key="wizard_candidates_next"):
                request_tab("generate")
                st.rerun()

with build_tab:
    st.subheader("세트 전개 설정")
    if "candidate_df" not in st.session_state:
        st.warning("먼저 ‘후보곡 불러오기’에서 곡을 불러오세요.")
    else:
        candidates = st.session_state["candidate_df"]
        usable_candidates = candidates[candidates["use"]].copy()

        st.markdown("### 장르 선택")
        genre_labels = usable_candidates["genre"].fillna("").astype(str).str.strip().replace("", "장르 미지정")
        genre_options = sorted(genre_labels.unique().tolist())
        selected_genres = st.multiselect(
            "이번 세트에 사용할 장르",
            genre_options,
            default=genre_options,
            help="Rekordbox의 Genre 값을 기준으로 후보곡을 좁힙니다. 여러 장르를 동시에 고를 수 있습니다.",
        )
        if selected_genres:
            usable_candidates = usable_candidates[genre_labels.isin(selected_genres)].copy()
            st.caption(f"선택한 장르의 후보곡: **{len(usable_candidates)}곡**")
        else:
            usable_candidates = usable_candidates.iloc[0:0].copy()
            st.warning("세트에 사용할 장르를 하나 이상 선택해주세요.")

        st.markdown("### 시작곡 · 마지막곡 고정")
        st.caption("지정하지 않으면 앱이 BPM·키·에너지 흐름에 맞춰 자동으로 배치합니다.")

        option_tokens = ["__AUTO__"] + [str(i) for i in usable_candidates.index]
        label_map = {
            str(i): f"{row['artist']} – {row['title']}  ·  {float(row['bpm']):.1f} BPM  ·  {row['camelot'] or row['key'] or 'Key 없음'}"
            for i, row in usable_candidates.iterrows()
        }

        existing_start = usable_candidates.index[usable_candidates["role"] == ROLE_START].tolist()
        existing_end = usable_candidates.index[usable_candidates["role"] == ROLE_END].tolist()
        start_default = str(existing_start[0]) if existing_start else "__AUTO__"
        end_default = str(existing_end[0]) if existing_end else "__AUTO__"

        def format_track_choice(token: str) -> str:
            return "지정하지 않음 — 자동 배치" if token == "__AUTO__" else label_map.get(token, token)

        st.markdown("### 공연 상황")
        ctx1, ctx2, ctx3 = st.columns(3)
        venue = ctx1.selectbox("공연 유형", list(VENUE_PRESETS), index=0)
        audience = ctx2.selectbox("관객 구성", list(AUDIENCE_PRESETS), index=3)
        mood = ctx3.selectbox("원하는 분위기", list(MOOD_PRESETS), index=2)
        st.caption(VENUE_PRESETS[venue]["note"])

        st.markdown("### 전개 프리셋")
        st.caption("느낌을 먼저 고르면 권장 세부 설정이 자동으로 채워집니다. 공연 상황이 프리셋에 자동 반영됩니다.")
        preset_keys = list(PRESET_CONFIGS.keys())
        if st.session_state.get("selected_preset") not in preset_keys:
            st.session_state["selected_preset"] = "classic_build"
        preset_key = st.radio(
            "세트 분위기 선택",
            preset_keys,
            format_func=lambda key: PRESET_CONFIGS[key]["label"],
            horizontal=True,
            label_visibility="collapsed",
            key="selected_preset",
        )
        preset = apply_context(PRESET_CONFIGS[preset_key], venue, audience, mood)
        st.info(f"**{preset['label']}** — {preset['description']}  \n{preset['summary']}")

        preview_positions = [i / 24 for i in range(25)]
        preview_values = [
            curve_value(preset["curve"], p, preset["start_energy"], preset["peak_energy"], preset["end_energy"])
            for p in preview_positions
        ]
        preview_df = pd.DataFrame({"목표 에너지": preview_values}, index=range(1, 26))
        st.line_chart(preview_df, height=170)

        with st.form("build_settings_form"):
            fixed1, fixed2 = st.columns(2)
            start_track_token = fixed1.selectbox(
                "첫 곡으로 고정",
                option_tokens,
                index=option_tokens.index(start_default) if start_default in option_tokens else 0,
                format_func=format_track_choice,
                help="선택한 곡은 세트의 1번 곡으로 고정됩니다.",
            )
            end_track_token = fixed2.selectbox(
                "마지막 곡으로 고정",
                option_tokens,
                index=option_tokens.index(end_default) if end_default in option_tokens else 0,
                format_func=format_track_choice,
                help="선택한 곡은 세트의 마지막 곡으로 고정됩니다.",
            )
            if start_track_token != "__AUTO__" and start_track_token == end_track_token:
                st.warning("같은 곡을 시작곡과 마지막곡으로 동시에 지정할 수 없습니다.")

            st.divider()
            a, b, c = st.columns(3)
            target_minutes = a.number_input("목표 세트 길이(분)", 10, 240, 60, 5)
            overlap_sec = b.number_input("평균 믹스 겹침(초)", 0, 180, 45, 5)
            seed = c.number_input("버전 번호", 1, 9999, 42, 1, help="숫자를 바꾸면 같은 설정에서도 다른 순서를 만들 수 있습니다.")

            st.markdown("#### 🎛️ AI Performance Planner")
            p1, p2, p3, p4 = st.columns(4)
            performance_enabled = p1.checkbox("마디 기반 시간 설계", True, help="곡 전체 길이 대신 Cue와 BPM을 이용해 실제 사용할 구간을 계산합니다.")
            variable_timing = p2.checkbox("곡 역할별 가변 시간", True, help="오프닝·피크·클로징은 길게, 브리지는 짧게 배분합니다.")
            average_play_sec = p3.number_input("평균 곡 사용시간(초)", 30, 240, 90, 5)
            tolerance_sec = p4.number_input("목표 오차 허용(초)", 5, 60, 15, 5)
            q1, q2 = st.columns(2)
            phrase_bars = q1.selectbox("기본 프레이즈 단위", [8, 16, 32], index=1)
            transition_bars = q2.selectbox("기본 믹싱 길이", [8, 16, 32], index=1)
            st.caption("이름이 지정된 Rekordbox Cue(Intro·Break·Drop·Outro)를 곡 역할과 함께 해석합니다. 구조 Cue가 부족하면 BPM·마디 기준으로 안전하게 추정합니다.")

            with st.expander("⚙️ 고급 설정 — 프리셋 세부값 조정", expanded=(preset_key == "custom")):
                st.caption("프리셋을 선택한 뒤 이 값을 조금씩 바꾸면 원하는 전개에 더 가깝게 조정할 수 있습니다.")
                curve_options = ["중후반 피크", "꾸준히 상승", "초반 피크", "파도형", "일정하게"]
                curve = st.selectbox(
                    "에너지 곡선 방식",
                    curve_options,
                    index=curve_options.index(preset["curve"]),
                    key=f"curve_{preset_key}",
                )
                e1, e2, e3 = st.columns(3)
                start_energy = e1.slider("시작 에너지", 1.0, 10.0, float(preset["start_energy"]), 0.5, key=f"start_energy_{preset_key}")
                peak_energy = e2.slider("피크 에너지", 1.0, 10.0, float(preset["peak_energy"]), 0.5, key=f"peak_energy_{preset_key}")
                end_energy = e3.slider("마지막 에너지", 1.0, 10.0, float(preset["end_energy"]), 0.5, key=f"end_energy_{preset_key}")
                auto_bpm = st.checkbox("시작·마지막 BPM 자동 계산", True, key=f"auto_bpm_{preset_key}")
                x1, x2, x3 = st.columns(3)
                start_bpm = x1.number_input("시작 BPM", 60.0, 200.0, 120.0, 0.5, disabled=auto_bpm, key=f"start_bpm_{preset_key}")
                end_bpm = x2.number_input("마지막 BPM", 60.0, 200.0, 132.0, 0.5, disabled=auto_bpm, key=f"end_bpm_{preset_key}")
                max_bpm_step = x3.slider("곡 사이 권장 BPM 변화", 1.0, 12.0, float(preset["max_bpm_step"]), 0.5, key=f"max_bpm_step_{preset_key}")
                w1, w2, w3 = st.columns(3)
                harmonic_weight = w1.slider("화성 믹싱 중요도", 0.0, 1.0, float(preset["harmonic_weight"]), 0.05, key=f"harmonic_weight_{preset_key}")
                energy_weight = w2.slider("에너지 곡선 중요도", 0.0, 1.0, float(preset["energy_weight"]), 0.05, key=f"energy_weight_{preset_key}")
                bpm_weight = w3.slider("BPM 흐름 중요도", 0.0, 1.0, float(preset["bpm_weight"]), 0.05, key=f"bpm_weight_{preset_key}")
                artist_gap = st.slider("같은 아티스트 재등장 최소 간격", 0, 8, int(preset["artist_gap"]), key=f"artist_gap_{preset_key}")

            generate = st.form_submit_button("이 프리셋으로 DPC 세트 생성", type="primary", use_container_width=True)
        if generate:
            if start_track_token != "__AUTO__" and start_track_token == end_track_token:
                st.error("시작곡과 마지막곡은 서로 다른 곡으로 선택해주세요.")
                st.stop()

            st.session_state["build_preset_label"] = preset["label"]
            st.session_state["performance_context"] = f"{venue} · {audience} · {mood}"
            build_candidates = candidates.copy()
            normalized_genres = build_candidates["genre"].fillna("").astype(str).str.strip().replace("", "장르 미지정")
            build_candidates["use"] = build_candidates["use"] & normalized_genres.isin(selected_genres)
            if int(build_candidates["use"].sum()) < 3:
                st.error("선택한 장르에 사용 가능한 곡이 3곡 미만입니다.")
                st.stop()
            build_candidates.loc[build_candidates["role"].isin([ROLE_START, ROLE_END]), "role"] = ROLE_NORMAL
            if start_track_token != "__AUTO__":
                build_candidates.loc[int(start_track_token), "role"] = ROLE_START
            if end_track_token != "__AUTO__":
                build_candidates.loc[int(end_track_token), "role"] = ROLE_END
            st.session_state["candidate_df"] = build_candidates

            settings = BuildSettings(
                target_minutes=int(target_minutes), overlap_sec=int(overlap_sec), curve=curve,
                start_energy=start_energy, peak_energy=peak_energy, end_energy=end_energy,
                start_bpm=None if auto_bpm else start_bpm + float(preset.get("context_bpm_shift",0)), end_bpm=None if auto_bpm else end_bpm + float(preset.get("context_bpm_shift",0)),
                max_bpm_step=max_bpm_step, harmonic_weight=harmonic_weight,
                energy_weight=energy_weight, bpm_weight=bpm_weight, artist_gap=artist_gap,
                seed=int(seed), iterations=7000,
                performance_average_play_sec=int(average_play_sec) if performance_enabled else None,
                performance_transition_bars=int(transition_bars),
            )
            try:
                with st.spinner("BPM·키·에너지 조합과 마디 단위 공연 시간을 계산하고 있습니다."):
                    result = build_set(build_candidates, settings)
                    if performance_enabled:
                        performance_settings = PerformancePlanSettings(
                            average_play_sec=int(average_play_sec),
                            tolerance_sec=int(tolerance_sec),
                            transition_bars=int(transition_bars),
                            phrase_bars=int(phrase_bars),
                            variable_timing=bool(variable_timing),
                        )
                        result = apply_performance_plan(result, performance_settings, int(target_minutes) * 60)
                        st.session_state["performance_plan_settings"] = performance_settings
                st.session_state["set_df"] = result
                st.session_state["build_settings"] = settings
                # Streamlit rerun 과정에서 dataclass/DataFrame attrs가 유실될 수 있으므로
                # Spotify 보충 탭에서 사용할 핵심 시간값은 단순 숫자로 별도 저장합니다.
                st.session_state["build_target_minutes"] = int(target_minutes)
                st.session_state["build_target_sec"] = int(target_minutes) * 60
                st.session_state["build_estimated_sec"] = int(round(result.attrs.get("estimated_duration_sec", 0)))
                st.session_state["build_overlap_sec"] = int(overlap_sec)
                st.session_state["selected_genres"] = selected_genres
                st.session_state.pop("spotify_matches", None)
                st.success("세트를 만들었습니다.")
                if st.session_state.get("wizard_mode"):
                    request_tab("edit")
                    st.rerun()
            except Exception as exc:
                st.error(str(exc))

        if "set_df" in st.session_state:
            result = st.session_state["set_df"]
            estimated = result.attrs.get("estimated_duration_sec", 0)
            preset_label = st.session_state.get("build_preset_label")
            if preset_label:
                st.caption(f"적용 프리셋: **{preset_label}**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("선곡 수", f"{len(result)}곡")
            m2.metric("예상 세트 길이", format_seconds(estimated))
            m3.metric("시작 → 마지막 BPM", f"{result.iloc[0]['bpm']:.1f} → {result.iloc[-1]['bpm']:.1f}")
            first_role = str(result.iloc[0].get("role", ""))
            last_role = str(result.iloc[-1].get("role", ""))
            fixed_notes = []
            if first_role == ROLE_START:
                fixed_notes.append(f"시작곡 고정: **{result.iloc[0]['artist']} – {result.iloc[0]['title']}**")
            if last_role == ROLE_END:
                fixed_notes.append(f"마지막곡 고정: **{result.iloc[-1]['artist']} – {result.iloc[-1]['title']}**")
            if fixed_notes:
                st.success("  ·  ".join(fixed_notes))
            m4.metric("평균 화성 연결", f"{result['transition_score'].mean():.0f}/100")
            chart_df = result.set_index("order")[["energy", "target_energy"]]
            st.line_chart(chart_df)
            if result.attrs.get("performance_plan_enabled"):
                display_cols = [
                    "order", "set_start_time", "title", "artist", "performance_role", "priority",
                    "used_range", "next_track_in_time", "planned_play_time",
                    "play_bars", "transition_bars", "structure_source", "confidence",
                    "bpm", "camelot", "energy", "key_transition"
                ]
                st.caption(
                    "사용 구간은 각 음원 파일 안의 위치입니다. ‘다음 곡 투입’부터 ‘사용 종료’까지가 전환 구간이며, "
                    "구조 Cue가 충분하지 않은 곡은 BPM 기반 추정으로 표시되며, 설정한 평균 사용시간을 크게 넘기지 않습니다."
                )
                target_gap = float(result.attrs.get("target_gap_sec", 0) or 0)
                tolerance = int(getattr(st.session_state.get("performance_plan_settings"), "tolerance_sec", 15))
                if target_gap > tolerance:
                    avg_sec = int(getattr(st.session_state.get("performance_plan_settings"), "average_play_sec", 90))
                    missing = max(1, math.ceil(target_gap / max(30, avg_sec)))
                    st.warning(
                        f"현재 후보곡만으로는 목표 시간보다 약 {format_seconds(target_gap)} 부족합니다. "
                        f"곡당 사용시간을 강제로 늘리지 않았습니다. 후보곡을 약 {missing}곡 이상 추가해주세요."
                    )
            else:
                display_cols = ["order", "set_time", "title", "artist", "bpm", "camelot", "energy", "target_energy", "bpm_change", "key_transition", "transition_score", "role"]
            display_df = result[display_cols].copy()
            if result.attrs.get("performance_plan_enabled"):
                display_df = display_df.rename(columns={
                    "order": "순서",
                    "set_start_time": "세트 진입",
                    "title": "곡명",
                    "artist": "아티스트",
                    "performance_role": "역할",
                    "priority": "우선순위",
                    "used_range": "사용 구간",
                    "next_track_in_time": "다음 곡 투입",
                    "planned_play_time": "사용시간",
                    "play_bars": "사용 마디",
                    "transition_bars": "전환 마디",
                    "structure_source": "구조 출처",
                    "confidence": "신뢰도",
                    "bpm": "BPM",
                    "camelot": "Camelot",
                    "energy": "Energy",
                    "key_transition": "키 전환",
                })
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=520)

            if result.attrs.get("performance_plan_enabled"):
                with st.expander("🎚️ 곡별 사용 구간 상세 보기"):
                    st.caption("곡 내부 시간과 전체 세트 타임라인을 구분해서 표시합니다.")
                    for _, track in result.iterrows():
                        st.markdown(
                            f"**{int(track['order']):02d}. {track['artist']} – {track['title']}**  "
                            f"`{track.get('performance_role', '')}` · 우선순위 {int(track.get('priority', 0))}/5"
                        )
                        c1, c2, c3 = st.columns(3)
                        c1.metric("곡 내부 사용 구간", str(track.get("used_range", "-")))
                        c2.metric("다음 곡 투입", str(track.get("next_track_in_time", "-")))
                        c3.metric("실제 사용시간", str(track.get("planned_play_time", "-")))
                        st.write(
                            f"핵심 재생: **{track.get('main_range', '-')}**  ·  "
                            f"전환 구간: **{track.get('transition_range', '-')}**  ·  "
                            f"전환 길이: **{int(track.get('transition_bars', 0))}마디**"
                        )
                        st.write(
                            f"세트 타임라인: **{track.get('set_range', '-')}**  ·  "
                            f"다음 곡 믹스 시작: **{track.get('set_next_mix_time', '-')}**"
                        )
                        st.caption(
                            f"분석 출처: {track.get('structure_source', '-')} · "
                            f"신뢰도: {track.get('confidence', '-')} · "
                            f"{track.get('plan_reason', '')}"
                        )
                        st.divider()

            warnings = result[(result["bpm_change"].abs() > max_bpm_step) | (result["key_transition"] == "큰 키 이동")]
            if not warnings.empty:
                st.warning(f"전환 주의 구간이 {len(warnings)}곳 있습니다. 실제 큐 포인트와 브레이크 구간을 듣고 확인하세요.")
            st.download_button("세트 CSV 다운로드", export_set_csv(result), file_name="DPC_DJ_Set.csv", mime="text/csv", use_container_width=True)
            notes = explain_set(result, st.session_state.get("build_preset_label", ""), st.session_state.get("performance_context", ""))
            st.markdown("### 🤖 AI 세트 해설")
            for note in notes:
                st.write(f"- {note}")
            st.download_button("공연 리포트 HTML 다운로드", make_html_report(result, notes), file_name="DPC_SetLab_Report.html", mime="text/html", use_container_width=True)

with edit_tab:
    st.subheader("SET EDITOR")
    st.caption("AI가 생성한 순서와 메타데이터를 공연 전 최종 검토합니다. 변경 내용은 Export에 바로 반영됩니다.")
    result = st.session_state.get("set_df")
    if not isinstance(result, pd.DataFrame) or result.empty:
        st.info("먼저 GENERATE에서 AI 세트를 생성하세요.")
    else:
        editable_columns = [c for c in ["order", "title", "artist", "bpm", "camelot", "energy", "role", "comments"] if c in result.columns]
        disabled_columns = [c for c in editable_columns if c not in {"order", "energy", "role", "comments"}]
        edited_set = st.data_editor(
            result[editable_columns],
            use_container_width=True,
            hide_index=True,
            height=560,
            disabled=disabled_columns,
            num_rows="fixed",
            key="patch07_set_editor",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("편집 내용 저장", type="primary", use_container_width=True):
                updated = result.copy()
                for col in edited_set.columns:
                    updated[col] = edited_set[col].values
                if "order" in updated.columns:
                    updated = updated.sort_values("order", kind="stable").reset_index(drop=True)
                    updated["order"] = range(1, len(updated) + 1)
                st.session_state["set_df"] = updated
                st.session_state["set_edit_complete"] = True
                st.success("편집 내용을 저장했습니다. EXPORT에서 내보낼 수 있습니다.")
                if st.session_state.get("wizard_mode"):
                    request_tab("export")
                    st.rerun()
        with c2:
            st.download_button("검토용 CSV 다운로드", export_set_csv(result), file_name="DPC_SetLab_Edit_Review.csv", mime="text/csv", use_container_width=True)
        st.markdown("### 검토 체크리스트")
        st.checkbox("시작곡과 마지막곡을 실제로 들어봤습니다.", key="edit_check_open_close")
        st.checkbox("BPM 변화가 큰 전환을 확인했습니다.", key="edit_check_bpm")
        st.checkbox("보컬 충돌과 브레이크 길이를 확인했습니다.", key="edit_check_vocal")
        st.checkbox("모든 로컬 파일 경로를 확인했습니다.", key="edit_check_path")


with spotify_tab:
    st.subheader("EXPORT CENTER")
    st.caption("완성한 세트를 감상용 Spotify 플레이리스트 또는 공연용 Rekordbox 파일로 내보냅니다.")
    st.markdown("### 🎵 Spotify Playlist")
    if "set_df" not in st.session_state:
        st.warning("먼저 ‘세트 만들기’에서 세트를 생성하세요.")
    elif not client_id.strip():
        st.warning("SETTINGS에서 Spotify Client ID를 입력하고 저장하세요.")
    else:
        token = current_spotify_token()
        if not token:
            st.info("HOME에서 Spotify를 먼저 연결하세요.")
        else:
            set_df = st.session_state["set_df"]
            if st.button("Spotify 곡 매칭 시작", use_container_width=True):
                progress_bar = st.progress(0.0)
                status = st.empty()
                def update_progress(i, total, text):
                    progress_bar.progress(i / max(total, 1))
                    status.text(f"[{i}/{total}] {text}")
                try:
                    api = api_from_token(token)
                    matches = match_set(api, set_df, update_progress)
                    st.session_state["spotify_matches"] = matches
                    status.text("매칭 완료")
                    st.success("Spotify 매칭이 끝났습니다.")
                except Exception as exc:
                    st.error(str(exc))
            if "spotify_matches" in st.session_state:
                matches = st.session_state["spotify_matches"]
                st.caption("신뢰도가 낮은 곡은 ‘추가’ 체크를 해제했습니다. Spotify 링크를 열어 버전을 확인하세요.")
                edited_matches = st.data_editor(
                    matches,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["order", "input_title", "input_artist", "confidence", "spotify_title", "spotify_artists", "spotify_uri", "spotify_url", "status"],
                    column_config={
                        "include": st.column_config.CheckboxColumn("추가"),
                        "order": "순서", "input_title": "원본 제목", "input_artist": "원본 아티스트",
                        "confidence": st.column_config.ProgressColumn("일치도", min_value=0.0, max_value=1.0, format="%.2f"),
                        "spotify_title": "Spotify 제목", "spotify_artists": "Spotify 아티스트",
                        "spotify_url": st.column_config.LinkColumn("확인 링크", display_text="Spotify 열기"),
                        "spotify_uri": None, "status": "상태",
                    },
                    num_rows="fixed",
                )
                st.session_state["spotify_matches"] = edited_matches.copy()

                st.markdown("### 잘못 매칭된 곡 직접 수정")
                st.caption("원본 곡을 선택하고 Spotify를 다시 검색한 뒤, 정확한 결과로 교체할 수 있습니다.")
                repair_options = edited_matches.index.tolist()
                repair_index = st.selectbox(
                    "수정할 원본 곡",
                    repair_options,
                    format_func=lambda i: f"{int(edited_matches.loc[i, 'order']):02d}. {edited_matches.loc[i, 'input_artist']} – {edited_matches.loc[i, 'input_title']}",
                    key="spotify_repair_index",
                )
                selected_match = edited_matches.loc[repair_index]
                default_query = f"{selected_match['input_title']} {selected_match['input_artist']}".strip()
                manual_query = st.text_input(
                    "Spotify 직접 검색어",
                    value=default_query,
                    help="리믹스명, 버전명, 피처링 아티스트까지 추가하면 더 정확하게 찾을 수 있습니다.",
                    key=f"spotify_manual_query_{repair_index}",
                )
                if st.button("Spotify에서 다시 검색", use_container_width=True, key="spotify_manual_search"):
                    try:
                        api = api_from_token(require_spotify_token())
                        results = search_manual_tracks(api, manual_query, limit=10)
                        st.session_state["spotify_manual_results"] = results
                        st.session_state["spotify_manual_results_for"] = repair_index
                        if results.empty:
                            st.warning("검색 결과가 없습니다. 제목이나 아티스트 검색어를 단순하게 바꿔보세요.")
                    except Exception as exc:
                        st.error(str(exc))

                manual_results = st.session_state.get("spotify_manual_results")
                if isinstance(manual_results, pd.DataFrame) and st.session_state.get("spotify_manual_results_for") == repair_index and not manual_results.empty:
                    result_labels = [
                        f"{row['artist']} – {row['title']} · {row['album']} · {row['duration']}"
                        for _, row in manual_results.iterrows()
                    ]
                    picked_position = st.radio(
                        "검색 결과에서 정확한 곡 선택",
                        options=list(range(len(result_labels))),
                        format_func=lambda i: result_labels[i],
                        key=f"spotify_manual_pick_{repair_index}",
                    )
                    picked = manual_results.iloc[picked_position]
                    if picked.get("spotify_url"):
                        st.link_button("선택한 곡 Spotify에서 확인", str(picked["spotify_url"]), use_container_width=True)
                    if st.button("이 곡으로 매칭 교체", type="primary", use_container_width=True, key="spotify_manual_apply"):
                        updated = edited_matches.copy()
                        updated.loc[repair_index, "include"] = True
                        updated.loc[repair_index, "confidence"] = 1.0
                        updated.loc[repair_index, "spotify_title"] = picked["title"]
                        updated.loc[repair_index, "spotify_artists"] = picked["artist"]
                        updated.loc[repair_index, "spotify_uri"] = picked["spotify_uri"]
                        updated.loc[repair_index, "spotify_url"] = picked["spotify_url"]
                        updated.loc[repair_index, "status"] = "직접 수정"
                        st.session_state["spotify_matches"] = updated
                        st.session_state.pop("spotify_manual_results", None)
                        st.session_state.pop("spotify_manual_results_for", None)
                        st.success("선택한 Spotify 곡으로 교체했습니다. 플레이리스트 생성 시 이 곡이 포함됩니다.")
                        st.rerun()
                st.divider()
                st.markdown("### 부족한 세트 시간 자동 보충")
                settings = st.session_state.get("build_settings")

                # 1순위: 세트 생성 시 별도 저장한 단순 숫자값
                target_sec = int(st.session_state.get("build_target_sec", 0) or 0)
                if target_sec <= 0 and settings is not None:
                    target_sec = int(getattr(settings, "target_minutes", 0) or 0) * 60

                current_sec = int(st.session_state.get("build_estimated_sec", 0) or 0)
                if current_sec <= 0:
                    current_sec = int(set_df.attrs.get("estimated_duration_sec", 0) or 0)

                # DataFrame attrs까지 유실된 경우 곡 길이와 평균 믹스 겹침으로 재계산
                if current_sec <= 0 and not set_df.empty and "duration_sec" in set_df.columns:
                    overlap_for_calc = int(st.session_state.get("build_overlap_sec", 0) or 0)
                    durations = pd.to_numeric(set_df["duration_sec"], errors="coerce").fillna(0).tolist()
                    current_sec = int(round(sum(
                        duration if i == 0 else max(30.0, duration - overlap_for_calc)
                        for i, duration in enumerate(durations)
                    )))

                shortage_sec = max(0, target_sec - current_sec)
                c1, c2, c3 = st.columns(3)
                c1.metric("목표 시간", format_seconds(target_sec))
                c2.metric("현재 세트", format_seconds(current_sec))
                c3.metric("부족 시간", format_seconds(shortage_sec))

                if target_sec <= 0:
                    st.error("목표 세트 시간을 불러오지 못했습니다. ‘3. AI 세트’에서 세트를 다시 생성해주세요.")
                elif shortage_sec <= 0:
                    st.success("현재 세트가 목표 시간을 충족합니다.")
                else:
                    st.warning(f"목표 시간보다 약 {format_seconds(shortage_sec)} 부족합니다.")
                    selected_genres_for_fill = [g for g in st.session_state.get("selected_genres", []) if g != "장르 미지정"]
                    available_fill_genres = sorted({
                        str(g).strip()
                        for g in list(selected_genres_for_fill) + set_df.get("genre", pd.Series(dtype=str)).fillna("").astype(str).tolist()
                        if str(g).strip() and str(g).strip() != "장르 미지정"
                    })
                    genre_hint = st.segmented_control(
                        "Spotify 검색 장르",
                        options=available_fill_genres,
                        default=[g for g in selected_genres_for_fill if g in available_fill_genres],
                        selection_mode="multi",
                        help="검색에 사용할 장르 버튼을 여러 개 선택할 수 있습니다.",
                        key="spotify_fill_genres",
                    ) if available_fill_genres else []
                    st.caption("선택한 버튼의 장르와 현재 세트 아티스트를 함께 사용해 보충곡을 검색합니다.")
                    if st.button("Spotify에서 보충곡 찾기", use_container_width=True):
                        try:
                            api = api_from_token(require_spotify_token())
                            existing_uris = set(matches["spotify_uri"].dropna().astype(str))
                            fill = discover_fill_tracks(
                                api,
                                set_df=set_df,
                                shortage_sec=shortage_sec,
                                genres=list(genre_hint or []),
                                exclude_uris=existing_uris,
                            )
                            st.session_state["spotify_fill_tracks"] = fill
                            if fill.empty:
                                st.warning("조건에 맞는 보충곡을 찾지 못했습니다. 선택한 장르를 줄이거나 다른 장르 버튼을 선택해보세요.")
                            else:
                                st.success(f"보충 후보 {len(fill)}곡을 찾았습니다.")
                        except Exception as exc:
                            st.error(str(exc))
                    if "spotify_fill_tracks" in st.session_state:
                        fill_tracks = st.session_state["spotify_fill_tracks"]
                        edited_fill = st.data_editor(
                            fill_tracks,
                            use_container_width=True,
                            hide_index=True,
                            disabled=["title", "artist", "duration", "source", "spotify_uri", "spotify_url"],
                            column_config={
                                "include": st.column_config.CheckboxColumn("추가"),
                                "title": "추천 제목", "artist": "아티스트", "duration": "길이",
                                "source": "발견 기준",
                                "spotify_url": st.column_config.LinkColumn("확인", display_text="Spotify 열기"),
                                "duration_sec": None,
                                "spotify_uri": None,
                            },
                            num_rows="fixed",
                            key="fill_editor",
                        )
                        st.session_state["spotify_fill_tracks_edited"] = edited_fill
                        selected_fill_sec = int(edited_fill.loc[edited_fill["include"], "duration_sec"].sum()) if "duration_sec" in edited_fill else 0
                        st.caption(f"선택한 보충곡 총 길이: **{format_seconds(selected_fill_sec)}** · 실제 DJ 믹스에서는 겹침 시간만큼 짧아질 수 있습니다.")
                        st.info("보충곡은 Spotify 검색 기반이라 BPM·키 정보가 없습니다. 아래 2단계 워크플로우로 최종 정렬하세요.")
                        st.markdown("""
**추천곡 사용 가이드**  
① Spotify 플레이리스트 끝에 보충곡 추가  
② Rekordbox로 플레이리스트 가져오기  
③ `Analyze Track`으로 BPM·Key·Beat Grid 분석  
④ Rekordbox XML을 다시 내보내기  
⑤ DPC SetLab에서 `AI Final` 세트로 재생성
""")

                p1, p2 = st.columns([3, 1])
                playlist_name = p1.text_input("새 Spotify 플레이리스트 이름", value=default_playlist_name)
                public = p2.checkbox("공개", value=default_public)
                if st.button("Spotify 플레이리스트 생성", type="primary", use_container_width=True):
                    uris = edited_matches.loc[edited_matches["include"] & edited_matches["spotify_uri"].astype(str).str.startswith("spotify:track:"), "spotify_uri"].tolist()
                    edited_fill = st.session_state.get("spotify_fill_tracks_edited")
                    if isinstance(edited_fill, pd.DataFrame) and not edited_fill.empty:
                        fill_uris = edited_fill.loc[edited_fill["include"] & edited_fill["spotify_uri"].astype(str).str.startswith("spotify:track:"), "spotify_uri"].tolist()
                        uris.extend(uri for uri in fill_uris if uri not in uris)
                    if not uris:
                        st.error("추가할 수 있는 Spotify 곡이 없습니다.")
                    else:
                        try:
                            api = api_from_token(require_spotify_token())
                            playlist = api.create_playlist(playlist_name.strip() or "DPC DJ Set", "Created with DPC DJ Set Builder", public)
                            api.add_items(playlist["id"], uris)
                            url = playlist.get("external_urls", {}).get("spotify", "")
                            st.session_state["spotify_export_complete"] = True
                            st.session_state["spotify_playlist_url"] = url
                            st.session_state["spotify_playlist_name"] = playlist_name.strip() or "DPC DJ Set"
                            st.success(f"{len(uris)}곡으로 플레이리스트를 만들었습니다.")
                            if url:
                                st.link_button("Spotify에서 플레이리스트 열기", url, use_container_width=True)
                        except Exception as exc:
                            st.error(str(exc))


    st.divider()
    st.markdown("### 💿 Rekordbox XML Sync · ⭐ 추천")
    st.caption("LIBRARY에서 불러온 원본 Rekordbox XML은 그대로 보존하고, 현재 세트 플레이리스트만 추가한 새 XML을 만듭니다.")

    with st.expander("📖 Rekordbox XML 처음부터 끝까지 따라하기", expanded=False):
        st.markdown("""
#### A. Rekordbox에서 원본 XML 만들기
1. Rekordbox를 **EXPORT 모드**로 실행합니다.
2. 상단 메뉴에서 **File → Export Collection in xml format**을 선택합니다.
3. 찾기 쉬운 위치에 `rekordbox.xml`로 저장합니다.
4. DPC SetLab의 **LIBRARY** 탭에서 방금 만든 XML을 업로드합니다.

#### B. DPC SetLab에서 세트 추가하기
1. CANDIDATES와 PLANNER에서 세트를 완성합니다.
2. 이 화면에서 플레이리스트 이름을 입력합니다.
3. 검사 결과가 `READY`인 곡만 새 플레이리스트에 포함됩니다.
4. **업데이트 XML 다운로드**와 **원본 백업 다운로드**를 모두 보관합니다.

#### C. 수정된 XML을 Rekordbox에 적용하기
1. Rekordbox에서 **Preferences → Advanced → Database**로 이동합니다.
2. **rekordbox xml** 항목의 파일 경로에서 다운로드한 `*_updated.xml`을 지정합니다.
3. Rekordbox 왼쪽 브라우저의 **rekordbox xml → DPC SetLab** 폴더를 펼칩니다.
4. 새 플레이리스트를 우클릭해 **Import Playlist**를 선택합니다.
5. 일반 **Playlists** 영역에 복사된 플레이리스트와 곡 연결 상태를 확인합니다.
6. USB를 연결하고 해당 플레이리스트를 장치로 Export합니다.

> XML 파일을 기존 파일 위에 직접 덮어쓰지 마세요. 문제가 있으면 원본 백업 XML을 다시 지정하면 됩니다.
""")

    original_xml = st.session_state.get("rekordbox_xml_bytes")
    if "set_df" not in st.session_state:
        st.info("먼저 PLANNER에서 세트를 생성하세요.")
    elif not original_xml:
        st.warning("Rekordbox XML Sync를 사용하려면 먼저 LIBRARY 탭에서 원본 Rekordbox XML을 업로드하세요. CSV나 샘플 세트만으로는 기존 Collection을 안전하게 유지할 수 없습니다.")
    else:
        rekordbox_set = st.session_state["set_df"]
        sync_check = assess_rekordbox_sync(original_xml, rekordbox_set)
        ready_count = int(sync_check["include"].sum()) if not sync_check.empty else 0
        missing_count = int((sync_check["status"] == "PATH MISSING").sum()) if not sync_check.empty else 0
        not_library_count = int((sync_check["status"] == "NOT IN LIBRARY").sum()) if not sync_check.empty else 0
        total_count = len(sync_check)

        st.markdown("#### 다운로드 전 검사")
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("전체 세트", f"{total_count}곡")
        q2.metric("READY", f"{ready_count}곡")
        q3.metric("NOT IN LIBRARY", f"{not_library_count}곡")
        q4.metric("PATH MISSING", f"{missing_count}곡")
        if ready_count < total_count:
            st.warning(f"{total_count - ready_count}곡은 원본 Rekordbox Collection과 연결되지 않아 새 플레이리스트에서 제외됩니다.")
            with st.expander("누락되는 곡 보기"):
                st.dataframe(sync_check.loc[~sync_check["include"], ["order", "artist", "title", "status", "reason"]], use_container_width=True, hide_index=True)
                st.download_button("누락곡 CSV 다운로드", sync_check.loc[~sync_check["include"]].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name="DPC_SetLab_missing_tracks.csv", mime="text/csv", use_container_width=True)
        else:
            st.success("현재 세트의 모든 곡이 원본 Rekordbox Collection과 연결되었습니다.")

        rekordbox_name = st.text_input("Rekordbox 플레이리스트 이름", value=default_playlist_name, key="rekordbox_playlist_name")
        updated_xml = sync_rekordbox_xml(original_xml, rekordbox_set, rekordbox_name)
        m3u8_data = export_m3u8(rekordbox_set)
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (rekordbox_name.strip() or "DPC_DJ_Set")).strip().replace(" ", "_")

        left, middle, right = st.columns(3)
        with left:
            st.markdown("#### 업데이트 XML")
            st.info("기존 Collection과 기존 플레이리스트를 유지하고 `DPC SetLab` 폴더에 현재 세트를 추가합니다.")
            st.download_button("업데이트 XML 다운로드", updated_xml, file_name=f"{safe_name}_updated.xml", mime="application/xml", use_container_width=True, disabled=ready_count == 0)
        with middle:
            st.markdown("#### 원본 백업")
            st.info("문제가 생기면 Rekordbox의 XML 경로를 이 파일로 다시 지정해 원래 상태로 돌아갈 수 있습니다.")
            original_name = st.session_state.get("rekordbox_xml_name", "rekordbox.xml")
            backup_stem = Path(original_name).stem or "rekordbox"
            st.download_button("원본 백업 다운로드", original_xml, file_name=f"{backup_stem}_backup.xml", mime="application/xml", use_container_width=True)
        with right:
            st.markdown("#### M3U8 · 범용")
            st.info("READY 곡의 재생 순서와 로컬 파일 경로만 저장합니다. VLC 등에서도 사용할 수 있습니다.")
            st.download_button("M3U8 다운로드", m3u8_data, file_name=f"{safe_name}.m3u8", mime="audio/x-mpegurl", use_container_width=True, disabled=ready_count == 0)

        st.markdown("#### Rekordbox 적용 체크리스트")
        c1, c2 = st.columns(2)
        with c1:
            st.checkbox("업데이트 XML을 다운로드했다", key="wizard_downloaded")
            st.checkbox("Preferences → Advanced → Database를 열었다", key="wizard_database")
            st.checkbox("rekordbox xml 경로를 업데이트 XML로 지정했다", key="wizard_selected")
        with c2:
            st.checkbox("rekordbox xml → DPC SetLab을 확인했다", key="wizard_found")
            st.checkbox("새 플레이리스트에서 Import Playlist를 실행했다", key="wizard_imported")
            st.checkbox("일반 Playlists에서 곡을 확인했다", key="wizard_verified")

        done = sum(bool(st.session_state.get(k)) for k in ["wizard_downloaded", "wizard_database", "wizard_selected", "wizard_found", "wizard_imported", "wizard_verified"])
        st.progress(done / 6, text=f"Rekordbox Setup {done} / 6")

with coach_tab:
    st.subheader("AI 코치 · 다음 곡 추천")
    if "set_df" not in st.session_state:
        st.warning("먼저 AI 세트를 생성하세요.")
    else:
        result = st.session_state["set_df"]
        notes = explain_set(result, st.session_state.get("build_preset_label", ""), st.session_state.get("performance_context", ""))
        for note in notes:
            st.write(f"- {note}")
        st.divider()
        labels = [f"{int(r['order']):02d}. {r['artist']} – {r['title']}" for _, r in result.iterrows()]
        chosen = st.selectbox("현재 재생 중인 곡", range(len(labels)), format_func=lambda i: labels[i])
        pool = st.session_state.get("candidate_df", result)
        recs = recommend_next_tracks(result.iloc[chosen], pool[pool["use"]], 10)
        st.dataframe(recs.drop(columns=["원본 인덱스"], errors="ignore"), use_container_width=True, hide_index=True)
        profile = load_style_profile()
        if profile:
            st.info(f"개인 스타일 학습: {profile.get('sessions',0)}개 세트 · 평균 {profile.get('avg_bpm',0)} BPM · 에너지 {profile.get('avg_energy',0)}")

with history_tab:
    st.subheader("Rekordbox History / 과거 세트 분석")
    st.caption("공연 순서대로 정렬된 CSV를 올리면 전환과 스타일을 분석합니다. Rekordbox History를 CSV로 내보낸 파일을 권장합니다.")
    history_file = st.file_uploader("History CSV", type=["csv"], key="history_upload")
    if history_file is not None:
        try:
            history_df = parse_csv(history_file.getvalue())
            analysis = analyze_history(history_df)
            h1,h2,h3,h4 = st.columns(4)
            h1.metric("곡 수", analysis.get("tracks",0))
            h2.metric("평균 BPM", analysis.get("avg_bpm",0))
            h3.metric("평균 에너지", analysis.get("avg_energy",0))
            h4.metric("화성 연결", f"{analysis.get('harmonic_avg',0):.0f}/100")
            st.write(f"피크: **{analysis.get('peak_order')}번 · {analysis.get('peak_track')}**")
            st.write(f"큰 키 이동 {analysis.get('big_key_moves',0)}회 · 큰 BPM 이동 {analysis.get('large_bpm_moves',0)}회")
            if analysis.get("genres"):
                st.bar_chart(pd.Series(analysis["genres"], name="곡 수"))
            trans = analysis.get("transitions")
            if isinstance(trans, pd.DataFrame) and not trans.empty:
                st.dataframe(trans, use_container_width=True, hide_index=True)
            if st.button("이 공연을 내 DJ 스타일에 학습"):
                profile = save_style_profile(analysis)
                st.success(f"스타일 프로필에 반영했습니다. 누적 {profile['sessions']}개 세트")
        except Exception as exc:
            st.error(str(exc))

with settings_tab:
    if st.button("첫 시작 화면 다시 보기", use_container_width=True, key="reset_first_run_landing"):
        st.session_state["workspace_entered"] = False
        st.session_state["landing_started"] = False
        st.rerun()
    st.caption("온보딩 랜딩 화면과 Spotify-first 시작 흐름을 다시 확인할 수 있습니다.")
    st.subheader("⚙️ Settings")
    st.caption("연결 상태와 API 정보는 이곳에서만 관리합니다. 로컬 설정은 config/settings.json에 저장되며 GitHub에는 업로드되지 않습니다.")

    st.markdown("#### 서비스 연결")
    c1, c2, c3 = st.columns(3)
    c1.metric("Spotify", "Connected" if token else "Not connected")
    c2.metric("Last.fm", "Configured" if lastfm_api_key else "Not configured")
    c3.metric("Redirect mode", "Web" if is_web_spotify else "Local")
    st.caption(f"Spotify Redirect URI: `{redirect_uri}`")

    if is_web_spotify and client_id and not oauth_state_secret:
        st.warning("Streamlit Secrets에 [app] oauth_state_secret을 추가해야 Spotify 로그인을 사용할 수 있습니다.")
    if is_web_spotify:
        auth_url = st.session_state.get("spotify_oauth_url", "")
        st.link_button(
            "Spotify 연결 / 재연결",
            auth_url or redirect_uri,
            use_container_width=True,
            disabled=not bool(client_id and auth_url and oauth_state_secret),
        )
    elif st.button("Spotify 연결 / 재연결", use_container_width=True, disabled=not bool(client_id), key="settings_spotify_connect"):
        try:
            with st.spinner("브라우저에서 Spotify 접근을 승인해주세요."):
                token = authorize(client_id)
            st.success("Spotify 연결 완료")
        except Exception as exc:
            st.error(str(exc))
    if st.button("저장된 Spotify 로그인 삭제", use_container_width=True, key="settings_spotify_reset"):
        reset_token()
        st.session_state.pop("spotify_web_token", None)
        st.session_state.pop("spotify_oauth_url", None)
        st.success("로그인 정보를 삭제했습니다.")
        st.rerun()

    st.divider()
    with st.form("settings_form"):
        spotify_client_id_input = st.text_input("Spotify Client ID", value=client_id, placeholder="Spotify Developer Client ID")
        spotify_redirect_uri_input = st.text_input(
            "Spotify Redirect URI",
            value=redirect_uri,
            help="웹: https://dpc-setlab.streamlit.app · 로컬: http://127.0.0.1:8888/callback",
        )
        lastfm_key_input = st.text_input("Last.fm API Key", value=lastfm_api_key, type="password")
        discogs_token_input = st.text_input("Discogs Token (선택)", value=discogs_token, type="password")
        playlist_name_input = st.text_input("기본 Spotify 플레이리스트 이름", value=default_playlist_name)
        public_input = st.checkbox("기본 공개 플레이리스트", value=default_public)
        auto_connect_input = st.checkbox("앱 시작 시 저장된 Spotify 로그인 자동 확인", value=auto_connect)
        save_clicked = st.form_submit_button("설정 저장", use_container_width=True)
    if save_clicked:
        new_settings = {
            "spotify": {
                "client_id": spotify_client_id_input.strip(),
                "redirect_uri": spotify_redirect_uri_input.strip() or "http://127.0.0.1:8888/callback",
            },
            "lastfm": {"api_key": lastfm_key_input.strip()},
            "discogs": {"token": discogs_token_input.strip()},
            "preferences": {
                "playlist_name": playlist_name_input.strip() or "DPC DJ Set",
                "public_playlist": public_input,
                "auto_connect": auto_connect_input,
            },
        }
        try:
            save_settings(new_settings)
            st.success("설정을 저장했습니다. 새 값을 전체 앱에 적용하려면 아래 버튼을 누르세요.")
            if st.button("저장한 설정 적용", type="primary", use_container_width=True):
                st.rerun()
        except OSError as exc:
            st.error(f"설정 저장 실패: {exc}")

    st.divider()
    st.markdown("#### 연결 테스트")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Spotify 연결 테스트", use_container_width=True, disabled=not bool(client_id)):
            if is_web_spotify:
                active = current_spotify_token()
                if not active:
                    st.warning("먼저 Spotify 연결을 완료해주세요.")
                else:
                    try:
                        profile = api_from_token(active).me()
                        st.success(f"Spotify 연결 정상: {profile.get('display_name') or profile.get('id', '사용자')}")
                    except Exception as exc:
                        st.warning(f"Spotify 연결 확인 실패: {exc}")
            else:
                ok, message = test_spotify_connection(client_id)
                (st.success if ok else st.warning)(message)
    with c2:
        if st.button("Last.fm API 테스트", use_container_width=True, disabled=not bool(lastfm_api_key)):
            with st.spinner("Last.fm 연결 확인 중..."):
                ok, message = test_lastfm_connection(lastfm_api_key)
            (st.success if ok else st.error)(message)

    st.divider()
    s1, s2, s3 = st.columns(3)
    s1.metric("Spotify", "Connected" if token else "Not connected")
    s2.metric("Last.fm", "Configured" if lastfm_api_key else "Not configured")
    s3.metric("DPC SetLab", "v4.0.6-dev")
    st.info("Streamlit Cloud에서는 config/settings.json 대신 App settings → Secrets에 키를 저장해야 재부팅 후에도 유지됩니다.")
    st.code('''[spotify]
client_id = "YOUR_CLIENT_ID"
redirect_uri = "https://dpc-setlab.streamlit.app"

[lastfm]
api_key = "YOUR_LASTFM_API_KEY"

[discogs]
token = "OPTIONAL"''', language="toml")


with guide_tab:
    st.subheader("DPC SetLab 4.0 워크플로우")
    st.markdown("""
1. **Rekordbox 후보곡 불러오기**  
   Collection 또는 공연 후보 플레이리스트를 XML로 내보냅니다.
2. **후보곡 불러오기**  
   XML을 올리고 Collection 또는 특정 플레이리스트를 고릅니다.
3. **곡 역할 지정**  
   꼭 넣을 곡은 `필수`, 첫 곡은 `시작`, 마지막 곡은 `마지막`으로 바꿉니다.
4. **에너지 확인**  
   앱이 BPM·별점·재생 횟수로 1–10을 자동 추정합니다. 실제 느낌과 다르면 직접 고칩니다.
5. **장르와 세트 전개 선택**  
   사용할 장르를 고르고 전개 프리셋과 목표 길이를 설정합니다. 필요하면 고급 설정을 펼쳐 세부값을 조정하고 여러 버전 번호를 비교합니다.
6. **직접 청취 검토**  
   이 앱은 큐 포인트, 보컬 충돌, 브레이크 길이, 드롭 구조를 듣지 못하므로 최종 순서는 반드시 귀로 확인합니다.
7. **Spotify 부족곡 보충**  
   부족한 시간만큼 검색 기반 후보를 추가합니다.
8. **Rekordbox Analyze**  
   Spotify 보충곡을 Rekordbox로 가져와 BPM·Key·Beat Grid를 분석합니다.
9. **AI Final**  
   분석이 끝난 XML을 다시 불러와 최종 세트를 생성합니다.
10. **AI 코치와 History 분석**  
   다음 곡 추천, 공연 해설, 과거 History 분석과 개인 스타일 학습을 사용합니다.
""")
    st.info("Rekordbox의 스트리밍 곡이나 로컬 에디트가 Spotify에 없으면 매칭되지 않습니다. CSV 다운로드는 항상 사용할 수 있습니다.")
