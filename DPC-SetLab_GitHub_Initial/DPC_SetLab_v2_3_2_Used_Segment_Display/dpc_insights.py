from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pandas as pd

from dpc_core import effective_bpm_diff, harmonic_cost, harmonic_relation, primary_artist, format_seconds

PROFILE_FILE = Path('dj_style_profile.json')

VENUE_PRESETS = {
    '클럽': {'energy_shift': 0.8, 'bpm_shift': 2.0, 'harmonic': 0.65, 'note': '초반 점화가 빠르고 피크 구간을 길게 가져갑니다.'},
    '라운지': {'energy_shift': -1.2, 'bpm_shift': -3.0, 'harmonic': 0.88, 'note': '화성 연결과 여유 있는 흐름을 우선합니다.'},
    '루프탑': {'energy_shift': -0.3, 'bpm_shift': 0.0, 'harmonic': 0.78, 'note': '밝고 개방적인 전개와 완만한 상승에 적합합니다.'},
    '페스티벌': {'energy_shift': 1.0, 'bpm_shift': 3.0, 'harmonic': 0.58, 'note': '명확한 피크와 큰 에너지 대비를 강조합니다.'},
    '카페': {'energy_shift': -1.8, 'bpm_shift': -5.0, 'harmonic': 0.90, 'note': '대화를 방해하지 않는 낮은 에너지와 부드러운 연결을 권장합니다.'},
    '웨딩': {'energy_shift': -0.2, 'bpm_shift': -1.0, 'harmonic': 0.72, 'note': '세대 혼합을 고려해 친숙함과 안정적인 전개를 우선합니다.'},
    '브랜드 행사': {'energy_shift': 0.0, 'bpm_shift': 0.0, 'harmonic': 0.80, 'note': '행사 흐름을 방해하지 않도록 과도한 피크를 줄입니다.'},
    'DJ 클래스': {'energy_shift': -0.4, 'bpm_shift': 0.0, 'harmonic': 0.92, 'note': '전환이 명확하고 학습하기 쉬운 조합을 우선합니다.'},
}

MOOD_PRESETS = {
    '차분하게': -1.2,
    '감성적으로': -0.6,
    '그루비하게': 0.0,
    '힙하게': 0.4,
    '신나게': 0.8,
    '강렬하게': 1.3,
}

AUDIENCE_PRESETS = {
    '20대 중심': {'bpm': 1.5, 'energy': 0.5},
    '30대 중심': {'bpm': 0.0, 'energy': 0.1},
    '40대 중심': {'bpm': -1.5, 'energy': -0.4},
    '연령 혼합': {'bpm': -0.5, 'energy': -0.2},
}


def apply_context(preset: dict[str, Any], venue: str, audience: str, mood: str) -> dict[str, Any]:
    out = dict(preset)
    v = VENUE_PRESETS.get(venue, VENUE_PRESETS['클럽'])
    a = AUDIENCE_PRESETS.get(audience, AUDIENCE_PRESETS['연령 혼합'])
    mood_shift = MOOD_PRESETS.get(mood, 0.0)
    energy_shift = v['energy_shift'] + a['energy'] + mood_shift
    for key in ('start_energy', 'peak_energy', 'end_energy'):
        out[key] = max(1.0, min(10.0, float(out[key]) + energy_shift))
    out['harmonic_weight'] = max(float(out.get('harmonic_weight', .65)), float(v['harmonic']))
    out['context_bpm_shift'] = float(v['bpm_shift']) + float(a['bpm'])
    out['context_note'] = v['note']
    return out


