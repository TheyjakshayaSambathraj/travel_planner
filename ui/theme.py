from __future__ import annotations

import streamlit as st

APP_VERSION = "1.0.0"
AGENT_COUNT = 8
PROVIDERS = ["Gemini", "Groq", "OpenRouter", "OpenAI"]

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-primary: #0b0f1a;
    --bg-secondary: #111827;
    --bg-card: rgba(17, 24, 39, 0.82);
    --border-glass: rgba(148, 163, 184, 0.22);
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
    --blue: #3b82f6;
    --purple: #8b5cf6;
    --emerald: #10b981;
    --shadow: 0 10px 40px rgba(0, 0, 0, 0.38);
    --section-gap: 2rem;
    --card-padding: 1.5rem;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: radial-gradient(ellipse at 15% 0%, rgba(59, 130, 246, 0.16) 0%, transparent 48%),
                radial-gradient(ellipse at 85% 15%, rgba(139, 92, 246, 0.14) 0%, transparent 42%),
                radial-gradient(ellipse at 50% 100%, rgba(16, 185, 129, 0.1) 0%, transparent 50%),
                var(--bg-primary);
    color: var(--text-primary);
}

#MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden;
    height: 0;
}

.main .block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 2rem;
    padding-bottom: 4rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
    max-width: 100%;
}

@media (min-width: 1440px) {
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 1680px;
        margin-left: auto;
        margin-right: auto;
    }
}

.page-section {
    margin-bottom: var(--section-gap);
}

.page-section-title {
    font-size: 1.65rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 0.35rem;
    letter-spacing: -0.02em;
}

.page-section-subtitle {
    color: var(--text-muted);
    font-size: 0.95rem;
    margin-bottom: 1.25rem;
}

/* Hero */
.hero-container {
    background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(139,92,246,0.18), rgba(16,185,129,0.12));
    border: 1px solid var(--border-glass);
    border-radius: 24px;
    padding: 2.5rem 3rem;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow);
    backdrop-filter: blur(18px);
}

.hero-title {
    font-size: 2.75rem;
    font-weight: 800;
    background: linear-gradient(90deg, #60a5fa, #a78bfa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.35rem;
    letter-spacing: -0.03em;
}

.hero-subtitle {
    font-size: 1.5rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.5rem;
}

.hero-tagline {
    color: var(--text-muted);
    font-size: 1rem;
    margin-bottom: 1.5rem;
}

.badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
}

.feature-badge {
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid var(--border-glass);
    border-radius: 999px;
    padding: 0.45rem 1rem;
    font-size: 0.82rem;
    color: #cbd5e1;
}

/* Dashboard */
.dashboard-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: 20px;
    padding: 1.75rem 2rem;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
    border-right: 1px solid var(--border-glass);
    min-width: 320px !important;
}

section[data-testid="stSidebar"] .block-container {
    padding: 1.25rem 1rem 2rem 1rem;
}

.sidebar-brand {
    font-size: 1.35rem;
    font-weight: 800;
    background: linear-gradient(90deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.sidebar-section-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 1rem 0 0.75rem 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.ai-status-box {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid var(--border-glass);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.75rem;
}

/* Tabs - pill style */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.65rem;
    background: rgba(15, 23, 42, 0.5);
    border-radius: 16px;
    padding: 0.45rem;
    border: 1px solid var(--border-glass);
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 999px !important;
    border: 1px solid transparent !important;
    color: var(--text-muted) !important;
    padding: 0.65rem 1.35rem !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    min-height: 44px;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, rgba(59,130,246,0.35), rgba(139,92,246,0.3)) !important;
    color: #f8fafc !important;
    border-color: rgba(96, 165, 250, 0.45) !important;
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.25) !important;
}

.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1.5rem;
}

/* Buttons */
div.stButton > button,
div.stDownloadButton > button {
    border-radius: 14px !important;
    padding: 0.85rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    min-height: 52px !important;
    transition: all 0.2s ease !important;
}

