"""
CodeSense - Reusable UI Components
Streamlit components for scores, issues, DSA cards, feedback panels, etc.
"""

import streamlit as st
from typing import Dict, List, Optional

from constants import (
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR,
)


# ─── CSS ──────────────────────────────────────────────────────────────────────

GLOBAL_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;1,400&display=swap');

  /* ── 1. DARK THEME PALETTE (Default Base) ────────────────────────────────── */
  :root,
  [data-theme="dark"],
  .stApp[data-theme="dark"],
  body[data-theme="dark"] {
    --app-bg: radial-gradient(circle at 50% 0%, #1E1B4B 0%, #0F0F17 75%);
    --card-bg: rgba(24, 25, 38, 0.85);
    --card-inner-bg: rgba(30, 30, 46, 0.9);
    --card-border: rgba(255, 255, 255, 0.09);
    --text-title: #F8FAFC;
    --text-body: #CBD5E1;
    --text-muted: #94A3B8;
    --input-bg: rgba(24, 25, 38, 0.9);
    --input-border: rgba(255, 255, 255, 0.15);
    --pill-bg: rgba(255, 255, 255, 0.06);
    --tab-bar-bg: rgba(15, 15, 23, 0.6);
    --accent-glow: rgba(99, 102, 241, 0.4);
    --shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    --code-bg: #181926;
    --btn-primary-bg: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%);
    --btn-primary-text: #FFFFFF;
    --btn-secondary-bg: rgba(24, 25, 38, 0.75);
    --btn-secondary-text: #F8FAFC;
    --btn-secondary-border: rgba(255, 255, 255, 0.12);
    --sidebar-bg: rgba(15, 15, 23, 0.85);
    --sidebar-border: rgba(255, 255, 255, 0.08);
  }

  /* ── 2. LIGHT THEME PALETTE ─────────────────────────────────────────────── */
  [data-theme="light"],
  .stApp[data-theme="light"],
  body[data-theme="light"] {
    --app-bg: linear-gradient(180deg, #F8FAFC 0%, #EEF2FF 100%);
    --card-bg: #FFFFFF;
    --card-inner-bg: #F1F5F9;
    --card-border: #E2E8F0;
    --text-title: #0F172A;
    --text-body: #334155;
    --text-muted: #64748B;
    --input-bg: #FFFFFF;
    --input-border: #CBD5E1;
    --pill-bg: #F1F5F9;
    --tab-bar-bg: #E2E8F0;
    --accent-glow: rgba(79, 70, 229, 0.15);
    --shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
    --code-bg: #F8FAFC;
    --btn-primary-bg: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%);
    --btn-primary-text: #FFFFFF;
    --btn-secondary-bg: #FFFFFF;
    --btn-secondary-text: #0F172A;
    --btn-secondary-border: #CBD5E1;
    --sidebar-bg: #FFFFFF;
    --sidebar-border: #E2E8F0;
  }

  /* ── 3. OS System Light Preference (when not explicitly forced dark) ────── */
  @media (prefers-color-scheme: light) {
    :root:not([data-theme="dark"]),
    .stApp:not([data-theme="dark"]),
    body:not([data-theme="dark"]) {
      --app-bg: linear-gradient(180deg, #F8FAFC 0%, #EEF2FF 100%);
      --card-bg: #FFFFFF;
      --card-inner-bg: #F1F5F9;
      --card-border: #E2E8F0;
      --text-title: #0F172A;
      --text-body: #334155;
      --text-muted: #64748B;
      --input-bg: #FFFFFF;
      --input-border: #CBD5E1;
      --pill-bg: #F1F5F9;
      --tab-bar-bg: #E2E8F0;
      --accent-glow: rgba(79, 70, 229, 0.15);
      --shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
      --code-bg: #F8FAFC;
      --btn-primary-bg: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%);
      --btn-primary-text: #FFFFFF;
      --btn-secondary-bg: #FFFFFF;
      --btn-secondary-text: #0F172A;
      --btn-secondary-border: #CBD5E1;
      --sidebar-bg: #FFFFFF;
      --sidebar-border: #E2E8F0;
    }
  }

  html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  }
  code, pre, .stCodeBlock {
    font-family: 'JetBrains Mono', monospace !important;
  }

  /* Transparent Streamlit Header */
  [data-testid="stHeader"] {
    background: transparent !important;
    backdrop-filter: none !important;
  }
  [data-testid="stHeader"] * {
    color: var(--text-title) !important;
  }

  /* App Background & Typography */
  .stApp, [data-testid="stAppViewContainer"] {
    background: var(--app-bg) !important;
    color: var(--text-title) !important;
  }
  .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: var(--text-title) !important;
  }
  .stApp label, .stApp label p {
    color: var(--text-title) !important;
    font-weight: 600 !important;
  }
  .stApp p {
    color: var(--text-body);
  }

  /* Text inputs, text areas, and password fields */
  .stTextInput input, .stTextArea textarea {
    background-color: var(--input-bg) !important;
    color: var(--text-title) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 10px !important;
  }
  .stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 10px var(--accent-glow) !important;
  }

  /* Selectboxes (BaseWeb Div Structure - Fixes Pitch Black Selectbox Conflicts) */
  div[data-baseweb="select"] > div {
    background-color: var(--input-bg) !important;
    color: var(--text-title) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 10px !important;
  }
  div[data-baseweb="select"] span,
  div[data-baseweb="select"] div {
    color: var(--text-title) !important;
  }
  div[data-baseweb="popover"] > div,
  div[data-baseweb="popover"] ul {
    background-color: var(--card-bg) !important;
    color: var(--text-title) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 10px !important;
  }
  div[data-baseweb="popover"] li {
    color: var(--text-title) !important;
  }
  div[data-baseweb="popover"] li:hover {
    background-color: var(--pill-bg) !important;
  }

  /* Primary & Form Submit Buttons */
  [data-testid="stFormSubmitButton"] button,
  .stButton > button[kind="primary"] {
    background: var(--btn-primary-bg) !important;
    color: var(--btn-primary-text) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 4px 14px var(--accent-glow) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  }
  [data-testid="stFormSubmitButton"] button:hover,
  .stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 8px 25px var(--accent-glow) !important;
    opacity: 0.95 !important;
  }

  /* Secondary Buttons */
  .stButton > button {
    background: var(--btn-secondary-bg) !important;
    color: var(--btn-secondary-text) !important;
    border: 1px solid var(--btn-secondary-border) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  }
  .stButton > button:hover {
    transform: translateY(-2px) scale(1.01) !important;
    border-color: #6366F1 !important;
    box-shadow: 0 4px 14px var(--accent-glow) !important;
  }

  /* Sidebar Styling */
  [data-testid="stSidebar"] {
    background: var(--sidebar-bg) !important;
    backdrop-filter: blur(16px) !important;
    border-right: 1px solid var(--sidebar-border) !important;
  }
  [data-testid="stSidebar"] .stButton > button {
    background: var(--pill-bg) !important;
    color: var(--text-title) !important;
    border: 1px solid var(--card-border) !important;
    box-shadow: none !important;
    justify-content: flex-start !important;
    text-align: left !important;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: var(--tab-bar-bg) !important;
    border-color: #6366F1 !important;
    color: var(--text-title) !important;
  }

  /* Tabs (Segmented Floating Pill Design) */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: var(--tab-bar-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 14px !important;
    padding: 6px !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.05) !important;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 10px 22px !important;
    color: var(--text-muted) !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid transparent !important;
  }
  .stTabs [data-baseweb="tab"]:hover {
    color: var(--text-title) !important;
    background: rgba(99, 102, 241, 0.1) !important;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 18px var(--accent-glow) !important;
    border-color: rgba(255, 255, 255, 0.15) !important;
  }

  /* Modern Card */
  .cs-card {
    background: var(--card-bg) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 16px !important;
    padding: 22px 26px !important;
    margin-bottom: 18px !important;
    box-shadow: var(--shadow) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  }
  .cs-card:hover {
    border-color: rgba(99, 102, 241, 0.4) !important;
    box-shadow: 0 14px 40px -10px var(--accent-glow) !important;
    transform: translateY(-2px);
  }
  .cs-card-header {
    font-size: 19px;
    font-weight: 700;
    margin-bottom: 14px;
    color: var(--text-title);
    letter-spacing: -0.01em;
  }

  /* Score ring styling */
  .score-ring {
    display: flex;
    align-items: center;
    gap: 24px;
  }
  .score-number {
    font-size: 58px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.03em;
  }
  .grade-badge {
    display: inline-block;
    padding: 5px 18px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.02em;
    box-shadow: 0 0 15px var(--accent-glow);
  }

  /* Issue severity left borders */
  .sev-error   { border-left: 4px solid #EF4444 !important; }
  .sev-warning { border-left: 4px solid #F59E0B !important; }
  .sev-info    { border-left: 4px solid #06B6D4 !important; }
  .sev-positive{ border-left: 4px solid #10B981 !important; }

  /* Metric pill */
  .metric-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--pill-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 7px 15px;
    font-size: 13px;
    color: var(--text-body);
    margin: 4px;
    transition: all 0.2s ease;
  }
  .metric-pill:hover {
    border-color: rgba(99, 102, 241, 0.3);
  }
  .metric-pill b { color: var(--text-title); }

  /* Badges */
  .badge {
    display: inline-block;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .badge-critical { background: #EF4444; color: #fff; box-shadow: 0 0 10px rgba(239,68,68,0.4); }
  .badge-high     { background: #F97316; color: #fff; }
  .badge-medium   { background: #F59E0B; color: #000; }
  .badge-low      { background: #10B981; color: #fff; }
  .badge-info     { background: #06B6D4; color: #fff; }

  /* Step indicator */
  .step-circle {
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3B82F6 0%, #6366F1 100%);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 800;
    flex-shrink: 0;
    box-shadow: 0 4px 12px var(--accent-glow);
  }

  /* Progress bar */
  .cs-progress-bar {
    background: var(--pill-bg);
    border-radius: 999px;
    height: 9px;
    overflow: hidden;
    margin: 8px 0;
  }
  .cs-progress-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* Off-screen theme sync iframe — keeps JavaScript execution active while taking 0px */
  iframe[title*="st.iframe"],
  iframe[height="0"],
  div[data-testid="stIFrame"]:has(iframe),
  div:has(> iframe[title*="st.iframe"]) {
    position: fixed !important;
    top: -9999px !important;
    left: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    opacity: 0 !important;
    pointer-events: none !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
  }
</style>
"""

def inject_css() -> None:
    """
    Injects CodeSense CSS and attaches an active client-side theme observer.
    Theme is controlled exclusively by Streamlit's built-in 3-dots switcher (Light / Dark / System).
    Uses Streamlit's native st.iframe for guaranteed JavaScript execution with zero warnings.
    """
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    theme_sync_script = """
    <script>
      (function() {
        try {
          var pDoc = window.parent.document;
          var pWin = window.parent;

          function sync() {
            var stTheme = pWin.localStorage.getItem('stActiveTheme-/-v2');
            var bodyBg = pWin.getComputedStyle(pDoc.body).backgroundColor;
            var isLight = false;
            if (stTheme && stTheme.indexOf('Light') !== -1) {
              isLight = true;
            } else if (stTheme && stTheme.indexOf('Dark') !== -1) {
              isLight = false;
            } else if (bodyBg === 'rgb(255, 255, 255)' || bodyBg === '#ffffff') {
              isLight = true;
            } else if (bodyBg === 'rgb(14, 17, 23)' || bodyBg === '#0e1117') {
              isLight = false;
            } else {
              isLight = pWin.matchMedia && pWin.matchMedia('(prefers-color-scheme: light)').matches;
            }
            var theme = isLight ? 'light' : 'dark';
            if (pDoc.documentElement.getAttribute('data-theme') !== theme) {
              pDoc.documentElement.setAttribute('data-theme', theme);
              pDoc.body.setAttribute('data-theme', theme);
              var app = pDoc.querySelector('.stApp');
              if (app) app.setAttribute('data-theme', theme);
            }
          }

          sync();

          if (!pWin.__cs_theme_sync_attached) {
            pWin.__cs_theme_sync_attached = true;
            pWin.addEventListener('storage', function(e) {
              if (e.key === 'stActiveTheme-/-v2') sync();
            });
            var obs = new MutationObserver(function() { sync(); });
            obs.observe(pDoc.head, { childList: true, subtree: true });
            if (pWin.matchMedia) {
              pWin.matchMedia('(prefers-color-scheme: light)').addEventListener('change', sync);
            }
            pWin.__cs_sync_loop = pWin.setInterval(sync, 150);
          }
        } catch(e) {}
      })();
    </script>
    """
    st.iframe(theme_sync_script, width=1, height=1)


# ─── Score Display ────────────────────────────────────────────────────────────

def score_card(score: float, grade: str, confidence: float,
               label: str = "", improvement: Optional[float] = None) -> None:
    """
    Score card using st.columns layout — avoids nested HTML divs which
    Streamlit's sanitizer strips, causing raw </div> text to appear.
    """
    color = _score_color(score)
    lbl   = label or _score_label(score)
    pct   = int(score)

    # Outer card shell — adaptive CSS variables for dark/light themes
    st.markdown(
        f'<div style="background:var(--card-inner-bg);border:1px solid var(--card-border);border-radius:12px;padding:16px 20px;margin-bottom:8px">',
        unsafe_allow_html=True,
    )
    col_ring, col_info = st.columns([1, 1.6])

    with col_ring:
        # Flat ring using span elements only (no nested divs)
        st.markdown(f"""
<span style="display:block;width:90px;height:90px;border-radius:50%;
             background:conic-gradient({color} {pct}%,var(--card-border) {pct}%);
             display:flex;align-items:center;justify-content:center;margin:auto">
  <span style="background:var(--card-inner-bg);width:68px;height:68px;border-radius:50%;
               display:flex;flex-direction:column;align-items:center;justify-content:center">
    <b style="font-size:22px;color:{color};line-height:1.1">{score:.0f}</b>
    <small style="font-size:10px;color:var(--text-muted)">/100</small>
  </span>
</span>""", unsafe_allow_html=True)

    with col_info:
        st.markdown(f'<b style="font-size:36px;color:{color}">{grade}</b>',
                    unsafe_allow_html=True)
        st.markdown(f'<span style="color:var(--text-body);font-size:13px;display:block">{lbl}</span>',
                    unsafe_allow_html=True)
        st.markdown(f'<span style="color:var(--text-muted);font-size:11px">±{confidence:.1f} confidence</span>',
                    unsafe_allow_html=True)
        if improvement is not None:
            sign   = "+" if improvement >= 0 else ""
            color2 = COLOR_SUCCESS if improvement >= 0 else COLOR_ERROR
            st.markdown(
                f'<span style="color:{color2};font-size:12px;display:block;margin-top:4px">' +
                f'{sign}{improvement:.1f} pts vs last</span>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)


def progress_bar(value: float, max_val: float = 100,
                 color: str = COLOR_PRIMARY, label: str = "") -> None:
    pct = min(100, value / max_val * 100) if max_val else 0
    st.markdown(f"""
    <div style="margin:4px 0">
      {"<small style='color:var(--text-muted)'>" + label + "</small>" if label else ""}
      <div class="cs-progress-bar">
        <div class="cs-progress-fill" style="width:{pct}%;background:{color}"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Issue Cards ─────────────────────────────────────────────────────────────

def issue_card(item: Dict) -> None:
    """
    Render an issue card using CSS variables for dark & light mode support.
    """
    sev   = item.get("severity", "info")
    title = item.get("title", "")
    msg   = item.get("message", "")
    line  = item.get("line")
    bef   = item.get("code_before", "")
    aft   = item.get("code_after", "")
    res   = item.get("resource")

    border = {
        "error":    "#E53935",
        "warning":  "#F59E0B",
        "info":     "#00ACC1",
        "positive": "#43A047",
    }.get(sev, "#757575")

    line_badge = (
        f'<span style="color:var(--text-muted);font-size:12px;margin-left:8px">Line {line}</span>'
        if line else ""
    )

    resource_html = ""
    if res and res.get("url"):
        resource_html = (
            f'<a href="{res["url"]}" target="_blank" '
            f'style="color:#1E88E5;font-size:12px;text-decoration:none">'
            f'📖 {res.get("title","Learn more")}</a>'
        )

    # Header rendered via st.markdown with CSS variables
    st.markdown(f"""
    <div style="border-left:4px solid {border};background:var(--card-inner-bg);border-radius:0 8px 8px 0;
                padding:12px 16px;margin-bottom:4px;border:1px solid var(--card-border);
                border-left:4px solid {border}">
      <div style="font-weight:600;color:var(--text-title);font-size:14px">{_esc(title)}{line_badge}</div>
      <div style="color:var(--text-body);font-size:13px;margin-top:4px">{_esc(msg)}</div>
      <div style="margin-top:6px">{resource_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Code snippets via st.code — completely bypasses HTML sanitizer
    if bef:
        st.caption("📄 Your code:")
        st.code(bef, language="python")
    if aft:
        st.caption("✅ Suggestion:")
        st.code(aft, language="python")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ─── DSA Cards ───────────────────────────────────────────────────────────────

def algo_card(algo: Dict) -> None:
    cx    = algo.get("complexity", {})
    conf  = int(algo.get("confidence", 0) * 100)
    color = COLOR_SUCCESS if cx.get("avg", "").startswith("O(log") or \
            cx.get("avg", "").startswith("O(n log") else COLOR_WARNING

    st.markdown(f"""
    <div class="cs-card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600;color:var(--text-title)">🧠 {algo['display_name']}</span>
        <span class="badge badge-info">{algo.get('category','')}</span>
      </div>
      <div style="color:var(--text-muted);font-size:13px;margin:6px 0">
        Lines {algo.get('start_line','?')}–{algo.get('end_line','?')} &nbsp;|&nbsp;
        Confidence: {conf}%
      </div>
      <div style="margin:8px 0">
        <span class="metric-pill">⏱ Best <b>{cx.get('best','?')}</b></span>
        <span class="metric-pill">⏱ Avg <b>{cx.get('avg','?')}</b></span>
        <span class="metric-pill">⏱ Worst <b>{cx.get('worst','?')}</b></span>
        <span class="metric-pill">💾 Space <b>{cx.get('space','?')}</b></span>
      </div>
      <div style="color:var(--text-body);font-size:13px;font-style:italic">{algo.get('reason','')}</div>
      {"<div style='margin-top:8px;color:#F59E0B;font-size:13px'>💡 " + algo.get('suggestion','') + "</div>" if algo.get('suggestion') else ""}
    </div>
    """, unsafe_allow_html=True)


def ds_chip(ds: Dict) -> None:
    st.markdown(
        f'<span class="metric-pill">📦 <b>{ds["display_name"]}</b> (line {ds["line"]})</span>',
        unsafe_allow_html=True,
    )


# ─── Stats Metrics Row ───────────────────────────────────────────────────────

def stat_row(items: List[Dict]) -> None:
    """
    Render a horizontal row of stat cards.
    Each item: {label, value, delta, color, icon}
    """
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            delta_html = ""
            if "delta" in item and item["delta"] is not None:
                d = item["delta"]
                c = COLOR_SUCCESS if d >= 0 else COLOR_ERROR
                delta_html = f'<div style="color:{c};font-size:12px">{"▲" if d >= 0 else "▼"} {abs(d):.1f}</div>'
            col.markdown(f"""
            <div class="cs-card" style="text-align:center;padding:16px">
              <div style="font-size:24px">{item.get('icon','')}</div>
              <div style="font-size:28px;font-weight:700;color:{item.get('color', COLOR_PRIMARY)}">{item['value']}</div>
              <div style="color:var(--text-muted);font-size:13px">{item['label']}</div>
              {delta_html}
            </div>
            """, unsafe_allow_html=True)


# ─── Loading States ───────────────────────────────────────────────────────────

def loading_spinner(message: str = "Analyzing your code...") -> None:
    st.markdown(f"""
    <div style="text-align:center;padding:40px">
      <div style="font-size:32px;animation:spin 1s linear infinite">⚙️</div>
      <div style="color:var(--text-muted);margin-top:12px">{message}</div>
    </div>
    <style>@keyframes spin {{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}</style>
    """, unsafe_allow_html=True)


# ─── Achievement Badge ───────────────────────────────────────────────────────

def achievement_badge(title: str, icon: str, description: str) -> None:
    st.markdown(f"""
    <div class="cs-card" style="display:flex;align-items:center;gap:16px;padding:12px 20px">
      <div style="font-size:36px">{icon}</div>
      <div>
        <div style="font-weight:600;color:var(--text-title)">{title}</div>
        <div style="color:var(--text-muted);font-size:13px">{description}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Diff Viewer ─────────────────────────────────────────────────────────────

def render_diff_viewer(before: str, after: str, explanation: str = "", language: str = "python") -> None:
    """Render a GitHub-style side-by-side / unified code diff viewer with syntax highlights."""
    import difflib
    
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = difflib.SequenceMatcher(None, before_lines, after_lines)
    
    diff_html_lines = []
    add_count, del_count = 0, 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in before_lines[i1:i2]:
                diff_html_lines.append(f'<div class="diff-line diff-equal"><span class="diff-num"> </span><span class="diff-prefix"> </span><span class="diff-text">{_esc(line)}</span></div>')
        elif tag == 'delete':
            for line in before_lines[i1:i2]:
                del_count += 1
                diff_html_lines.append(f'<div class="diff-line diff-del"><span class="diff-num">-</span><span class="diff-prefix">-</span><span class="diff-text">{_esc(line)}</span></div>')
        elif tag == 'insert':
            for line in after_lines[j1:j2]:
                add_count += 1
                diff_html_lines.append(f'<div class="diff-line diff-add"><span class="diff-num">+</span><span class="diff-prefix">+</span><span class="diff-text">{_esc(line)}</span></div>')
        elif tag == 'replace':
            for line in before_lines[i1:i2]:
                del_count += 1
                diff_html_lines.append(f'<div class="diff-line diff-del"><span class="diff-num">-</span><span class="diff-prefix">-</span><span class="diff-text">{_esc(line)}</span></div>')
            for line in after_lines[j1:j2]:
                add_count += 1
                diff_html_lines.append(f'<div class="diff-line diff-add"><span class="diff-num">+</span><span class="diff-prefix">+</span><span class="diff-text">{_esc(line)}</span></div>')

    diff_body = "".join(diff_html_lines)
    explanation_html = f'<div style="margin-top:10px;font-size:13px;color:var(--text-muted);border-top:1px solid var(--card-border);padding-top:8px">💡 <b>Explanation:</b> {_esc(explanation)}</div>' if explanation else ""

    st.markdown(f"""
    <div style="background:var(--code-bg);border:1px solid var(--card-border);border-radius:8px;padding:12px;margin-bottom:12px;font-family:'JetBrains Mono',monospace;font-size:13px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;border-bottom:1px solid var(--card-border);padding-bottom:6px">
        <span style="color:var(--text-title);font-weight:600">Unified Diff</span>
        <div>
          <span style="color:#43A047;font-weight:600;margin-right:8px">+{add_count}</span>
          <span style="color:#E53935;font-weight:600">-{del_count}</span>
        </div>
      </div>
      <div style="overflow-x:auto;max-height:300px;line-height:1.5">
        {diff_body}
      </div>
      {explanation_html}
    </div>
    <style>
      .diff-line {{ display:flex; padding:2px 4px; border-radius:2px; }}
      .diff-equal {{ color: var(--text-body); }}
      .diff-del {{ background: rgba(229, 57, 53, 0.15); color: #EF5350; }}
      .diff-add {{ background: rgba(67, 160, 71, 0.15); color: #66BB6A; }}
      .diff-num {{ width: 20px; user-select: none; opacity: 0.6; }}
      .diff-prefix {{ width: 14px; user-select: none; font-weight: bold; }}
      .diff-text {{ flex: 1; white-space: pre-wrap; }}
    </style>
    """, unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _score_color(score: float) -> str:
    if score >= 85: return COLOR_SUCCESS
    if score >= 70: return COLOR_PRIMARY
    if score >= 50: return COLOR_WARNING
    return COLOR_ERROR


def _score_label(score: float) -> str:
    if score >= 90: return "Excellent"
    if score >= 75: return "Good"
    if score >= 60: return "Average"
    if score >= 40: return "Below Average"
    return "Poor"


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))