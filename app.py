import streamlit as st
import anthropic
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Smart Bees Analytics", page_icon="🐝", layout="wide")

# API key is checked only when the AI report is requested, so uploading,
# KPIs and charts all work without it.
api_key = os.environ.get("ANTHROPIC_API_KEY")

# ── Honeycomb SVG helpers ──────────────────────────────────────────────────────

def hex_points(cx, cy, r=22):
    """Flat-top hexagon vertices."""
    import math
    pts = []
    for i in range(6):
        angle = math.radians(60 * i)
        pts.append(f"{cx + r * math.cos(angle):.1f},{cy + r * math.sin(angle):.1f}")
    return " ".join(pts)

def honeycomb_svg(width=260, height=210):
    """7-hex cluster SVG for hero decoration."""
    # flat-top hex: neighbour offsets (dx, dy)
    # R=26, apothem=22.5, col-offset=39, row-offset=22.5
    R = 26
    dx = R * 1.5          # 39
    dy = R * (3**0.5)/2   # 22.5

    centers = [
        (130, 105),                          # center
        (130 - 2*dx, 105),                   # far-left
        (130 + 2*dx, 105),                   # far-right
        (130 - dx,   105 - dy),              # upper-left
        (130 + dx,   105 - dy),              # upper-right
        (130 - dx,   105 + dy),              # lower-left
        (130 + dx,   105 + dy),              # lower-right
        (130,        105 - 2*dy),            # top
        (130,        105 + 2*dy),            # bottom
    ]

    polys = []
    for i, (cx, cy) in enumerate(centers):
        is_center = i == 0
        fill_op  = "0.09" if is_center else "0.03"
        stroke_op = "0.35" if is_center else "0.18"
        sw = "1.5" if is_center else "1"
        pts = hex_points(cx, cy, R)
        polys.append(
            f'<polygon points="{pts}" '
            f'fill="rgba(255,195,0,{fill_op})" '
            f'stroke="#FFC300" stroke-width="{sw}" stroke-opacity="{stroke_op}"/>'
        )

    return f"""
<svg width="{width}" height="{height}" viewBox="0 0 260 210"
     xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;opacity:0.9">
  {"".join(polys)}
</svg>"""

