from __future__ import annotations

import streamlit as st

APP_VERSION = "2.0.0"
AGENT_COUNT = 8
PROVIDERS = ["Gemini", "Groq", "OpenRouter", "OpenAI"]

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800;0,14..32,900;1,14..32,400&family=Outfit:wght@400;500;600;700;800;900&display=swap');

/* ── Reset & Root ───────────────────────────────────────────────────────── */
:root {
    --bg-primary:     #080c14;
    --bg-secondary:   #0d1220;
    --bg-card:        rgba(15, 22, 40, 0.82);
    --bg-card-hover:  rgba(20, 30, 55, 0.92);
    --border-glass:   rgba(148, 163, 184, 0.18);
    --border-active:  rgba(96, 165, 250, 0.45);
    --text-primary:   #f1f5f9;
    --text-secondary: #cbd5e1;
    --text-muted:     #64748b;
    --blue:           #3b82f6;
    --blue-light:     #60a5fa;
    --purple:         #8b5cf6;
    --purple-light:   #a78bfa;
    --emerald:        #10b981;
    --emerald-light:  #34d399;
    --amber:          #f59e0b;
    --red:            #ef4444;
    --shadow-sm:      0 2px 8px rgba(0,0,0,0.3);
    --shadow-md:      0 8px 32px rgba(0,0,0,0.4);
    --shadow-lg:      0 20px 60px rgba(0,0,0,0.5);
    --shadow-glow:    0 0 40px rgba(59,130,246,0.2);
    --section-gap:    2.25rem;
    --card-padding:   1.5rem;
    --radius-sm:      10px;
    --radius-md:      16px;
    --radius-lg:      24px;
    --radius-xl:      32px;
    --nav-width:      270px;
    --nav-collapsed:  0px;
    --transition:     0.3s cubic-bezier(0.4,0,0.2,1);
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* ── App Background ─────────────────────────────────────────────────────── */
.stApp {
    background:
        radial-gradient(ellipse 80% 50% at 10% -10%, rgba(59,130,246,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 90% 10%,  rgba(139,92,246,0.14) 0%, transparent 50%),
        radial-gradient(ellipse 70% 50% at 50% 110%, rgba(16,185,129,0.10) 0%, transparent 60%),
        var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
}

/* ── Hide default Streamlit chrome ─────────────────────────────────────── */
#MainMenu,
footer,
header[data-testid="stHeader"],
section[data-testid="stSidebar"],
[data-testid="collapsedControl"],
.stDeployButton {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
}

/* ── Main content area ──────────────────────────────────────────────────── */
.main .block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 1.25rem;
    padding-bottom: 5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100%;
}

@media (min-width: 1440px) {
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 1600px;
        margin: 0 auto;
    }
}

/* ── Top Navigation Bar ─────────────────────────────────────────────────── */
.tm-topbar {
    position: sticky;
    top: 0;
    z-index: 1100;
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.65rem 1.5rem;
    background: rgba(8, 12, 20, 0.92);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-bottom: 1px solid var(--border-glass);
    margin-bottom: 1.5rem;
}

.tm-topbar-brand {
    font-family: 'Outfit', sans-serif;
    font-size: 1.25rem;
    font-weight: 800;
    background: linear-gradient(90deg, var(--blue-light), var(--purple-light), var(--emerald-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    margin-right: auto;
}

.tm-topbar-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.tm-hamburger {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-glass);
    background: rgba(30, 41, 59, 0.6);
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    transition: all var(--transition);
    flex-shrink: 0;
}
.tm-hamburger:hover {
    background: rgba(59, 130, 246, 0.2);
    border-color: var(--border-active);
    color: var(--text-primary);
}

.tm-new-trip-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.5rem 1rem;
    border-radius: var(--radius-sm);
    background: linear-gradient(90deg, var(--blue), var(--purple));
    color: white;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: all var(--transition);
    box-shadow: 0 4px 16px rgba(59,130,246,0.3);
    text-decoration: none;
}
.tm-new-trip-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(139,92,246,0.45);
}

/* ── Custom Navigation Panel ────────────────────────────────────────────── */
.tm-nav-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1199;
    backdrop-filter: blur(4px);
}
.tm-nav-overlay.visible { display: block; }

