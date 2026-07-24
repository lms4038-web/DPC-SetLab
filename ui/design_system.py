from __future__ import annotations

import streamlit as st


APP_CSS = r"""
<style>
:root {
  --dpc-bg: #090b10;
  --dpc-panel: rgba(18, 21, 30, .88);
  --dpc-panel-strong: #11141d;
  --dpc-border: rgba(255, 255, 255, .085);
  --dpc-text: #f4f5f7;
  --dpc-muted: #979dab;
  --dpc-purple: #8b5cf6;
  --dpc-cyan: #22d3ee;
  --dpc-green: #34d399;
  --dpc-amber: #fbbf24;
}

html, body, [class*="css"] {font-family: Inter, Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;}
.stApp {
  background:
    radial-gradient(circle at 18% -10%, rgba(139, 92, 246, .17), transparent 31rem),
    radial-gradient(circle at 92% 4%, rgba(34, 211, 238, .10), transparent 27rem),
    var(--dpc-bg);
  color: var(--dpc-text);
}
.block-container {max-width: 1500px; padding-top: 5.4rem; padding-bottom: 5rem;}
header[data-testid="stHeader"] {background: rgba(9, 11, 16, .88); backdrop-filter: blur(16px); border-bottom:1px solid var(--dpc-border);}
header[data-testid="stHeader"] + div {scroll-margin-top:5rem;}
[data-testid="stSidebar"] {background: #0d1017; border-right: 1px solid var(--dpc-border);}
[data-testid="stSidebar"] .block-container {padding-top: 1.4rem;}

/* Hide Streamlit's default tab underline treatment and use deck-style tabs. */
.stTabs [data-baseweb="tab-list"] {
  position: sticky; top: 3.45rem; z-index: 999;
  gap: .42rem; overflow-x: auto; padding: .55rem .6rem .7rem; margin:-4.6rem 0 1rem;
  background:rgba(7,9,14,.96); backdrop-filter:blur(18px);
  border:1px solid var(--dpc-border); border-radius:1rem;
  box-shadow:0 14px 40px rgba(0,0,0,.30);
}
.stTabs [data-baseweb="tab"] {
  height: 3.1rem; border: 1px solid var(--dpc-border); border-radius: .72rem;
  background: rgba(255,255,255,.025); padding: 0 .95rem; color: var(--dpc-muted);
  white-space: nowrap; font-weight:700; letter-spacing:-.01em;
}
.stTabs [data-baseweb="tab"] p {font-size:.83rem;}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(139,92,246,.23), rgba(34,211,238,.08));
  border-color: rgba(139,92,246,.50); color: var(--dpc-text);
}
.stTabs [data-baseweb="tab-highlight"] {display:none;}

[data-testid="stMetric"] {
  background: var(--dpc-panel); border: 1px solid var(--dpc-border); border-radius: 1rem;
  padding: .95rem 1rem; box-shadow: 0 12px 35px rgba(0,0,0,.18);
}
[data-testid="stMetricLabel"] {color: var(--dpc-muted);}
[data-testid="stMetricValue"] {font-size: 1.55rem; letter-spacing: -.03em;}

div.stButton > button, div.stDownloadButton > button, a[data-testid="stLinkButton"] {
  border-radius: .72rem; border: 1px solid var(--dpc-border); min-height: 2.7rem;
  transition: transform .13s ease, border-color .13s ease, background .13s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover, a[data-testid="stLinkButton"]:hover {
  transform: translateY(-1px); border-color: rgba(139,92,246,.65);
}
button[kind="primary"] {
  background: linear-gradient(120deg, #7c3aed, #5b5ce2) !important;
  border: 0 !important; box-shadow: 0 8px 24px rgba(124,58,237,.25);
}

[data-testid="stFileUploader"] section, [data-testid="stDataFrame"],
[data-testid="stForm"], [data-testid="stExpander"] details {
  border-color: var(--dpc-border) !important; border-radius: .9rem !important;
}
hr {border-color: var(--dpc-border) !important;}

.dpc-brandline {display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.15rem 0 .7rem;}
.dpc-kicker {color:var(--dpc-cyan); font-size:.76rem; font-weight:750; letter-spacing:.16em; text-transform:uppercase;}
.dpc-version {color:var(--dpc-muted); font-size:.78rem; border:1px solid var(--dpc-border); border-radius:999px; padding:.28rem .58rem;}
.dpc-hero {
  position:relative; overflow:hidden; min-height:265px; padding:2.25rem 2.35rem;
  border:1px solid var(--dpc-border); border-radius:1.35rem;
  background: linear-gradient(135deg, rgba(20,23,34,.98), rgba(13,16,24,.94));
  box-shadow: 0 24px 70px rgba(0,0,0,.28); margin-bottom:1rem;
}
.dpc-hero:before {
  content:""; position:absolute; inset:0; pointer-events:none; opacity:.65;
  background:
    repeating-radial-gradient(ellipse at 79% 54%, transparent 0 17px, rgba(139,92,246,.16) 18px 20px, transparent 21px 34px),
    linear-gradient(115deg, transparent 0 54%, rgba(124,58,237,.12) 72%, rgba(34,211,238,.05) 100%);
  transform:skewY(-2deg) scale(1.08);
}
.dpc-hero:after {
  content:""; position:absolute; width:540px; height:540px; right:-155px; top:-255px;
  border-radius:50%; background:radial-gradient(circle, rgba(139,92,246,.38), transparent 66%);
}
.dpc-hero > * {position:relative;z-index:2;}
.dpc-hero h1 {font-size:clamp(2.2rem,4vw,4rem); line-height:.96; letter-spacing:-.055em; margin:.45rem 0 .8rem; max-width:850px;}
.dpc-hero p {color:#b1b6c2; max-width:720px; font-size:1.02rem; line-height:1.7; margin:0;}
.dpc-live-chip {display:inline-flex; align-items:center; gap:.45rem; color:#d8dcE5; font-size:.79rem; margin-top:1.2rem;}
.dpc-live-dot {width:.48rem;height:.48rem;border-radius:50%;background:var(--dpc-green);box-shadow:0 0 13px rgba(52,211,153,.8);}

.dpc-section-head {display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:1.35rem 0 .7rem;}
.dpc-section-head h2 {font-size:1.08rem; letter-spacing:-.02em; margin:0;}
.dpc-section-head span {color:var(--dpc-muted);font-size:.82rem;}
.dpc-card-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.72rem;margin:.2rem 0 1rem;}
.dpc-card {border:1px solid var(--dpc-border);border-radius:1rem;background:var(--dpc-panel);padding:1rem;min-height:112px;}
.dpc-card .label {color:var(--dpc-muted);font-size:.78rem;margin-bottom:.72rem;}
.dpc-card .value {font-size:1.03rem;font-weight:720;letter-spacing:-.02em;}
.dpc-card .sub {color:var(--dpc-muted);font-size:.76rem;margin-top:.35rem;line-height:1.45;}
.dpc-accent {color:#c4b5fd;}

.dpc-workflow {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.55rem;margin:.3rem 0 1.1rem;}
.dpc-step {position:relative;border:1px solid var(--dpc-border);border-radius:.85rem;padding:.85rem;background:rgba(255,255,255,.018);min-height:96px;}
.dpc-step.active {border-color:rgba(139,92,246,.68);background:linear-gradient(145deg,rgba(139,92,246,.18),rgba(255,255,255,.02));}
.dpc-step .num {color:var(--dpc-cyan);font-size:.7rem;font-weight:800;letter-spacing:.12em;}
.dpc-step .name {font-size:.88rem;font-weight:720;margin-top:.48rem;}
.dpc-step .desc {font-size:.7rem;color:var(--dpc-muted);margin-top:.25rem;line-height:1.35;}

.dpc-empty {border:1px dashed rgba(255,255,255,.14);border-radius:1rem;padding:1.2rem;color:var(--dpc-muted);background:rgba(255,255,255,.014);}
.small-note {color:var(--dpc-muted); font-size:.86rem;}
div[role="radiogroup"] {gap:.45rem;flex-wrap:wrap;}
div[role="radiogroup"] label {border:1px solid var(--dpc-border);border-radius:.75rem;padding:.55rem .75rem;background:rgba(255,255,255,.025);}

@media (max-width: 900px) {.block-container{padding-top:6.2rem}.stTabs [data-baseweb="tab-list"]{top:3.35rem;margin-top:-5.15rem}}
@media (max-width: 1100px) {.dpc-card-grid {grid-template-columns:repeat(2,minmax(0,1fr));}.dpc-workflow{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width: 650px) {.block-container{padding-left:1rem;padding-right:1rem;padding-top:6.6rem}.stTabs [data-baseweb="tab-list"]{top:3.25rem;border-radius:.8rem;padding:.45rem}.stTabs [data-baseweb="tab"]{height:2.75rem;padding:0 .75rem}.dpc-hero{padding:1.55rem 1.3rem;min-height:225px}.dpc-card-grid,.dpc-workflow{grid-template-columns:1fr}.dpc-hero h1{font-size:2.35rem}}
</style>
"""


def apply_design_system() -> None:
    """Apply the shared 4.x visual system once per Streamlit rerun."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