# ── Styles ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Subtle honeycomb dot-grid background */
    .stApp {
        background-color: #0a0a0a;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='52' height='90'%3E%3Cpolygon points='26,2 50,15 50,41 26,54 2,41 2,15' fill='none' stroke='%23FFC300' stroke-width='0.6' stroke-opacity='0.04'/%3E%3Cpolygon points='26,56 50,69 50,88 26,88 2,88 2,69' fill='none' stroke='%23FFC300' stroke-width='0.6' stroke-opacity='0.04'/%3E%3C/svg%3E");
    }

    .block-container {
        padding-top: 0 !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 1400px;
    }

    header[data-testid="stHeader"] { background: transparent; }

    /* ── NAVBAR ── */
    .navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.2rem 0;
        border-bottom: 1px solid #1e1e1e;
        margin-bottom: 2.5rem;
    }
    .navbar-brand { display: flex; align-items: center; gap: 12px; }
    .navbar-hex-logo {
        width: 42px; height: 42px;
        background: linear-gradient(135deg, #FFC300, #e6a800);
        clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem;
    }
    .navbar-name { font-size: 1.25rem; font-weight: 700; color: #FFC300; letter-spacing: -0.3px; }
    .navbar-tag  { font-size: 0.7rem; color: #888; font-weight: 500; letter-spacing: 2px; text-transform: uppercase; margin-top: 2px; }
    .navbar-right { display: flex; align-items: center; gap: 14px; }
    .navbar-hex-dots { display: flex; gap: 6px; align-items: center; }
    .navbar-hex-dot {
        width: 10px; height: 10px;
        clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
    }
    .navbar-badge {
        background: #111;
        border: 1px solid #2a2a2a;
        border-radius: 20px;
        padding: 5px 14px;
        font-size: 0.72rem;
        color: #FFC300;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* ── HERO ── */
    .hero-section {
        background: linear-gradient(135deg, #0f0f0f 0%, #0a0a0a 100%);
        border: 1px solid #1e1e1e;
        border-radius: 20px;
        padding: 2.2rem 2.8rem;
        margin-bottom: 2.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        overflow: hidden;
        position: relative;
    }
    .hero-section::before {
        content: '';
        position: absolute;
        top: -80px; right: 200px;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(255,195,0,0.05) 0%, transparent 65%);
        border-radius: 50%;
        pointer-events: none;
    }
    .hero-text { flex: 1; }
    .hero-title { font-size: 1.7rem; font-weight: 700; color: #fff; margin: 0 0 8px; }
    .hero-subtitle { font-size: 0.88rem; color: #8a8a8a; margin: 0; font-weight: 400; line-height: 1.5; }
    /* Stack hero + hide honeycomb on small screens */
    @media (max-width: 820px) {
        .hero-section { flex-direction: column; align-items: flex-start; gap: 1.2rem; padding: 1.8rem; }
        .hero-section svg { display: none; }
    }

    /* ── FILE UPLOADER ── */
    [data-testid="stFileUploader"] {
        border: 1.5px dashed #2a2a2a !important;
        border-radius: 14px !important;
        background: #0d0d0d !important;
        padding: 0.8rem !important;
    }
    [data-testid="stFileUploader"]:hover { border-color: #FFC300 !important; }
    [data-testid="stFileUploader"] label { color: #888 !important; font-size: 0.85rem !important; }

    /* ── SECTION HEADERS ── */
    .section-header { display: flex; align-items: center; gap: 12px; margin: 0 0 1.2rem; }
    .section-icon {
        width: 34px; height: 34px;
        background: rgba(255,195,0,0.12);
        clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem;
        border: none;
    }
    .section-title  { font-size: 1rem; font-weight: 600; color: #fff; margin: 0; }
    .section-subtitle { font-size: 0.78rem; color: #888; margin: 0; }

    /* ── KPI CARDS ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2.5rem;
    }
    /* Tablet: 2 columns */
    @media (max-width: 1100px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    }
    /* Mobile: single column */
    @media (max-width: 640px) {
        .kpi-grid { grid-template-columns: 1fr; }
    }
    .kpi-card {
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        position: relative;
        overflow: hidden;
    }
    /* Hex watermark inside each KPI card */
    .kpi-card::before {
        content: '⬡';
        position: absolute;
        bottom: -10px; right: 6px;
        font-size: 5rem;
        color: #FFC300;
        opacity: 0.04;
        line-height: 1;
        pointer-events: none;
    }
    /* Gold bottom-left accent bar */
    .kpi-card::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0;
        width: 40%; height: 2px;
        background: linear-gradient(90deg, #FFC300, transparent);
    }
    .kpi-label { font-size: 0.7rem; font-weight: 600; color: #8a8a8a; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 0.6rem; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #FFC300; line-height: 1; margin-bottom: 0.4rem; }
    .kpi-hint  { font-size: 0.72rem; color: #666; }

    /* ── QUALITY BANNERS ── */
    .quality-ok {
        background: rgba(34,197,94,0.06); border: 1px solid rgba(34,197,94,0.18);
        border-radius: 10px; padding: 0.7rem 1rem;
        font-size: 0.82rem; color: #4ade80; margin-bottom: 1.5rem;
        display: flex; align-items: center; gap: 8px;
    }
    .quality-warn {
        background: rgba(251,191,36,0.06); border: 1px solid rgba(251,191,36,0.18);
        border-radius: 10px; padding: 0.7rem 1rem;
        font-size: 0.82rem; color: #fbbf24; margin-bottom: 1.5rem;
        display: flex; align-items: center; gap: 8px;
    }

    /* ── TABLE ── */
    [data-testid="stDataFrame"] { border-radius: 12px !important; border: 1px solid #1e1e1e !important; overflow: hidden; }

    /* ── SELECT BOXES ── */
    [data-testid="stSelectbox"] label { color: #666 !important; font-size: 0.78rem !important; font-weight: 500 !important; }
    [data-testid="stSelectbox"] > div > div { background: #0f0f0f !important; border-color: #2a2a2a !important; border-radius: 10px !important; font-size: 0.88rem !important; }

    /* ── AI SECTION ── */
    .ai-section {
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 16px;
        padding: 1.8rem 2rem;
        margin-bottom: 2.5rem;
        position: relative;
        overflow: hidden;
    }
    /* Honeycomb watermark in AI section */
    .ai-section::after {
        content: '⬡ ⬡ ⬡';
        position: absolute;
        bottom: -14px; right: 12px;
        font-size: 5.5rem;
        color: #FFC300;
        opacity: 0.025;
        letter-spacing: -8px;
        pointer-events: none;
    }
    .ai-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
    .ai-badge {
        background: rgba(255,195,0,0.08); border: 1px solid rgba(255,195,0,0.2);
        border-radius: 20px; padding: 4px 12px;
        font-size: 0.7rem; color: #FFC300; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;
    }
    .ai-description { font-size: 0.83rem; color: #8a8a8a; margin-bottom: 1.4rem; line-height: 1.5; }
    /* AI report box — content rendered as sanitised Markdown (no raw HTML) */
    .st-key-ai-report {
        background: #0d0d0d; border: 1px solid #1e1e1e;
        border-radius: 12px; padding: 1.5rem 1.7rem;
    }
    .st-key-ai-report [data-testid="stMarkdownContainer"] {
        font-size: 0.88rem; color: #ccc; line-height: 1.7;
    }
    .st-key-ai-report h1, .st-key-ai-report h2, .st-key-ai-report h3 {
        color: #FFC300; font-weight: 600;
    }
    .st-key-ai-report strong { color: #fff; }
    .st-key-ai-report a { color: #FFC300; }

    /* ── BUTTON ── */
    .stButton > button {
        background: linear-gradient(135deg, #FFC300 0%, #e6b000 100%) !important;
        color: #000 !important; font-weight: 600 !important;
        border: none !important; border-radius: 10px !important;
        padding: 0.6rem 2rem !important; font-size: 0.88rem !important;
        letter-spacing: 0.3px !important;
        box-shadow: 0 4px 20px rgba(255,195,0,0.18) !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }

    /* ── SPINNER ── */
    .stSpinner > div { border-top-color: #FFC300 !important; }

    hr { border-color: #1a1a1a !important; margin: 2rem 0 !important; }

    /* ── EMPTY STATE ── */
    .empty-state {
        text-align: center; padding: 4rem 2rem; color: #777;
    }
    .empty-hex {
        font-size: 4rem; margin-bottom: 1rem; color: #FFC300; opacity: 0.45;
    }

    /* ── FOOTER ── */
    .footer {
        text-align: center; padding: 2rem 0 1rem;
        border-top: 1px solid #1a1a1a;
        font-size: 0.75rem; color: #777; margin-top: 1rem;
    }
    .footer span { color: #FFC300; }
</style>
""", unsafe_allow_html=True)

# ── NAVBAR ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="navbar">
    <div class="navbar-brand">
        <div class="navbar-hex-logo">🐝</div>
        <div>
            <div class="navbar-name">Smart Bees</div>
            <div class="navbar-tag">Analytics Platform</div>
        </div>
    </div>
    <div class="navbar-right">
        <div class="navbar-hex-dots">
            <div class="navbar-hex-dot" style="background:#FFC300;opacity:0.8"></div>
            <div class="navbar-hex-dot" style="background:#FFC300;opacity:0.4"></div>
            <div class="navbar-hex-dot" style="background:#FFC300;opacity:0.2"></div>
        </div>
        <div class="navbar-badge">AI-Powered</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── HERO + HONEYCOMB SVG ───────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-section">
    <div class="hero-text">
        <div class="hero-title">Upload your dataset</div>
        <div class="hero-subtitle">
            Drop any CSV file to instantly generate KPIs, charts,<br>and an AI-powered insight report — in seconds.
        </div>
    </div>
    {honeycomb_svg(260, 180)}
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload a CSV file", type="csv", label_visibility="collapsed")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # ── DATA QUALITY ───────────────────────────────────────────────────────────
    issues = []
    if df.isnull().sum().sum() > 0:
        issues.append(f"{df.isnull().sum().sum()} missing values")
    if df.duplicated().sum() > 0:
        issues.append(f"{df.duplicated().sum()} duplicate rows")

    if issues:
        st.markdown(f'<div class="quality-warn">⚠️ Data quality issues detected: {", ".join(issues)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="quality-ok">⬡ No data quality issues detected — dataset looks clean</div>', unsafe_allow_html=True)

    # ── KPI CALCULATION ────────────────────────────────────────────────────────
    # Rank numeric columns by business importance rather than just taking the first
    # four, so marketing datasets surface revenue / conversions / rate / ROAS first.
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    ratio_keywords = ['roas', 'cac', 'rate', 'ratio', 'pct', 'avg', 'mean', '%']
    money_keywords = ['revenue', 'sales', 'turnover', 'spend', 'cost', 'amount', 'budget']

    def kpi_priority(name):
        """Lower number = more important business KPI."""
        c = name.lower()
        if any(w in c for w in ['revenue', 'sales', 'turnover']):                  return 0
        if ('conversion' in c or 'conv' in c) and 'rate' in c:                     return 2
        if any(w in c for w in ['conversion', 'orders', 'purchases', 'leads',
                                 'signups']):                                      return 1
        if 'roas' in c:                                                            return 3
        if 'roi' in c:                                                             return 4
        if any(w in c for w in ['ctr', 'cpc', 'cpa', 'cac']):                      return 5
        if any(w in c for w in ['spend', 'cost', 'budget']):                       return 6
        if any(w in c for w in ['click', 'impression', 'session', 'visit',
                                 'reach']):                                        return 7
        return 50

    # Build a KPI for every numeric column, then keep the four highest priority.
    candidates = []  # (priority, original_order, kpi)
    for idx, col in enumerate(numeric_cols):
        col_lower = col.lower()
        if any(w in col_lower for w in ratio_keywords):
            val = df[df[col] > 0][col].mean()
            if pd.isna(val):
                continue
            kpi = {"label": col.replace('_', ' ').upper(),
                   "value": f"{val:.2f}x" if 'roas' in col_lower else f"{val:.2f}",
                   "hint": "average"}
        else:
            val = df[col].sum()
            if pd.isna(val):
                continue
            money = any(w in col_lower for w in money_keywords)
            kpi = {"label": col.replace('_', ' ').upper(),
                   "value": f"€{val:,.0f}" if money else f"{val:,.0f}",
                   "hint": "total"}
        candidates.append((kpi_priority(col), idx, kpi))

    # Derive conversion rate when the parts exist but no explicit rate column does.
    has_rate_col = any(('conversion' in c.lower() or 'conv' in c.lower()) and 'rate' in c.lower()
                       for c in numeric_cols)
    if {'sessions', 'conversions'}.issubset(df.columns) and not has_rate_col:
        total_sessions = df['sessions'].sum()
        if total_sessions:
            rate = (df['conversions'].sum() / total_sessions) * 100
            candidates.append((2, -1, {"label": "CONVERSION RATE",
                                       "value": f"{rate:.2f}%", "hint": "calculated"}))

    candidates.sort(key=lambda t: (t[0], t[1]))
    kpis = [c[2] for c in candidates[:4]]

    while len(kpis) < 4:
        kpis.append({"label": "TOTAL ROWS", "value": f"{len(df):,}", "hint": "dataset size"})

    # ── KPI CARDS ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <div class="section-icon">📊</div>
        <div>
            <div class="section-title">Key Performance Indicators</div>
            <div class="section-subtitle">Automatically extracted from your dataset</div>
        </div>
    </div>""", unsafe_allow_html=True)

    cards_html = '<div class="kpi-grid">'
    for kpi in kpis:
        cards_html += f"""
        <div class="kpi-card">
            <div class="kpi-label">{kpi['label']}</div>
            <div class="kpi-value">{kpi['value']}</div>
            <div class="kpi-hint">{kpi['hint']}</div>
        </div>"""
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── DATA PREVIEW ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <div class="section-icon">🗂</div>
        <div>
            <div class="section-title">Data Preview</div>
            <div class="section-subtitle">First 10 rows of your dataset</div>
        </div>
    </div>""", unsafe_allow_html=True)
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHART ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <div class="section-icon">📈</div>
        <div>
            <div class="section-title">Visualize Your Data</div>
            <div class="section-subtitle">Select axes to explore relationships</div>
        </div>
    </div>""", unsafe_allow_html=True)

    all_cols = df.columns.tolist()
    if len(numeric_cols) > 0:
        col_x, col_y, _ = st.columns([1, 1, 2])
        with col_x:
            x_axis = st.selectbox("X Axis", all_cols)
        with col_y:
            y_axis = st.selectbox("Y Axis", numeric_cols)

        is_ratio = any(w in y_axis.lower() for w in ratio_keywords)
        if df[x_axis].dtype == 'object' or 'date' in x_axis.lower():
            chart_df = (df[df[y_axis] > 0].groupby(x_axis)[y_axis].mean().reset_index()
                        if is_ratio else df.groupby(x_axis)[y_axis].sum().reset_index())
        else:
            chart_df = df[[x_axis, y_axis]].copy()

        if 'date' in x_axis.lower():
            fig = px.line(chart_df, x=x_axis, y=y_axis, color_discrete_sequence=['#FFC300'])
            fig.update_traces(line=dict(width=2.5), fill='tozeroy', fillcolor='rgba(255,195,0,0.06)')
        else:
            fig = px.bar(chart_df, x=x_axis, y=y_axis, color=y_axis,
                         color_continuous_scale=[[0, '#1a1a1a'], [1, '#FFC300']])

        fig.update_layout(
            plot_bgcolor='#111', paper_bgcolor='#111',
            font=dict(family='Inter', color='#888', size=12),
            showlegend=False, coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor='#1e1e1e', showgrid=True, zeroline=False, tickfont=dict(size=11, color='#555')),
            yaxis=dict(gridcolor='#1e1e1e', showgrid=True, zeroline=False, tickfont=dict(size=11, color='#555')),
            bargap=0.3,
        )
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No numeric columns found for chart.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI REPORT ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="ai-section">
        <div class="ai-header">
            <div class="section-header" style="margin:0">
                <div class="section-icon">🤖</div>
                <div>
                    <div class="section-title">AI Insight Report</div>
                    <div class="section-subtitle">Powered by Claude Sonnet</div>
                </div>
            </div>
            <div class="ai-badge">⬡ Claude AI</div>
        </div>
        <div class="ai-description">
            Generate a full professional analysis of your dataset in French — covering key findings,
            strengths, risks, and actionable recommendations.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Generate AI Insights →"):
      if not api_key:
        st.warning("⚠️ ANTHROPIC_API_KEY not found. Set it in your terminal and restart to enable AI reports — KPIs and charts above work without it.")
      else:
        client = anthropic.Anthropic(api_key=api_key)
        data_sample   = df.head(50).to_string()
        columns_info  = df.dtypes.to_string()
        stats         = df.describe().to_string()
        kpi_summary   = "\n".join([f"- {k['label']}: {k['value']}" for k in kpis])

        prompt = f"""
Tu es un analyste de données senior travaillant pour Smart Bees,
un cabinet de conseil data & analytics spécialisé en marketing digital.

Voici un dataset client avec les KPIs calculés:

KPIs principaux:
{kpi_summary}

Colonnes et types:
{columns_info}

Statistiques descriptives:
{stats}

Aperçu des données (50 premières lignes):
{data_sample}

Génère un rapport d'analyse professionnel en français avec:
1. Vue d'ensemble des données
2. Métriques clés identifiées
3. Points forts
4. Points d'attention
5. Recommandations concrètes
"""

        try:
            with st.spinner("Analysing your data with Claude..."):
                placeholder = st.container(key="ai-report").empty()
                full_response = ""
                with client.messages.stream(
                    model="claude-sonnet-4-6",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        full_response += text
                        # Render as Markdown WITHOUT unsafe_allow_html so the model's
                        # output can't inject HTML/scripts — Streamlit escapes raw HTML
                        # while still formatting the report's headings, bold and lists.
                        placeholder.markdown(full_response)
        except anthropic.InternalServerError:
            st.error("Server error. Wait 30 seconds and try again.")
        except anthropic.APIConnectionError:
            st.error("Connection error. Check your internet and try again.")
        except anthropic.RateLimitError:
            st.error("Rate limit reached. Wait a minute and try again.")
        except Exception as e:
            st.error(f"Something went wrong: {str(e)}")

else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-hex">⬡</div>
        <div style="font-size:1rem;font-weight:600;color:#aaa;margin-bottom:0.5rem">No file uploaded yet</div>
        <div style="font-size:0.82rem;color:#777">Upload a CSV above to get started</div>
    </div>
    """, unsafe_allow_html=True)

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    ⬡ Built with ❤️ by <span>Smart Bees</span> · Powered by Claude AI ⬡
</div>
""", unsafe_allow_html=True)