.tm-nav {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: var(--nav-width);
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1526 100%);
    border-right: 1px solid var(--border-glass);
    z-index: 1200;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transform: translateX(-100%);
    transition: transform var(--transition);
    box-shadow: var(--shadow-lg);
}
.tm-nav.open { transform: translateX(0); }

.tm-nav-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.25rem 1.25rem 1rem 1.25rem;
    border-bottom: 1px solid var(--border-glass);
    flex-shrink: 0;
}

.tm-nav-brand {
    font-family: 'Outfit', sans-serif;
    font-size: 1.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, var(--blue-light), var(--purple-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.tm-nav-close {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: 1px solid var(--border-glass);
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    transition: all var(--transition);
}
.tm-nav-close:hover {
    background: rgba(239,68,68,0.2);
    border-color: rgba(239,68,68,0.4);
    color: #fca5a5;
}

.tm-nav-section {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    padding: 1rem 1.25rem 0.4rem 1.25rem;
}

.tm-nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.25rem;
    color: var(--text-secondary);
    font-size: 0.925rem;
    font-weight: 500;
    cursor: pointer;
    border-radius: var(--radius-sm);
    margin: 0.1rem 0.5rem;
    transition: all var(--transition);
    border: 1px solid transparent;
    text-decoration: none;
}
.tm-nav-item:hover {
    background: rgba(59,130,246,0.12);
    border-color: rgba(96,165,250,0.2);
    color: var(--text-primary);
}
.tm-nav-item.active {
    background: linear-gradient(90deg, rgba(59,130,246,0.2), rgba(139,92,246,0.15));
    border-color: var(--border-active);
    color: var(--blue-light);
    font-weight: 600;
}

.tm-nav-item-icon { font-size: 1.1rem; flex-shrink: 0; }

.tm-nav-footer {
    margin-top: auto;
    padding: 1rem 1.25rem;
    border-top: 1px solid var(--border-glass);
    flex-shrink: 0;
}

.tm-nav-status {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.8rem;
    color: var(--text-muted);
}

.tm-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--emerald);
    box-shadow: 0 0 8px var(--emerald);
    animation: pulse-dot 2s infinite;
    flex-shrink: 0;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* ── Hero Section ───────────────────────────────────────────────────────── */
.hero-container {
    background: linear-gradient(135deg,
        rgba(59,130,246,0.22) 0%,
        rgba(139,92,246,0.18) 50%,
        rgba(16,185,129,0.12) 100%);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-xl);
    padding: 2.75rem 3.5rem;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow-md), var(--shadow-glow);
    backdrop-filter: blur(18px);
    position: relative;
    overflow: hidden;
}
.hero-container::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(139,92,246,0.12), transparent 60%);
    pointer-events: none;
}

.hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: 3rem;
    font-weight: 900;
    background: linear-gradient(90deg, var(--blue-light), var(--purple-light), var(--emerald-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.4rem;
    letter-spacing: -0.04em;
    line-height: 1;
}
.hero-subtitle {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
    letter-spacing: -0.02em;
}
.hero-tagline {
    color: var(--text-muted);
    font-size: 1rem;
    margin-bottom: 1.75rem;
}

.badge-row { display: flex; flex-wrap: wrap; gap: 0.6rem; }

.feature-badge {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(96,165,250,0.25);
    border-radius: 999px;
    padding: 0.4rem 1rem;
    font-size: 0.8rem;
    color: var(--text-secondary);
    font-weight: 500;
    transition: all var(--transition);
}
.feature-badge:hover {
    border-color: var(--border-active);
    background: rgba(59,130,246,0.15);
    color: var(--blue-light);
}

/* ── Destination Hero Banner ─────────────────────────────────────────────── */
.dest-hero-banner {
    position: relative;
    width: 100%;
    height: 320px;
    border-radius: var(--radius-xl);
    overflow: hidden;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow-lg);
}
.dest-hero-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.6s ease;
}
.dest-hero-banner:hover .dest-hero-img {
    transform: scale(1.04);
}
.dest-hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        to bottom,
        transparent 20%,
        rgba(8,12,20,0.5) 55%,
        rgba(8,12,20,0.9) 100%
    );
}
.dest-hero-content {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 2rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}
.dest-hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: 2.5rem;
    font-weight: 900;
    color: white;
    text-shadow: 0 2px 12px rgba(0,0,0,0.6);
    letter-spacing: -0.03em;
    line-height: 1.1;
}
.dest-hero-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.35rem;
}
.dest-hero-badge {
    background: rgba(15,23,42,0.75);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-glass);
    border-radius: 999px;
    padding: 0.4rem 1rem;
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-weight: 500;
}
.dest-hero-score {
    background: linear-gradient(90deg, rgba(59,130,246,0.8), rgba(139,92,246,0.8));
    border-radius: 999px;
    padding: 0.45rem 1.1rem;
    font-size: 0.9rem;
    font-weight: 700;
    color: white;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

/* SVG/fallback hero */
.dest-hero-fallback {
    width: 100%;
    height: 320px;
    border-radius: var(--radius-xl);
    background: linear-gradient(135deg,
        rgba(59,130,246,0.35) 0%,
        rgba(139,92,246,0.3) 50%,
        rgba(16,185,129,0.2) 100%);
    border: 1px solid var(--border-glass);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow-md);
    position: relative;
    overflow: hidden;
}
.dest-hero-fallback::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 30% 50%, rgba(59,130,246,0.15), transparent 50%),
        radial-gradient(circle at 70% 30%, rgba(139,92,246,0.15), transparent 40%);
}
.dest-hero-fallback-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
    z-index: 1;
}
.dest-hero-fallback-title {
    font-family: 'Outfit', sans-serif;
    font-size: 2.25rem;
    font-weight: 900;
    color: white;
    text-align: center;
    z-index: 1;
    letter-spacing: -0.03em;
}
.dest-hero-fallback-sub {
    font-size: 0.9rem;
    color: var(--text-muted);
    z-index: 1;
    margin-top: 0.5rem;
}