div.stButton > button[kind="primary"],
div.stDownloadButton > button[kind="primary"] {
    background: linear-gradient(90deg, var(--blue), var(--purple)) !important;
    border: none !important;
    box-shadow: 0 6px 24px rgba(59, 130, 246, 0.35) !important;
    color: white !important;
}

div.stButton > button[kind="primary"]:hover,
div.stDownloadButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(139, 92, 246, 0.45) !important;
}

div.stButton > button:not([kind="primary"]),
div.stDownloadButton > button:not([kind="primary"]) {
    border: 1px solid var(--border-glass) !important;
    background: rgba(30, 41, 59, 0.85) !important;
    color: #e2e8f0 !important;
}

div.stButton > button:not([kind="primary"]):hover,
div.stDownloadButton > button:not([kind="primary"]):hover {
    border-color: var(--blue) !important;
    background: rgba(59, 130, 246, 0.18) !important;
}

.action-bar {
    margin: 1.5rem 0 2rem 0;
}

/* Metrics */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(30,41,59,0.95), rgba(15,23,42,0.9));
    border: 1px solid var(--border-glass);
    border-radius: 16px;
    padding: 1.25rem 1rem !important;
    box-shadow: var(--shadow);
}

[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted) !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.65rem !important;
    font-weight: 800 !important;
    color: #f8fafc !important;
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
    background: rgba(15, 23, 42, 0.85) !important;
    border-color: var(--border-glass) !important;
    border-radius: 12px !important;
    color: #f1f5f9 !important;
    min-height: 44px;
}

.stMultiSelect [data-baseweb="tag"] {
    background: rgba(59, 130, 246, 0.28) !important;
    border-radius: 8px !important;
}

/* Expanders */
.streamlit-expanderHeader {
    background: rgba(30, 41, 59, 0.65) !important;
    border-radius: 14px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.85rem 1rem !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--border-glass);
    border-radius: 16px;
    margin-bottom: 1rem;
    overflow: hidden;
}

/* Progress */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--blue), var(--purple), var(--emerald)) !important;
    border-radius: 999px !important;
    height: 10px !important;
}

/* Containers with border */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    padding: var(--card-padding) !important;
    background: rgba(15, 23, 42, 0.55) !important;
    border-color: var(--border-glass) !important;
    margin-bottom: 1rem;
}

.divider-line {
    border: none;
    border-top: 1px solid var(--border-glass);
    margin: 2rem 0;
}

/* Compact mode */
body.compact-mode .main .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}

body.compact-mode [data-testid="stMetric"] {
    padding: 0.75rem 0.65rem !important;
}

body.compact-mode .hero-container {
    padding: 1.5rem 2rem;
}

body.compact-mode .dashboard-panel {
    padding: 1.25rem 1.5rem;
}

/* No animations */
body.no-animations * {
    transition: none !important;
    animation: none !important;
}

body.no-animations div.stButton > button:hover {
    transform: none !important;
}
"""


def inject_theme(
    compact_view: bool = False,
    animations_enabled: bool = True,
) -> None:
    extra_rules = ""
    if compact_view:
        extra_rules += """
body.compact-mode .main .block-container { padding-top: 1rem; padding-bottom: 2rem; }
body.compact-mode [data-testid="stMetric"] { padding: 0.75rem 0.65rem !important; }
body.compact-mode .hero-container { padding: 1.5rem 2rem; }
body.compact-mode .dashboard-panel { padding: 1.25rem 1.5rem; }
"""
    if not animations_enabled:
        extra_rules += """
body.no-animations * { transition: none !important; animation: none !important; }
body.no-animations div.stButton > button:hover { transform: none !important; }
"""

    body_class = ""
    if compact_view:
        body_class += " compact-mode"
    if not animations_enabled:
        body_class += " no-animations"

    st.markdown(
        f"<style>{BASE_CSS}{extra_rules}</style>",
        unsafe_allow_html=True,
    )
    if body_class.strip():
        st.markdown(
            f"<script>document.body.className = '{body_class.strip()}';</script>",
            unsafe_allow_html=True,
        )