def explain_set(df: pd.DataFrame, preset_label: str = '', context: str = '') -> list[str]:
    if df is None or df.empty:
        return []
    avg_bpm = float(pd.to_numeric(df['bpm'], errors='coerce').mean())
    max_energy_idx = int(pd.to_numeric(df['energy'], errors='coerce').idxmax())
    peak_row = df.loc[max_energy_idx]
    peak_pos = int(peak_row.get('order', max_energy_idx + 1))
    peak_min = str(peak_row.get('set_time', ''))
    harmonic_ok = int((pd.to_numeric(df.get('transition_score', 0), errors='coerce').fillna(0) >= 70).sum())
    big_moves = int((df.get('key_transition', pd.Series(dtype=str)) == '큰 키 이동').sum())
    bpm_changes = pd.to_numeric(df.get('bpm_change', 0), errors='coerce').abs().fillna(0)
    notes = []
    if preset_label:
        notes.append(f'{preset_label} 전개를 기준으로 {len(df)}곡을 배치했습니다.')
    if context:
        notes.append(f'공연 상황은 {context} 기준으로 해석했습니다.')
    notes.append(f'평균 BPM은 {avg_bpm:.1f}이며, 가장 높은 에너지는 {peak_pos}번 곡({peak_min})에서 형성됩니다.')
    notes.append(f'{max(0, len(df)-1)}개 전환 중 {max(0, harmonic_ok-1)}개가 비교적 안정적인 화성 연결입니다.')
    if big_moves:
        notes.append(f'큰 키 이동이 {big_moves}회 있어 브레이크, 에코 아웃 또는 퍼커시브 구간을 활용하는 편이 안전합니다.')
    if (bpm_changes > 5).any():
        notes.append('BPM 변화가 큰 구간은 루프나 하프/더블 타임 전환으로 실제 청취 확인을 권장합니다.')
    if float(df.iloc[-1]['energy']) < float(peak_row['energy']) - 1.5:
        notes.append('피크 이후 에너지를 낮춰 엔딩이 명확하게 느껴지도록 구성했습니다.')
    else:
        notes.append('마지막까지 에너지를 유지하는 방식이라 다음 DJ에게 넘기거나 앙코르로 이어가기 좋습니다.')
    return notes