/* ── Destination Info Card ──────────────────────────────────────────────── */
.dest-info-card {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow-md);
}
.dest-info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 1rem;
}
.dest-info-item {
    background: rgba(15,23,42,0.55);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-sm);
    padding: 0.85rem 1rem;
    transition: all var(--transition);
}
.dest-info-item:hover {
    border-color: var(--border-active);
    background: rgba(59,130,246,0.08);
}
.dest-info-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted);
    margin-bottom: 0.3rem;
}
.dest-info-value {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
}

/* ── Dashboard Panel ────────────────────────────────────────────────────── */
.dashboard-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.75rem 2rem;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow-md);
}

/* ── Budget Intelligence ────────────────────────────────────────────────── */
.budget-intel-card {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.75rem;
    margin-bottom: var(--section-gap);
    box-shadow: var(--shadow-md);
}
.budget-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
    gap: 0.75rem;
}
.budget-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
}
.budget-badge {
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
}
.budget-badge.adequate  { background: rgba(59,130,246,0.2);  color: var(--blue-light);    border: 1px solid rgba(59,130,246,0.4); }
.budget-badge.tight     { background: rgba(245,158,11,0.2);  color: #fbbf24;              border: 1px solid rgba(245,158,11,0.4); }
.budget-badge.critical  { background: rgba(239,68,68,0.2);   color: #fca5a5;              border: 1px solid rgba(239,68,68,0.4); }
.budget-badge.comfortable { background: rgba(16,185,129,0.2); color: var(--emerald-light); border: 1px solid rgba(16,185,129,0.4); }

.budget-conversion-row {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.25rem;
}
.budget-currency-block {
    background: rgba(15,23,42,0.55);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-sm);
    padding: 1rem;
    text-align: center;
}
.budget-currency-label { font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
.budget-currency-amount { font-size: 1.4rem; font-weight: 800; color: var(--text-primary); margin: 0.2rem 0; }
.budget-currency-code { font-size: 0.8rem; color: var(--text-muted); }
.budget-arrow { font-size: 1.5rem; color: var(--text-muted); text-align: center; }

.budget-items-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}
.budget-item {
    background: rgba(15,23,42,0.55);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-sm);
    padding: 0.85rem;
    transition: all var(--transition);
}
.budget-item:hover { border-color: var(--border-active); }
.budget-item-label { font-size: 0.72rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.3rem; }
.budget-item-amount { font-size: 1rem; font-weight: 700; color: var(--text-primary); }
.budget-item-note { font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem; }

.budget-alert-warning {
    background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.08));
    border: 1px solid rgba(239,68,68,0.4);
    border-radius: var(--radius-md);
    padding: 1.25rem;
    margin-top: 1rem;
}
.budget-alert-success {
    background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.08));
    border: 1px solid rgba(16,185,129,0.4);
    border-radius: var(--radius-md);
    padding: 1.25rem;
    margin-top: 1rem;
}
.budget-alert-tight {
    background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.08));
    border: 1px solid rgba(245,158,11,0.4);
    border-radius: var(--radius-md);
    padding: 1.25rem;
    margin-top: 1rem;
}
.budget-alert-title { font-size: 0.95rem; font-weight: 700; margin-bottom: 0.5rem; }
.budget-alert-body { font-size: 0.85rem; color: var(--text-secondary); }
.budget-reason { font-size: 0.82rem; color: var(--text-muted); margin-top: 0.35rem; }
.budget-reason::before { content: '• '; }

/* ── Saved Trips Modal ──────────────────────────────────────────────────── */
.trips-modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.65);
    z-index: 2000;
    backdrop-filter: blur(8px);
    align-items: flex-start;
    justify-content: center;
    padding: 3rem 1rem;
}
.trips-modal-overlay.open { display: flex; }

.trips-modal {
    background: linear-gradient(180deg, #0a0f1e, #0d1526);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-xl);
    width: 100%;
    max-width: 700px;
    max-height: 80vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: var(--shadow-lg);
    animation: modal-slide-in 0.3s var(--transition);
}
@keyframes modal-slide-in {
    from { opacity: 0; transform: translateY(-20px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}

.trips-modal-header {
    padding: 1.5rem;
    border-bottom: 1px solid var(--border-glass);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}
.trips-modal-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); }
.trips-modal-close {
    width: 36px; height: 36px;
    border-radius: 8px;
    border: 1px solid var(--border-glass);
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
    transition: all var(--transition);
}
.trips-modal-close:hover {
    background: rgba(239,68,68,0.2);
    border-color: rgba(239,68,68,0.4);
    color: #fca5a5;
}

.trips-modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 1.5rem 1.5rem;
}

.trip-card {
    background: rgba(15,23,42,0.6);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    padding: 1.1rem;
    margin-bottom: 0.75rem;
    transition: all var(--transition);
}
.trip-card:hover {
    border-color: var(--border-active);
    background: rgba(20,30,55,0.8);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}
.trip-card-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 0.5rem; }
.trip-card-dest { font-size: 1rem; font-weight: 700; color: var(--text-primary); }
.trip-card-score {
    font-size: 0.8rem;
    font-weight: 700;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(59,130,246,0.3), rgba(139,92,246,0.3));
    color: var(--blue-light);
    border: 1px solid rgba(96,165,250,0.3);
    white-space: nowrap;
}
.trip-card-meta { display: flex; gap: 1rem; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem; }
.trip-card-meta span { display: flex; align-items: center; gap: 0.3rem; }
.trip-card-actions { display: flex; gap: 0.5rem; }
.trip-card-btn {
    flex: 1;
    padding: 0.4rem 0;
    border-radius: 8px;
    border: 1px solid var(--border-glass);
    background: rgba(30,41,59,0.6);
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition);
    text-align: center;
}
.trip-card-btn:hover { background: rgba(59,130,246,0.2); border-color: var(--border-active); color: var(--blue-light); }
.trip-card-btn.danger:hover { background: rgba(239,68,68,0.2); border-color: rgba(239,68,68,0.4); color: #fca5a5; }

/* ── Page Sections ──────────────────────────────────────────────────────── */
.page-section { margin-bottom: var(--section-gap); }

.page-section-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 0.35rem;
    letter-spacing: -0.025em;
}
.page-section-subtitle {
    color: var(--text-muted);
    font-size: 0.92rem;
    margin-bottom: 1.25rem;
}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: rgba(15,23,42,0.6);
    border-radius: var(--radius-md);
    padding: 0.4rem;
    border: 1px solid var(--border-glass);
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 999px !important;
    border: 1px solid transparent !important;
    color: var(--text-muted) !important;
    padding: 0.6rem 1.25rem !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    min-height: 42px;
    transition: all var(--transition) !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, rgba(59,130,246,0.3), rgba(139,92,246,0.25)) !important;
    color: var(--text-primary) !important;
    border-color: var(--border-active) !important;
    box-shadow: 0 4px 16px rgba(59,130,246,0.2) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