def recommend_next_tracks(current: pd.Series, pool: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    rows = []
    current_genres = {g.strip().casefold() for g in str(current.get('genre', '')).replace('/', ',').split(',') if g.strip()}
    for idx, row in pool.iterrows():
        if str(row.get('title')) == str(current.get('title')) and str(row.get('artist')) == str(current.get('artist')):
            continue
        bpm_diff = effective_bpm_diff(float(current.get('bpm', 0) or 0), float(row.get('bpm', 0) or 0))
        key_cost = harmonic_cost(str(current.get('camelot', '')), str(row.get('camelot', '')))
        energy_diff = abs(float(current.get('energy', 5)) - float(row.get('energy', 5)))
        row_genres = {g.strip().casefold() for g in str(row.get('genre', '')).replace('/', ',').split(',') if g.strip()}
        genre_bonus = 1.0 if current_genres and row_genres and current_genres.intersection(row_genres) else 0.0
        score = 100 - min(45, bpm_diff * 5.5) - key_cost * 28 - min(24, energy_diff * 5) + genre_bonus * 7
        rows.append({
            '추천 점수': round(max(0, min(100, score))),
            '제목': row.get('title', ''), '아티스트': row.get('artist', ''),
            'BPM': row.get('bpm', 0), 'Camelot': row.get('camelot', ''), '에너지': row.get('energy', 0),
            '장르': row.get('genre', ''), '키 연결': harmonic_relation(str(current.get('camelot', '')), str(row.get('camelot', ''))),
            'BPM 차이': round(bpm_diff, 1), '원본 인덱스': idx,
        })
    return pd.DataFrame(rows).sort_values(['추천 점수', 'BPM 차이'], ascending=[False, True]).head(limit).reset_index(drop=True)


def analyze_history(df: pd.DataFrame) -> dict[str, Any]:
    data = df.copy().reset_index(drop=True)
    if data.empty:
        return {}
    bpm = pd.to_numeric(data['bpm'], errors='coerce').fillna(0)
    energy = pd.to_numeric(data.get('energy', 5), errors='coerce').fillna(5)
    transitions = []
    for i in range(1, len(data)):
        transitions.append({
            'from': f"{data.loc[i-1, 'artist']} – {data.loc[i-1, 'title']}",
            'to': f"{data.loc[i, 'artist']} – {data.loc[i, 'title']}",
            'bpm_diff': effective_bpm_diff(float(bpm.iloc[i-1]), float(bpm.iloc[i])),
            'key': harmonic_relation(str(data.loc[i-1, 'camelot']), str(data.loc[i, 'camelot'])),
            'key_score': round(100 * (1 - harmonic_cost(str(data.loc[i-1, 'camelot']), str(data.loc[i, 'camelot'])))),
        })
    trans = pd.DataFrame(transitions)
    peak_idx = int(energy.idxmax())
    genres = data['genre'].fillna('').astype(str)
    genre_counts = genres[genres.str.strip() != ''].value_counts().head(5).to_dict()
    return {
        'tracks': len(data), 'avg_bpm': round(float(bpm[bpm > 0].mean()), 1) if (bpm > 0).any() else 0,
        'bpm_range': f"{bpm[bpm>0].min():.1f}–{bpm.max():.1f}" if (bpm > 0).any() else '-',
        'avg_energy': round(float(energy.mean()), 1), 'peak_order': peak_idx + 1,
        'peak_track': f"{data.loc[peak_idx, 'artist']} – {data.loc[peak_idx, 'title']}",
        'harmonic_avg': round(float(trans['key_score'].mean()), 0) if not trans.empty else 100,
        'big_key_moves': int((trans['key'] == '큰 키 이동').sum()) if not trans.empty else 0,
        'large_bpm_moves': int((trans['bpm_diff'] > 5).sum()) if not trans.empty else 0,
        'genres': genre_counts, 'transitions': trans,
    }


def save_style_profile(analysis: dict[str, Any]) -> dict[str, Any]:
    old = {}
    if PROFILE_FILE.exists():
        try:
            old = json.loads(PROFILE_FILE.read_text(encoding='utf-8'))
        except Exception:
            old = {}
    count = int(old.get('sessions', 0))
    new_count = count + 1
    profile = {
        'sessions': new_count,
        'avg_bpm': round((float(old.get('avg_bpm', analysis.get('avg_bpm', 0))) * count + float(analysis.get('avg_bpm', 0))) / new_count, 1),
        'avg_energy': round((float(old.get('avg_energy', analysis.get('avg_energy', 0))) * count + float(analysis.get('avg_energy', 0))) / new_count, 1),
        'favorite_genres': analysis.get('genres', {}),
    }
    PROFILE_FILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    return profile


def load_style_profile() -> dict[str, Any]:
    if not PROFILE_FILE.exists():
        return {}
    try:
        return json.loads(PROFILE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def make_html_report(df: pd.DataFrame, notes: list[str], title: str = 'DPC SetLab Performance Report') -> bytes:
    rows = ''.join(
        f"<tr><td>{int(r.get('order', i+1))}</td><td>{html.escape(str(r.get('artist','')))}</td><td>{html.escape(str(r.get('title','')))}</td><td>{float(r.get('bpm',0)):.1f}</td><td>{html.escape(str(r.get('camelot','')))}</td><td>{float(r.get('energy',0)):.1f}</td></tr>"
        for i, (_, r) in enumerate(df.iterrows())
    )
    bullets = ''.join(f'<li>{html.escape(n)}</li>' for n in notes)
    body = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Arial,sans-serif;max-width:980px;margin:40px auto;line-height:1.55}}table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}h1{{margin-bottom:4px}}.muted{{color:#666}}</style>
<h1>{html.escape(title)}</h1><p class="muted">Estimated duration: {html.escape(format_seconds(float(df.attrs.get('estimated_duration_sec',0))))}</p>
<h2>AI Set Analysis</h2><ul>{bullets}</ul><h2>Set List</h2><table><thead><tr><th>#</th><th>Artist</th><th>Title</th><th>BPM</th><th>Key</th><th>Energy</th></tr></thead><tbody>{rows}</tbody></table></html>'''
    return body.encode('utf-8')