/* ── Buttons ────────────────────────────────────────────────────────────── */
div.stButton > button,
div.stDownloadButton > button {
    border-radius: var(--radius-sm) !important;
    padding: 0.75rem 1.25rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    min-height: 48px !important;
    transition: all var(--transition) !important;
    letter-spacing: -0.01em !important;
}
div.stButton > button[kind="primary"],
div.stDownloadButton > button[kind="primary"] {
    background: linear-gradient(90deg, var(--blue), var(--purple)) !important;
    border: none !important;
    box-shadow: 0 6px 24px rgba(59,130,246,0.3) !important;
    color: white !important;
}
div.stButton > button[kind="primary"]:hover,
div.stDownloadButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 36px rgba(139,92,246,0.45) !important;
}
div.stButton > button:not([kind="primary"]),
div.stDownloadButton > button:not([kind="primary"]) {
    border: 1px solid var(--border-glass) !important;
    background: rgba(15,23,42,0.75) !important;
    color: var(--text-secondary) !important;
}
div.stButton > button:not([kind="primary"]):hover,
div.stDownloadButton > button:not([kind="primary"]):hover {
    border-color: var(--border-active) !important;
    background: rgba(59,130,246,0.15) !important;
    color: var(--text-primary) !important;
}

/* ── Metrics ────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(15,22,40,0.95), rgba(8,12,20,0.9));
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    padding: 1.25rem 1rem !important;
    box-shadow: var(--shadow-sm);
    transition: all var(--transition);
}
[data-testid="stMetric"]:hover {
    border-color: var(--border-active);
    box-shadow: var(--shadow-md);
}
[data-testid="stMetricLabel"] {
    font-size: 0.74rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted) !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 800 !important;
    color: var(--text-primary) !important;
}

/* ── Inputs ─────────────────────────────────────────────────────────────── */
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
    background: rgba(8,12,20,0.85) !important;
    border-color: var(--border-glass) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    min-height: 44px;
    transition: border-color var(--transition) !important;
}
.stTextInput input:focus,
.stNumberInput input:focus {
    border-color: var(--border-active) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(59,130,246,0.25) !important;
    border-radius: 6px !important;
    color: var(--blue-light) !important;
}

/* ── Expanders ──────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: rgba(15,23,42,0.65) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.85rem 1rem !important;
    transition: background var(--transition) !important;
}
.streamlit-expanderHeader:hover {
    background: rgba(30,41,59,0.8) !important;
}
[data-testid="stExpander"] {
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    margin-bottom: 0.85rem;
    overflow: hidden;
    transition: border-color var(--transition);
}
[data-testid="stExpander"]:hover {
    border-color: var(--border-active);
}

/* ── Progress ───────────────────────────────────────────────────────────── */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--blue), var(--purple), var(--emerald)) !important;
    border-radius: 999px !important;
    height: 8px !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3) !important;
}

/* ── Containers ─────────────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: var(--radius-md) !important;
    padding: var(--card-padding) !important;
    background: rgba(8,12,20,0.55) !important;
    border-color: var(--border-glass) !important;
    margin-bottom: 0.85rem;
    transition: all var(--transition) !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(96,165,250,0.25) !important;
    background: rgba(15,22,40,0.65) !important;
}

/* ── Divider ────────────────────────────────────────────────────────────── */
.divider-line {
    border: none;
    border-top: 1px solid var(--border-glass);
    margin: 2rem 0;
}

/* ── Toast / Info ────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    border-width: 1px !important;
}

/* ── Compact mode ───────────────────────────────────────────────────────── */
body.compact-mode .main .block-container { padding-top: 0.75rem; padding-bottom: 2rem; }
body.compact-mode [data-testid="stMetric"] { padding: 0.75rem 0.65rem !important; }
body.compact-mode .hero-container { padding: 1.75rem 2.5rem; }
body.compact-mode .dashboard-panel { padding: 1.25rem 1.5rem; }
body.compact-mode .dest-hero-banner { height: 220px; }

/* ── No animations ──────────────────────────────────────────────────────── */
body.no-animations * { transition: none !important; animation: none !important; }
body.no-animations div.stButton > button:hover { transform: none !important; }
body.no-animations .dest-hero-banner:hover .dest-hero-img { transform: none !important; }

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(96,165,250,0.3); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(96,165,250,0.5); }
"""


def inject_theme(
    compact_view: bool = False,
    animations_enabled: bool = True,
) -> None:
    extra_rules = ""
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
