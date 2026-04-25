"""
Dashboard Agentique — BH Bank
Charte graphique BH Bank :
  - Navy  #1a2b5e (header, sidebar, accents)
  - Rouge #cc0000 (CTA, alertes critiques)
  - Blanc #ffffff (fond cards)
  - Gris  #f5f6fa (background général)
"""
import sys, os, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from agent import BankReportingAgent

# ══════════════════════════════════════════════════════════════
# CONFIG & CHARTE BH BANK
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="BH Bank — Dashboard IA",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
* { font-family: 'Plus Jakarta Sans', sans-serif !important; }

/* ── Background général ── */
.stApp { background:#f5f6fa !important; color:#1a2b5e !important; }

/* ── Sidebar BH Navy ── */
.stSidebar {
  background: #1a2b5e !important;
  border-right: none !important;
}
.stSidebar * { color: #e8edf5 !important; }
.stSidebar .stMarkdown p, .stSidebar .stMarkdown div { color: #e8edf5 !important; }
.stSidebar h1, .stSidebar h2, .stSidebar h3 { color: #ffffff !important; }
.stSidebar hr { border-color: rgba(255,255,255,0.15) !important; }
.stSidebar [data-testid="stCaption"] { color: #9aaac5 !important; }
section[data-testid="stSidebar"] { background: #1a2b5e !important; }

/* ── Métriques ── */
[data-testid="stMetric"] {
  background: #ffffff !important;
  border: 1px solid #e2e6f0 !important;
  border-radius: 12px !important;
  padding: 16px !important;
  border-left: 4px solid #1a2b5e !important;
  box-shadow: 0 2px 6px rgba(26,43,94,.08) !important;
  transition: all .2s;
}
[data-testid="stMetric"]:hover {
  box-shadow: 0 6px 16px rgba(26,43,94,.14) !important;
  transform: translateY(-2px);
}
[data-testid="stMetric"] label {
  font-size: 11px !important; color: #6b7a99 !important;
  letter-spacing: .7px; text-transform: uppercase; font-weight: 700 !important;
}
[data-testid="stMetricValue"] { color: #1a2b5e !important; font-weight: 700 !important; }

/* ── Boutons ── */
.stButton>button {
  background: #ffffff !important; color: #1a2b5e !important;
  border: 1.5px solid #c8d0e0 !important; border-radius: 8px !important;
  font-weight: 600 !important; transition: all .2s !important;
}
.stButton>button:hover {
  background: #1a2b5e !important; color: white !important;
  border-color: #1a2b5e !important; transform: translateY(-1px) !important;
}
.stButton>button[kind="primary"] {
  background: #cc0000 !important; color: white !important;
  border-color: #cc0000 !important;
}
.stButton>button[kind="primary"]:hover {
  background: #a80000 !important; border-color: #a80000 !important;
}

/* ── Onglets ── */
.stTabs [data-baseweb="tab"] {
  background: transparent !important; color: #6b7a99 !important;
  border-bottom: 3px solid transparent !important;
  padding: 10px 20px !important; font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
  color: #1a2b5e !important; border-bottom-color: #cc0000 !important;
  font-weight: 700 !important;
}

/* ── Expander ── */
div[data-testid="stExpander"] {
  background: #ffffff !important; border: 1px solid #e2e6f0 !important;
  border-radius: 10px !important; box-shadow: 0 1px 4px rgba(26,43,94,.06) !important;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 10px !important; border: 1px solid #e2e6f0 !important; }

/* ── Sections ── */
.section-title {
  font-size: 10px; text-transform: uppercase; letter-spacing: 1.4px;
  color: #9aaac5; font-weight: 700;
  margin: 24px 0 14px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e2e6f0;
}
.dash-divider { border: none; border-top: 1px solid #e2e6f0; margin: 24px 0; }

/* ── Badges ── */
.badge-navy   { display:inline-block; background:#e8edf5; color:#1a2b5e;
  border-radius:6px; padding:4px 14px; font-size:12px; font-weight:700; margin:2px; }
.badge-red    { display:inline-block; background:#fff0f0; color:#cc0000;
  border-radius:6px; padding:4px 14px; font-size:12px; font-weight:700; margin:2px; }
.badge-green  { display:inline-block; background:#e6f9f0; color:#156f47;
  border-radius:6px; padding:4px 14px; font-size:12px; font-weight:700; margin:2px; }
.badge-orange { display:inline-block; background:#fff5e6; color:#b45309;
  border-radius:6px; padding:4px 14px; font-size:12px; font-weight:700; margin:2px; }

/* ── Insights ── */
.insight-card {
  background:#eef2fb; border:1px solid #c5d0e8; border-radius:10px;
  padding:12px 16px; margin:6px 0; font-size:13px; color:#1a2b5e;
  border-left: 4px solid #1a2b5e;
}
.insight-green  { background:#e6f9f0; border-color:#9ee8c5; color:#0d4f32; border-left-color:#10b981; }
.insight-orange { background:#fff5e6; border-color:#ffd199; color:#7c3d00; border-left-color:#f59e0b; }
.insight-red    { background:#fff0f0; border-color:#ffb3b3; color:#7f0000; border-left-color:#cc0000; }

/* ── XAI steps ── */
.xai-step { background:#f5f6fa; border:1px solid #e2e6f0; border-radius:8px;
  padding:10px 14px; margin:4px 0; font-size:12px; }
.xai-step-ok    { border-left:3px solid #10b981; }
.xai-step-error { border-left:3px solid #cc0000; }

/* ── Mémoire ── */
.memory-human { background:#eef2fb; border-radius:6px; padding:8px 12px; margin-bottom:4px; font-size:13px; }
.memory-ai    { background:#f0fdf4; border-radius:6px; padding:8px 12px; font-size:13px; }

/* ── Form input ── */
.stForm { background:#ffffff !important; border:1px solid #e2e6f0 !important;
  border-radius:12px !important; padding:16px !important; }
.stTextInput input {
  border-radius: 8px !important;
  border-color: #c8d0e0 !important;
  color: #1a2b5e !important;
}
.stTextInput input:focus { border-color: #1a2b5e !important; }

/* ── Sidebar items ── */
.sidebar-item {
  background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12);
  border-radius:8px; padding:8px 12px; margin:4px 0;
  font-size:12px; color:#d0d9ee !important;
}
.sidebar-item-active {
  background: rgba(204,0,0,0.3); border-color: rgba(204,0,0,0.5);
  border-radius:8px; padding:8px 12px; margin:4px 0;
  font-size:12px; color:#ffffff !important; font-weight:600;
}

/* ── Titres principaux ── */
h1 { color: #1a2b5e !important; font-weight: 800 !important; }
h2, h3 { color: #1a2b5e !important; font-weight: 700 !important; }

/* ── Status bar ── */
.status-bar {
  background: #1a2b5e; color: white; padding: 6px 16px;
  font-size: 12px; border-radius: 8px; margin-bottom: 12px;
  display: inline-flex; align-items: center; gap: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Palette BH Bank ──────────────────────────────────────────
# Couleurs principales
NAVY   = "#1a2b5e"
RED    = "#cc0000"
TEAL   = "#0077b6"
GREEN  = "#10b981"
AMBER  = "#f59e0b"
PURPLE = "#7c3aed"
CYAN   = "#06b6d4"
ORANGE = "#f97316"

C = [NAVY, RED, TEAL, GREEN, AMBER, PURPLE, CYAN, ORANGE]

PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=NAVY, family="Plus Jakarta Sans"),
    xaxis=dict(gridcolor="#eaecf5", linecolor="#e2e6f0", tickcolor="#9aaac5"),
    yaxis=dict(gridcolor="#eaecf5", linecolor="#e2e6f0", tickcolor="#9aaac5"),
    margin=dict(l=0, r=0, t=44, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=NAVY))
)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
@st.cache_resource
def get_agent():
    return BankReportingAgent()

_KC = {}
def _ukey(b):
    _KC[b] = _KC.get(b, 0) + 1
    return f"{b}_{_KC[b]}"

def _f(fig, h=None):
    fig.update_layout(**PL)
    if h: fig.update_layout(height=h)
    return fig

def _to_list(d):
    if isinstance(d, list): return d
    if isinstance(d, dict):
        if "data" in d:
            lst = d["data"]
            return lst if isinstance(lst, list) else []
        if d.get("status") == "not_found": return []
    return []

def _filtre_badge(data):
    if isinstance(data, dict):
        f = data.get("filtre", "")
        if f and f != "Global":
            st.markdown(f'<span class="badge-navy">🔍 {f}</span>', unsafe_allow_html=True)

def _section(t):
    st.markdown(f'<p class="section-title">{t}</p>', unsafe_allow_html=True)

def _hdiv():
    st.markdown('<hr class="dash-divider">', unsafe_allow_html=True)

def _insight(text, color="blue"):
    cls = {
        "blue":   "insight-card",
        "green":  "insight-card insight-green",
        "orange": "insight-card insight-orange",
        "red":    "insight-card insight-red"
    }.get(color, "insight-card")
    icons = {"blue": "💡", "green": "✅", "orange": "⚠️", "red": "🔴"}
    st.markdown(f'<div class="{cls}">{icons.get(color, "💡")} {text}</div>', unsafe_allow_html=True)

# ── Graphiques helpers ────────────────────────────────────────
def _pie(df, names, vals, title, h=280, hole=0.42):
    if df.empty or names not in df.columns or vals not in df.columns: return None
    fig = px.pie(df, names=names, values=vals, hole=hole, height=h,
                 title=title, color_discrete_sequence=C)
    fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
    return _f(fig)

def _bar_h(df, x, y, title, cs="Blues", h=300):
    if df.empty or x not in df.columns or y not in df.columns: return None
    # Utiliser les couleurs BH
    cs_bh = {"Blues": [[0, "#e8edf5"], [1, NAVY]],
              "Greens": [[0, "#e6f9f0"], [1, "#10b981"]],
              "RdYlGn": "RdYlGn"}.get(cs, cs)
    fig = px.bar(df, x=x, y=y, orientation="h", color=x,
                 color_continuous_scale=cs_bh, height=h, title=title)
    fig.update_coloraxes(showscale=False)
    fig.update_traces(marker_line_width=0)
    return _f(fig)

def _bar_v(df, x, y, title, colors=None, h=280):
    if df.empty or x not in df.columns or y not in df.columns: return None
    kw = dict(color=x, color_discrete_sequence=colors or C) if colors else \
         dict(color=y, color_continuous_scale=[[0, "#e8edf5"], [1, NAVY]])
    fig = px.bar(df, x=x, y=y, height=h, title=title, **kw)
    if not colors: fig.update_coloraxes(showscale=False)
    fig.update_traces(marker_line_width=0)
    return _f(fig)

def _line(df, x, y, title, color=None, h=260):
    if df.empty or x not in df.columns or y not in df.columns: return None
    fig = px.line(df, x=x, y=y, height=h, title=title, markers=True,
                  color_discrete_sequence=[color or NAVY])
    fig.update_traces(line_width=2.5, marker_size=5)
    return _f(fig)

def _area(df, x, y, title, h=260, color=None):
    if df.empty or x not in df.columns or y not in df.columns: return None
    fig = px.area(df, x=x, y=y, height=h, title=title,
                  color_discrete_sequence=[color or NAVY])
    fig.update_traces(line_width=2.5, fillcolor="rgba(26,43,94,0.10)")
    return _f(fig)

def _gauge(val, title, max_val=100, suffix="", h=200):
    if suffix == "h":
        color = GREEN if val < 24 else AMBER if val < 72 else RED
    else:
        color = GREEN if val >= 70 else AMBER if val >= 40 else RED
    steps = [
        {"range": [0, max_val * 0.33], "color": "#fff0f0"},
        {"range": [max_val * 0.33, max_val * 0.66], "color": "#fff5e6"},
        {"range": [max_val * 0.66, max_val], "color": "#e6f9f0"},
    ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val,
        number={"suffix": suffix, "font": {"color": NAVY, "size": 28, "family": "Plus Jakarta Sans"}},
        gauge={"axis": {"range": [0, max_val], "tickcolor": "#9aaac5"},
               "bar": {"color": color, "thickness": 0.65},
               "bgcolor": "#f5f6fa", "bordercolor": "#e2e6f0",
               "steps": steps},
        title={"text": title, "font": {"color": "#6b7a99", "size": 12}}
    ))
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=30, b=10),
                      paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Plus Jakarta Sans"))
    return fig

def _show(fig, key=None):
    if fig: 
        k = key if key else _ukey("chart")
        st.plotly_chart(fig, use_container_width=True, key=k)


# ══════════════════════════════════════════════════════════════
# BLOCS ATOMIQUES — renderers inchangés, seuls les couleurs changent
# ══════════════════════════════════════════════════════════════

def _bloc_reclamations_kpis(data):
    if not isinstance(data, dict) or data.get("erreur"): return
    _filtre_badge(data)
    nom = data.get("client_nom", "")
    if nom: st.markdown(f'<span class="badge-navy">👤 {nom}</span>', unsafe_allow_html=True)
    
    total = int(data.get("total", 0) or 0)
    ouv = int(data.get("ouvertes", 0) or 0)
    trt = int(data.get("traitees", 0) or 0)
    att = max(0, total - ouv - trt)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Total réclamations", f"{total:,}")
    c2.metric("🔴 Ouvertes", f"{ouv:,}",
              delta=f"{ouv / total * 100:.1f}%" if total else None, delta_color="inverse")
    c3.metric("✅ Traitées", f"{trt:,}",
              delta=f"{trt / total * 100:.1f}%" if total else None)
    c4.metric("⏳ En attente", f"{att:,}", delta_color="off")

def _bloc_reclamations_statut(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Répartition par statut")
    df = pd.DataFrame(lst).rename(columns={"_id": "Statut", "count": "Nombre"})
    if "Statut" not in df.columns or "Nombre" not in df.columns: return
    total = int(df["Nombre"].sum())
    col1, col2 = st.columns([3, 2])
    with col1: _show(_pie(df, "Statut", "Nombre", f"Statuts des réclamations ({total:,})"))
    with col2: _show(_bar_h(df.sort_values("Nombre", ascending=True), "Nombre", "Statut", "Nb par statut", "Blues", 240))

def _bloc_reclamations_objet(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Top motifs de réclamations")
    df = pd.DataFrame(lst).rename(columns={"_id": "Objet", "count": "Nombre"})
    if "Objet" not in df.columns: return
    df = df[df["Objet"].notna()].sort_values("Nombre", ascending=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.bar(df, x="Nombre", y="Objet", orientation="h",
                     color="Nombre", color_continuous_scale=[[0, "#e8edf5"], [1, RED]],
                     height=320, title="Top 10 motifs")
        fig.update_coloraxes(showscale=False); fig.update_traces(marker_line_width=0)
        _show(_f(fig))
    with col2:
        if len(df) > 0:
            _insight(f"**{df.iloc[-1]['Objet']}** = **{df.iloc[-1]['Nombre'] / df['Nombre'].sum() * 100:.1f}%**", "orange")
        if len(df) >= 3:
            _insight(f"Top 3 = **{df.tail(3)['Nombre'].sum() / df['Nombre'].sum() * 100:.1f}%** du total", "blue")

def _bloc_reclamations_serie(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Évolution temporelle")
    df = pd.DataFrame(lst).rename(columns={"_id": "Date", "count": "Nombre"})
    if "Date" not in df.columns or "Nombre" not in df.columns: return
    df = df[df["Date"].notna()].sort_values("Date")
    if df.empty: return
    col1, col2 = st.columns([3, 1])
    with col1: _show(_area(df, "Date", "Nombre", "Volume de réclamations dans le temps", color=NAVY))
    with col2:
        if len(df) >= 2:
            last = int(df.iloc[-1]["Nombre"]); prev = int(df.iloc[-2]["Nombre"])
            diff = last - prev; pct = diff / prev * 100 if prev else 0
            _insight(f"Dernière période : **{last}** ({'📈' if diff > 0 else '📉'} {abs(pct):.1f}%)",
                     "red" if diff > 0 else "green")
        _insight(f"Moyenne : **{df['Nombre'].mean():.0f}** réclamations/période", "blue")

def _bloc_delai_resolution(data):
    if not isinstance(data, dict) or data.get("erreur"): return
    _filtre_badge(data); _section("Délai moyen de résolution (SLA)")
    h_val = data.get("duree_moy_heures")
    if not h_val: st.info("Données SLA non disponibles."); return
    h_val = float(h_val)
    col1, col2 = st.columns([2, 3])
    with col1:
        st.plotly_chart(_gauge(round(h_val, 1), "Délai résolution (h)", 120, suffix="h"), 
                        use_container_width=True, key=_ukey("gauge_sla"))
    with col2:
        c = "green" if h_val < 24 else "orange" if h_val < 72 else "red"
        _insight(f"**{h_val:.1f}h** — " + ("🟢 Excellent." if h_val < 24 else "🟡 Acceptable." if h_val < 72 else "🔴 SLA dépassé !"), c)
        df_sla = pd.DataFrame({"Seuil": ["Votre délai", "<24h", "<72h", "Limite"], "Heures": [round(h_val, 1), 24, 72, 120]})
        fig = px.bar(df_sla, x="Heures", y="Seuil", orientation="h", color="Heures",
                     color_continuous_scale=[[0, "#e6f9f0"], [0.5, "#fff5e6"], [1, "#fff0f0"]],
                     height=180, title="vs seuils SLA")
        fig.update_coloraxes(showscale=False); _show(_f(fig))

def _bloc_delai_par_objet(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Délai de résolution par motif")
    df = pd.DataFrame(lst).rename(columns={"_id": "Objet", "delai_moyen": "Délai (h)", "count": "Nb cas"})
    if "Objet" not in df.columns or "Délai (h)" not in df.columns: return
    df = df.sort_values("Délai (h)", ascending=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.bar(df, x="Délai (h)", y="Objet", orientation="h", color="Délai (h)",
                     color_continuous_scale=[[0, "#e6f9f0"], [0.5, "#fff5e6"], [1, "#fff0f0"]],
                     height=300, title="Délai moyen par motif (h)",
                     hover_data={"Nb cas": True} if "Nb cas" in df.columns else {})
        fig.update_coloraxes(showscale=False)
        fig.add_vline(x=72, line_dash="dash", line_color=RED, annotation_text="SLA 72h")
        _show(_f(fig))
    with col2:
        if len(df) > 0:
            _insight(f"**{df.iloc[-1]['Objet']}** : plus long ({df.iloc[-1]['Délai (h)']:.1f}h)", "red")
            _insight(f"**{df.iloc[0]['Objet']}** : plus rapide ({df.iloc[0]['Délai (h)']:.1f}h)", "green")

def _bloc_txn_kpis(data):
    if not isinstance(data, dict) or data.get("erreur"): return
    _filtre_badge(data)
    nom = data.get("client_nom", "")
    if nom: st.markdown(f'<span class="badge-navy">👤 {nom}</span>', unsafe_allow_html=True)
    
    total = int(data.get('total', 0) or 0)
    montant = float(data.get('montant', 0) or 0)
    moy = float(data.get('moy', 0) or 0)
    max_val = float(data.get('max', 0) or 0)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💳 Transactions", f"{total:,}")
    c2.metric("💰 Volume total", f"{montant:,.0f} TND")
    c3.metric("📊 Montant moyen", f"{moy:,.0f} TND")
    c4.metric("📈 Max", f"{max_val:,.0f} TND")

def _bloc_txn_par_type(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Volume et montant par type de transaction")
    df = pd.DataFrame(lst).rename(columns={"_id": "Type", "montant_total": "Montant", "nombre": "Nombre", "montant_moyen": "Moy"})
    if "Type" not in df.columns: return
    df = df[df["Type"].notna()]
    col1, col2 = st.columns([3, 2])
    with col1:
        if "Montant" in df.columns:
            fig = px.bar(df.sort_values("Montant", ascending=False), x="Type", y="Montant",
                         color="Type", height=280, title="Montant par type", color_discrete_sequence=C)
            fig.update_traces(marker_line_width=0); _show(_f(fig))
    with col2:
        if "Montant" in df.columns:
            _show(_pie(df, "Type", "Montant", f"Répartition ({df['Montant'].sum():,.0f} TND)", 280))
    if len(df) > 0:
        with st.expander("📊 Tableau détaillé"):
            d = df[[c for c in ["Type", "Nombre", "Montant", "Moy"] if c in df.columns]].copy()
            for cm in ["Montant", "Moy"]:
                if cm in d.columns: d[cm] = d[cm].apply(lambda x: f"{x:,.0f} TND")
            st.dataframe(d, use_container_width=True, hide_index=True)

def _bloc_txn_serie(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Évolution temporelle des transactions")
    df = pd.DataFrame(lst)
    if "_id" in df.columns: df = df.rename(columns={"_id": "Date"})
    if "Date" not in df.columns: return
    nb_col = next((c for c in ["nb_transactions", "nb"] if c in df.columns), None)
    tot_col = next((c for c in ["montant_total", "total"] if c in df.columns), None)
    df = df[df["Date"].notna()].sort_values("Date")
    if df.empty or not tot_col: return
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df["Date"], y=df[tot_col], name="Montant (TND)",
                         marker_color="#c5d0e8", opacity=0.85, marker_line_width=0), secondary_y=False)
    if nb_col:
        fig.add_trace(go.Scatter(x=df["Date"], y=df[nb_col], name="Nombre",
                                 line=dict(color=RED, width=2.5), mode="lines+markers", marker_size=5), secondary_y=True)
    fig.update_yaxes(title_text="Montant (TND)", secondary_y=False)
    if nb_col: fig.update_yaxes(title_text="Nb transactions", secondary_y=True)
    fig.update_layout(height=280, **PL, title="Montant et nombre de transactions")
    _show(fig)

def _bloc_txn_par_heure(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Activité par heure de la journée")
    df = pd.DataFrame(lst).rename(columns={"_id": "Heure", "count": "Transactions"})
    if "Heure" not in df.columns or "Transactions" not in df.columns: return
    df = df[df["Heure"].notna()].sort_values("Heure")
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.bar(df, x="Heure", y="Transactions", color="Transactions",
                     color_continuous_scale=[[0, "#e8edf5"], [1, NAVY]],
                     height=240, title="Intensité transactionnelle par heure")
        fig.update_coloraxes(showscale=False); fig.update_traces(marker_line_width=0); _show(_f(fig))
    with col2:
        if len(df) > 0:
            peak = int(df.loc[df["Transactions"].idxmax(), "Heure"])
            low  = int(df.loc[df["Transactions"].idxmin(), "Heure"])
            _insight(f"Pic : **{peak}h** — surveillance renforcée.", "orange")
            _insight(f"Creux : **{low}h** — maintenance idéale.", "green")

def _bloc_txn_top(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("⚡ Top transactions — alertes montant")
    df = pd.DataFrame(lst)
    cols = [c for c in ["type", "amount", "date", "desc", "account_number"] if c in df.columns]
    col1, col2 = st.columns([3, 2])
    with col1: st.dataframe(df[cols] if cols else df, use_container_width=True, hide_index=True)
    with col2:
        if "amount" in df.columns and "type" in df.columns:
            amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
            fig = px.scatter(df, y=amounts, x=df.index, color="type", size=amounts,
                             height=240, title="Dispersion des montants", color_discrete_sequence=C,
                             labels={"y": "Montant (TND)", "x": "Rang"})
            _show(_f(fig))

def _bloc_loans_stats(data):
    if not isinstance(data, dict) or data.get("erreur"): return
    _filtre_badge(data)
    
    total = int(data.get('total_loans', 0) or 0)
    montant = float(data.get('montant_total', 0) or 0)
    moy = float(data.get('montant_moyen', 0) or 0)
    r = float(data.get("taux_remboursement_global", 0) or 0)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💼 Total prêts", f"{total:,}")
    c2.metric("💰 Encours total", f"{montant:,.0f} TND")
    c3.metric("📊 Montant moyen", f"{moy:,.0f} TND")
    c4.metric("✅ Taux remboursement", f"{r:.1f}%",
              delta="Sain" if r >= 70 else "Vigilance", delta_color="normal" if r >= 70 else "inverse")

def _bloc_loans_grade(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Distribution des prêts par grade (risque crédit)")
    df = pd.DataFrame(lst).rename(columns={"_id": "Grade", "total": "Nb",
                                             "montant_total": "Montant", "taux_moyen": "Taux %",
                                             "taux_remboursement_pct": "Remb %"})
    if "Grade" not in df.columns: return
    df = df[df["Grade"].notna()].sort_values("Grade")
    col1, col2 = st.columns([3, 1])
    with col1:
        if "Nb" in df.columns:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=df["Grade"], y=df["Nb"], name="Nb prêts",
                                 marker_color=NAVY, opacity=0.85, marker_line_width=0), secondary_y=False)
            if "Remb %" in df.columns:
                fig.add_trace(go.Scatter(x=df["Grade"], y=df["Remb %"], name="% Remboursé",
                                         line=dict(color=RED, width=2.5), mode="lines+markers+text",
                                         text=df["Remb %"].round(1), textposition="top center", marker_size=6),
                              secondary_y=True)
            fig.update_yaxes(title_text="Nb prêts", secondary_y=False)
            fig.update_yaxes(title_text="% Remboursé", secondary_y=True, range=[0, 115])
            fig.update_layout(height=300, **PL, title="Prêts par grade — nb & taux remboursement")
            _show(fig)
    with col2:
        if "Remb %" in df.columns and len(df) > 0:
            _insight(f"Grade **{df.loc[df['Remb %'].idxmax(), 'Grade']}** : meilleur remboursement ✓", "green")
            _insight(f"Grade **{df.loc[df['Remb %'].idxmin(), 'Grade']}** : à surveiller !", "red")

def _bloc_loans_objet(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Répartition des prêts par objet")
    df = pd.DataFrame(lst).rename(columns={"_id": "Objet", "count": "Nombre", "montant_total": "Montant"})
    if "Objet" not in df.columns: return
    df = df[df["Objet"].notna()]
    col1, col2 = st.columns(2)
    with col1:
        if "Montant" in df.columns: _show(_pie(df, "Objet", "Montant", f"Répartition ({df['Montant'].sum():,.0f} TND)"))
    with col2:
        if "Montant" in df.columns: _show(_bar_h(df.sort_values("Montant", ascending=True), "Montant", "Objet", "Encours par objet (TND)", "Blues"))

def _bloc_loans_taux(data):
    lst = _to_list(data)
    if not lst: return
    _section("Distribution des taux d'intérêt")
    df = pd.DataFrame(lst)
    if "_id" not in df.columns or "count" not in df.columns: return
    df["tranche"] = df["_id"].apply(lambda x: str(x) if x is not None else "Autre")
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.bar(df, x="tranche", y="count", color="count",
                     color_continuous_scale=[[0, "#e8edf5"], [1, RED]],
                     height=240, title="Prêts par tranche de taux",
                     labels={"tranche": "Taux (%)", "count": "Nb prêts"})
        fig.update_coloraxes(showscale=False); fig.update_traces(marker_line_width=0); _show(_f(fig))
    with col2: _insight("Taux >14% = profil risque élevé.", "orange")

def _bloc_scores(data):
    lst = data if isinstance(data, list) else []
    if not lst: return
    _section("Distribution des scores crédit (300→1000)")
    df = pd.DataFrame(lst)
    if "_id" not in df.columns or "count" not in df.columns: return
    df["tranche"] = df["_id"].apply(lambda x: str(x) if x != "non_renseigne" else "N/A")
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.bar(df, x="tranche", y="count", color="count",
                     color_continuous_scale="RdYlGn", height=280, title="Clients par tranche de score",
                     labels={"tranche": "Score crédit", "count": "Nb clients"})
        fig.update_coloraxes(showscale=False); fig.update_traces(marker_line_width=0); _show(_f(fig))
    with col2:
        total = df["count"].sum()
        if total > 0:
            bons = df[df["_id"].apply(lambda x: isinstance(x, (int, float)) and x >= 670)]["count"].sum()
            mauvais = df[df["_id"].apply(lambda x: isinstance(x, (int, float)) and x < 580)]["count"].sum()
            _insight(f"**{bons / total * 100:.1f}%** bon score (≥670)", "green")
            _insight(f"**{mauvais / total * 100:.1f}%** à risque (<580)", "red")

def _bloc_score_region(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("Score crédit moyen par région")
    df = pd.DataFrame(lst).rename(columns={"_id": "Région", "score_moyen": "Score moyen"})
    if "Région" not in df.columns or "Score moyen" not in df.columns: return
    _show(_bar_h(df[df["Région"].notna()].sort_values("Score moyen", ascending=True),
                 "Score moyen", "Région", "Score crédit moyen par région", "RdYlGn", 280))

def _bloc_defauts(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("🚨 Clients en défaut de paiement")
    rows = [{"Client": f"{d.get('personal_info', {}).get('prenom', '')} {d.get('personal_info', {}).get('nom', '')}".strip(),
             "Région": d.get("personal_info", {}).get("region", "-"),
             "Score": d.get("credit_profile", {}).get("credit_score", "-"),
             "Défauts": d.get("credit_profile", {}).get("num_of_delinquencies", 0)} for d in lst]
    df = pd.DataFrame(rows)
    col1, col2 = st.columns([3, 1])
    with col1: st.dataframe(df, use_container_width=True, hide_index=True)
    with col2:
        _insight(f"**{len(df)}** clients en défaut.", "red")
        df_s = df[df["Score"] != "-"].copy(); df_s["Score"] = pd.to_numeric(df_s["Score"], errors="coerce")
        if not df_s.empty: _insight(f"Score moyen : **{df_s['Score'].mean():.0f}**", "orange")

def _bloc_accounts_type(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("Comptes par type")
    df = pd.DataFrame(lst).rename(columns={"_id": "Type", "solde_total": "Solde total", "count": "Nombre"})
    if "Type" not in df.columns: return
    df = df[df["Type"].notna()]
    if df.empty: return
    col1, col2 = st.columns(2)
    with col1:
        if "Solde total" in df.columns:
            fig = px.bar(df.sort_values("Solde total", ascending=False), x="Type", y="Solde total",
                         color="Type", height=260, title="Solde total par type", color_discrete_sequence=C)
            fig.update_traces(marker_line_width=0); _show(_f(fig))
    with col2:
        if "Solde total" in df.columns:
            _show(_pie(df, "Type", "Solde total", f"Répartition ({df['Solde total'].sum():,.0f} TND)", 260))

def _bloc_accounts_statut(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("Statuts des comptes")
    df = pd.DataFrame(lst).rename(columns={"_id": "Statut", "count": "Nombre"})
    if "Statut" not in df.columns or "Nombre" not in df.columns: return
    _show(_pie(df, "Statut", "Nombre", "Répartition par statut", 240))

def _bloc_solde(data):
    if not isinstance(data, dict): return
    c = st.columns(3)
    c[0].metric("💰 Solde total", f"{data.get('solde_total', 0):,.0f} TND")
    c[1].metric("📊 Solde moyen", f"{data.get('solde_moyen', 0):,.0f} TND")
    c[2].metric("🏦 Nb comptes", f"{data.get('count', 0):,}")

def _bloc_cheques(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("🔲 Chèques par statut")
    df = pd.DataFrame(lst).rename(columns={"_id": "Statut", "count": "Nombre"})
    if "Statut" not in df.columns or "Nombre" not in df.columns: return
    col1, col2 = st.columns(2)
    with col1: _show(_bar_v(df, "Statut", "Nombre", "Chèques par statut", C, 240))
    with col2: _show(_pie(df, "Statut", "Nombre", "Répartition", 240))

def _bloc_recovery_statut(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("⚠️ Recovery par statut")
    df = pd.DataFrame(lst).rename(columns={"_id": "Statut", "count": "Nombre"})
    if "Statut" not in df.columns or "Nombre" not in df.columns: return
    _show(_pie(df, "Statut", "Nombre", "Prêts recovery", 240, hole=0.4))

def _bloc_recovery_montants(data):
    if not isinstance(data, dict) or not data: return
    _section("⚠️ Montants en recouvrement")
    c1, c2, c3 = st.columns(3)
    c1.metric("💸 Montant total", f"{data.get('montant_total', 0):,.0f} TND")
    c2.metric("📋 Nb prêts", f"{data.get('count', 0):,}")
    nr = data.get("non_rembourses", 0); total = data.get("count", 1)
    pct = float(nr) / max(float(total), 1) * 100
    c3.metric("❌ Non remboursés", f"{pct:.1f}%", delta_color="inverse")
    col1, col2 = st.columns([2, 3])
    with col1: st.plotly_chart(_gauge(round(pct, 1), "% Non remboursés", 100, suffix="%"), 
                               use_container_width=True, key=_ukey("gauge_recovery"))
    with col2:
        c = "red" if pct > 50 else "orange" if pct > 25 else "green"
        _insight(f"**{pct:.1f}%** non remboursés ({int(nr):,} sur {int(total):,}).", c)

def _bloc_clients_region(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("Répartition des clients par région")
    df = pd.DataFrame(lst).rename(columns={"_id": "Région", "count": "Clients"})
    if "Région" not in df.columns or "Clients" not in df.columns: return
    df = df[df["Région"].notna()]
    col1, col2 = st.columns([3, 2])
    with col1: _show(_bar_h(df.sort_values("Clients", ascending=True), "Clients", "Région", "Clients par région", "Blues", 280))
    with col2:
        _show(_pie(df, "Région", "Clients", "Répartition régionale", 280))
        if len(df) > 0:
            top = df.loc[df["Clients"].idxmax(), "Région"]
            _insight(f"**{top}** = région dominante ({df['Clients'].max() / df['Clients'].sum() * 100:.1f}%).", "blue")

def _bloc_clients_genre(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("Répartition H/F")
    df = pd.DataFrame(lst).rename(columns={"_id": "Genre", "count": "Nombre"})
    if "Genre" not in df.columns or "Nombre" not in df.columns: return
    _show(_pie(df, "Genre", "Nombre", f"Répartition ({df['Nombre'].sum():,} clients)", 240))

def _bloc_revenu_region(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("Revenu annuel moyen par région")
    df = pd.DataFrame(lst).rename(columns={"_id": "Région", "revenu_moyen": "Revenu moyen"})
    if "Région" not in df.columns or "Revenu moyen" not in df.columns: return
    _show(_bar_h(df[df["Région"].notna()].sort_values("Revenu moyen", ascending=True),
                 "Revenu moyen", "Région", "Revenu annuel moyen (TND)", "Greens", 280))

def _bloc_correlation(data):
    lst = data if isinstance(data, list) else _to_list(data)
    if not lst: return
    _section("Corrélation Score crédit ↔ Revenu")
    df = pd.DataFrame(lst)
    if "score_moyen" not in df.columns or "revenu_moyen" not in df.columns: return
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.scatter(df, x="revenu_moyen", y="score_moyen",
                         size="count" if "count" in df.columns else None,
                         color="score_moyen", color_continuous_scale="RdYlGn", height=280,
                         title="Score moyen vs Revenu moyen",
                         labels={"revenu_moyen": "Revenu (TND)", "score_moyen": "Score"})
        fig.update_coloraxes(showscale=False); _show(_f(fig))
    with col2: _insight("Plus le revenu est élevé, meilleur est le score crédit.", "blue")

def _bloc_kpis_globaux(data):
    if not isinstance(data, dict): return
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Clients", f"{data.get('total_clients', 0):,}")
    c2.metric("🏦 Comptes", f"{data.get('total_accounts', 0):,}")
    c3.metric("📋 Réclamations", f"{data.get('total_reclamations', 0):,}",
              delta=f"{data.get('reclamations_ouvertes', 0)} ouvertes", delta_color="inverse")
    c4.metric("💳 Chèques", f"{data.get('total_cheques', 0):,}")
    c5.metric("⚠️ Recovery actifs", f"{data.get('compte_recouvrement_actifs', 0):,}", delta_color="inverse")

def _bloc_loans_liste(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Détail des prêts client")
    df = pd.DataFrame(lst)
    cols = [c for c in ["montant", "loan_purpose", "taux", "loan_term", "grade_subgrade",
                         "loan_paid_back", "date_debut", "date_fin"] if c in df.columns]
    col1, col2 = st.columns([2, 1])
    with col1: st.dataframe(df[cols].fillna("-") if cols else df, use_container_width=True, hide_index=True)
    with col2:
        if "loan_paid_back" in df.columns:
            cnts = df["loan_paid_back"].map({True: "✅ Remboursé", False: "⏳ En cours"}).value_counts().reset_index()
            cnts.columns = ["Statut", "Nombre"]; _show(_pie(cnts, "Statut", "Nombre", "Statut", 240))

def _bloc_accounts_client(data):
    lst = _to_list(data)
    if not lst: return
    _filtre_badge(data); _section("Comptes bancaires du client")
    df = pd.DataFrame(lst)
    cols = [c for c in ["account_number", "type", "balance", "status", "date_creation"] if c in df.columns]
    col1, col2 = st.columns([2, 1])
    with col1: st.dataframe(df[cols].fillna("-") if cols else df, use_container_width=True, hide_index=True)
    with col2:
        if "balance" in df.columns and "account_number" in df.columns:
            fig = px.bar(df, x="account_number", y="balance", color="type" if "type" in df.columns else None,
                         height=220, color_discrete_sequence=C, labels={"balance": "Solde (TND)", "account_number": "Compte"})
            fig.update_traces(marker_line_width=0); _show(_f(fig))


# ══════════════════════════════════════════════════════════════
# RAPPORT COMPLET — Dashboard plat BH Bank
# ══════════════════════════════════════════════════════════════
def render_rapport_complet(data):
    if not isinstance(data, dict): return

    # Header BH Bank
    st.markdown(f"""
    <div style="background:{NAVY}; padding:20px 24px; border-radius:12px; margin-bottom:20px;">
      <div style="display:flex; align-items:center; gap:16px;">
        <div style="font-size:28px;">🏦</div>
        <div>
          <div style="color:white; font-size:20px; font-weight:800; letter-spacing:0.5px;">BH BANK — Rapport Global</div>
          <div style="color:#9aaac5; font-size:13px; margin-top:2px;">Tableau de bord analytique · Données en temps réel</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    _section("📊 KPIs GLOBAUX")
    kpis = data.get("kpis", {})
    if kpis: _bloc_kpis_globaux(kpis)

    _hdiv(); _section("💰 COMPTES & SOLDES")
    if data.get("solde_total"): _bloc_solde(data["solde_total"])
    if data.get("accounts_type"): _bloc_accounts_type(data["accounts_type"])

    _hdiv(); _section("💳 TRANSACTIONS")
    if data.get("transactions_type"):  _bloc_txn_par_type({"data": data["transactions_type"]})
    if data.get("transactions_serie"): _bloc_txn_serie({"data": data["transactions_serie"]})

    _hdiv(); _section("📋 RÉCLAMATIONS")
    if data.get("reclamations_statut"): _bloc_reclamations_statut({"data": data["reclamations_statut"]})
    if data.get("reclamations_objet"):  _bloc_reclamations_objet({"data": data["reclamations_objet"]})
    if data.get("reclamations_serie"):  _bloc_reclamations_serie({"data": data["reclamations_serie"]})
    if data.get("delai_resolution"):    _bloc_delai_resolution(data["delai_resolution"])

    _hdiv(); _section("💼 CRÉDITS & SCORES")
    if data.get("loans_stats"): _bloc_loans_stats(data["loans_stats"])
    if data.get("loans_grade"): _bloc_loans_grade({"data": data["loans_grade"]})
    if data.get("loans_objet"): _bloc_loans_objet({"data": data["loans_objet"]})
    if data.get("scores"):      _bloc_scores(data["scores"])
    if data.get("score_region"): _bloc_score_region(data["score_region"])

    _hdiv(); _section("👥 CLIENTS")
    if data.get("clients_region"): _bloc_clients_region(data["clients_region"])
    if data.get("clients_genre"):  _bloc_clients_genre(data["clients_genre"])

    _hdiv(); _section("⚠️ CHÈQUES & RECOVERY")
    if data.get("cheques_statut"): _bloc_cheques(data["cheques_statut"])
    if data.get("recovery"):       _bloc_recovery_montants(data["recovery"])


# ══════════════════════════════════════════════════════════════
# CLIENT COMPLET — Dashboard plat BH Bank
# ══════════════════════════════════════════════════════════════
def render_client_complet(data):
    if isinstance(data, str):
        try: data = json.loads(data)
        except: st.error("Données invalides"); return
    if not data or (isinstance(data, dict) and data.get("erreur")):
        st.error(data.get("erreur", "Client non trouvé") if isinstance(data, dict) else "Client non trouvé"); return

    profil = data.get("profil", {})
    if isinstance(profil, list): profil = profil[0] if profil else {}
    pi = profil.get("personal_info", {}); emp = profil.get("employment", {})
    cp = profil.get("credit_profile", {}); cin = data.get("cin", "")
    nom = f"{pi.get('prenom', '-')} {pi.get('nom', '-')}"

    # Header client BH style
    st.markdown(f"""
    <div style="background:{NAVY}; padding:20px 24px; border-radius:12px; margin-bottom:20px;
                display:flex; align-items:center; gap:20px;">
      <div style="background:{RED}; border-radius:50%; width:56px; height:56px;
                  display:flex; align-items:center; justify-content:center;
                  font-size:24px; font-weight:800; color:white;">
        {nom[0].upper() if nom else '?'}
      </div>
      <div>
        <div style="color:white; font-size:22px; font-weight:800;">{nom}</div>
        <div style="color:#9aaac5; font-size:13px; margin-top:4px;">
          CIN : <span style="color:white; font-weight:600;">{cin}</span>
          &nbsp;·&nbsp; {pi.get('region', '-')} &nbsp;·&nbsp; {pi.get('genre', '-')}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Région", pi.get("region", "-"))
    c2.metric("Genre", pi.get("genre", "-"))
    c3.metric("Revenu", f"{emp.get('annual_income', 0):,.0f} TND" if emp.get("annual_income") else "-")
    c4.metric("Domaine", emp.get("domaine_activite", pi.get("domaine_activite", "-")))

    score = cp.get("credit_score", 0) or 0
    if score:
        col_g, col_s = st.columns([1, 2])
        with col_g: st.plotly_chart(_gauge(score, "Score Crédit", 1000), 
                                   use_container_width=True, key=_ukey("gauge_credit"))
        with col_s:
            c = st.columns(2)
            c[0].metric("Créances impayées", cp.get("num_of_delinquencies", 0))
            c[1].metric("Comptes ouverts", len(data.get("accounts", [])))
            c2x = st.columns(2)
            c2x[0].metric("Défaut historique", "Oui 🔴" if cp.get("delinquency_history") else "Non 🟢")
            c2x[1].metric("Nb prêts", len(data.get("loans", [])))

    # ── Prêts ──
    _hdiv(); _section("💼 PRÊTS")
    loans = data.get("loans", [])
    if loans:
        df_l = pd.DataFrame(loans)
        cols = [c for c in ["montant", "loan_purpose", "taux", "loan_term", "grade_subgrade", "loan_paid_back", "date_debut", "date_fin"] if c in df_l.columns]
        col1, col2 = st.columns([2, 1])
        with col1: st.dataframe(df_l[cols].fillna("-"), use_container_width=True, hide_index=True)
        with col2:
            if "loan_paid_back" in df_l.columns:
                cnts = df_l["loan_paid_back"].map({True: "✅ Remboursé", False: "⏳ En cours"}).value_counts().reset_index()
                cnts.columns = ["Statut", "Nombre"]; _show(_pie(cnts, "Statut", "Nombre", "Remboursement", 220))
        total_mt = sum(l.get("montant", 0) or 0 for l in loans)
        remb = sum(1 for l in loans if l.get("loan_paid_back"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Total encours", f"{total_mt:,.0f} TND")
        c2.metric("Remboursés", f"{remb}/{len(loans)}")
        c3.metric("Taux remboursement", f"{remb / len(loans) * 100:.1f}%" if loans else "0%")
    else: st.info("Aucun prêt.")

    # ── Réclamations ──
    _hdiv(); _section("📋 RÉCLAMATIONS")
    recl = data.get("reclamations", [])
    if recl:
        df_r = pd.DataFrame(recl)
        cols = [c for c in ["objet", "status", "date", "date_rep"] if c in df_r.columns]
        col1, col2 = st.columns([2, 1])
        with col1: st.dataframe(df_r[cols].fillna("-"), use_container_width=True, hide_index=True)
        with col2:
            if "status" in df_r.columns:
                cnts = df_r["status"].value_counts().reset_index(); cnts.columns = ["Statut", "Nombre"]
                _show(_pie(cnts, "Statut", "Nombre", "Statuts", 220))
        ouv = sum(1 for r in recl if r.get("status", "") in ["en cours", "ouverte", "ouvert", "open"])
        c1, c2 = st.columns(2)
        c1.metric("Total réclamations", f"{len(recl):,}")
        c2.metric("Ouvertes", f"{ouv:,}", delta=f"{ouv / len(recl) * 100:.1f}%" if recl else None, delta_color="inverse")
    else: st.info("Aucune réclamation.")

    # ── Comptes ──
    _hdiv(); _section("🏦 COMPTES BANCAIRES")
    accs = data.get("accounts", [])
    if accs:
        df_a = pd.DataFrame(accs)
        cols = [c for c in ["account_number", "type", "balance", "status", "date_creation"] if c in df_a.columns]
        col1, col2 = st.columns([2, 1])
        with col1: st.dataframe(df_a[cols].fillna("-"), use_container_width=True, hide_index=True)
        with col2:
            if "balance" in df_a.columns and "account_number" in df_a.columns:
                fig = px.bar(df_a, x="account_number", y="balance", color="type" if "type" in df_a.columns else None,
                             height=220, color_discrete_sequence=C, labels={"balance": "Solde (TND)", "account_number": "Compte"})
                fig.update_traces(marker_line_width=0); _show(_f(fig))
        solde_total = sum(float(a.get("balance", 0) or 0) for a in accs)
        c1, c2 = st.columns(2)
        c1.metric("Solde total", f"{solde_total:,.0f} TND")
        c2.metric("Nb comptes", f"{len(accs):,}")
    else: st.info("Aucun compte.")

    # ── Transactions ──
    _hdiv(); _section("💳 TRANSACTIONS RÉCENTES")
    txns = data.get("transactions", [])
    if txns:
        total_txn = sum(a.get("nombre_transactions", 0) for a in txns)
        total_vol = sum(float(a.get("montant_total", 0) or 0) for a in txns)
        c1, c2 = st.columns(2)
        c1.metric("Total transactions", f"{total_txn:,}")
        c2.metric("Volume total", f"{total_vol:,.0f} TND")
        for acc in txns:
            if not isinstance(acc, dict): continue
            with st.expander(f"🏦 Compte {acc.get('account_number', '')} — {acc.get('nombre_transactions', 0)} transactions"):
                last = acc.get("dernieres_transactions", [])
                if last:
                    df_t = pd.DataFrame(last).rename(columns={"date": "Date", "label": "Desc", "amount": "Montant", "type": "Type"})
                    try: df_t["Date"] = pd.to_datetime(df_t["Date"]).dt.strftime("%Y-%m-%d %H:%M")
                    except: pass
                    col1, col2 = st.columns([2, 1])
                    with col1: st.dataframe(df_t, use_container_width=True, hide_index=True)
                    with col2:
                        if "Montant" in df_t.columns:
                            fig = px.bar(df_t, x="Date", y="Montant", color="Type" if "Type" in df_t.columns else None,
                                         height=200, color_discrete_sequence=C)
                            fig.update_traces(marker_line_width=0); _show(_f(fig))
    else: st.info("Aucune transaction.")


# ══════════════════════════════════════════════════════════════
# DISPATCH
# ══════════════════════════════════════════════════════════════
RENDERERS = {
    "reclamations_kpis":               _bloc_reclamations_kpis,
    "reclamations_par_statut":         _bloc_reclamations_statut,
    "reclamations_par_objet":          _bloc_reclamations_objet,
    "reclamations_serie_temporelle":   _bloc_reclamations_serie,
    "delai_moyen_resolution":          _bloc_delai_resolution,
    "reclamations_delai_par_objet":    _bloc_delai_par_objet,
    "transactions_kpis":               _bloc_txn_kpis,
    "transactions_par_type":           _bloc_txn_par_type,
    "transactions_serie_temporelle":   _bloc_txn_serie,
    "transactions_par_heure":          _bloc_txn_par_heure,
    "transactions_top_montants":       _bloc_txn_top,
    "loans_stats_globales":            _bloc_loans_stats,
    "loans_par_grade":                 _bloc_loans_grade,
    "loans_par_objet":                 _bloc_loans_objet,
    "loans_taux_interet_distribution": _bloc_loans_taux,
    "loans_liste_client":              _bloc_loans_liste,
    "scores_credit_distribution":      _bloc_scores,
    "score_moyen_par_region":          _bloc_score_region,
    "clients_en_defaut":               _bloc_defauts,
    "accounts_par_type":               _bloc_accounts_type,
    "accounts_par_statut":             _bloc_accounts_statut,
    "solde_total_banque":              _bloc_solde,
    "accounts_du_client_detail":       _bloc_accounts_client,
    "cheques_par_statut":              _bloc_cheques,
    "recovery_par_statut":             _bloc_recovery_statut,
    "recovery_montants":               _bloc_recovery_montants,
    "clients_par_region":              _bloc_clients_region,
    "clients_par_genre":               _bloc_clients_genre,
    "revenu_moyen_par_region":         _bloc_revenu_region,
    "correlation_score_revenu":        _bloc_correlation,
    "kpis_globaux":                    _bloc_kpis_globaux,
    "rapport_complet_data":            render_rapport_complet,
    "analyse_complete_client":         render_client_complet,
}

ORDER_RECL = ["reclamations_kpis","reclamations_par_statut","reclamations_par_objet",
              "reclamations_serie_temporelle","delai_moyen_resolution","reclamations_delai_par_objet"]
ORDER_TXN  = ["transactions_kpis","transactions_par_type","transactions_serie_temporelle",
              "transactions_par_heure","transactions_top_montants"]
ORDER_CRED = ["loans_stats_globales","loans_par_grade","loans_par_objet","loans_taux_interet_distribution",
              "loans_liste_client","scores_credit_distribution","score_moyen_par_region","clients_en_defaut"]
ORDER_COMP = ["solde_total_banque","accounts_par_type","accounts_par_statut","accounts_du_client_detail",
              "cheques_par_statut","recovery_par_statut","recovery_montants"]
ORDER_CLI  = ["kpis_globaux","clients_par_region","clients_par_genre","revenu_moyen_par_region","correlation_score_revenu"]

THEME_SETS = {"recl": set(ORDER_RECL), "txn": set(ORDER_TXN), "cred": set(ORDER_CRED),
              "comp": set(ORDER_COMP),  "cli": set(ORDER_CLI)}
ORDERS = {"recl": ORDER_RECL, "txn": ORDER_TXN, "cred": ORDER_CRED, "comp": ORDER_COMP, "cli": ORDER_CLI}


def render_all(tool_results: dict):
    if not tool_results: return
    _KC.clear()
    used = set(tool_results.keys())

    def _load(tn):
        d = tool_results.get(tn)
        if isinstance(d, str):
            try: return json.loads(d)
            except: return d
        return d

    if "rapport_complet_data" in used:
        render_rapport_complet(_load("rapport_complet_data")); return
    if "analyse_complete_client" in used:
        render_client_complet(_load("analyse_complete_client")); return

    if "comparaison_deux_periodes" in used:
        raw = _load("comparaison_deux_periodes")
        if isinstance(raw, dict):
            _section("⚖️ Comparaison deux périodes")
            rows = []
            for p in [raw.get("periode_1", {}), raw.get("periode_2", {})]:
                for item in p.get("data", []):
                    rows.append({"Période": p.get("label", ""), "Type": item.get("_id", ""),
                                 "Nombre": item.get("count", 0), "Montant": item.get("total", 0)})
            if rows:
                df = pd.DataFrame(rows)
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(df, x="Type", y="Nombre", color="Période", barmode="group", height=280,
                                 color_discrete_sequence=[NAVY, RED], title="Nombre de transactions")
                    fig.update_traces(marker_line_width=0); _show(_f(fig))
                with col2:
                    fig2 = px.bar(df, x="Type", y="Montant", color="Période", barmode="group", height=280,
                                  color_discrete_sequence=[NAVY, RED], title="Montant total")
                    fig2.update_traces(marker_line_width=0); _show(_f(fig2))

    best = max(THEME_SETS, key=lambda t: len(used & THEME_SETS[t]))
    if len(used & THEME_SETS[best]) == 0:
        for tn in tool_results: RENDERERS.get(tn, lambda x: None)(_load(tn))
        return

    rendered = set()
    for tn in ORDERS[best]:
        if tn in used and tn in RENDERERS:
            RENDERERS[tn](_load(tn)); rendered.add(tn)

    skip = {"rapport_complet_data", "analyse_complete_client", "comparaison_deux_periodes"}
    for tn in tool_results:
        if tn in rendered or tn in skip: continue
        if tn in RENDERERS: RENDERERS[tn](_load(tn))


# ══════════════════════════════════════════════════════════════
# XAI & MÉMOIRE
# ══════════════════════════════════════════════════════════════
def render_xai_panel(xai: dict):
    if not xai: return
    st.markdown(f"### 🧠 Explication de l'agent (XAI)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Thème", xai.get("theme", "?").upper())
    col2.metric("🔧 Tools", f"{xai.get('tools_count', 0)}")
    col3.metric("✅ Confiance", f"{xai.get('confidence', 0):.0f}%")
    col4.metric("⏱️ Temps", f"{xai.get('execution_time', 0):.1f}s")
    if xai.get("theme_desc"): st.info(f"**Analyse :** {xai['theme_desc']}")
    if xai.get("filters"):
        _section("Filtres appliqués")
        for f in xai["filters"]: st.markdown(f'<span class="badge-navy">{f}</span>', unsafe_allow_html=True)
    if xai.get("tools_steps"):
        _section("Étapes d'exécution")
        for step in xai["tools_steps"]:
            ok = "ok" if step["status"].startswith("✅") else "error"
            st.markdown(f"""<div class="xai-step xai-step-{ok}">
              <strong>Étape {step['step']} — {step['tool']}</strong>
              <span style="float:right">{step['status']} · {step['records']} enregistrements</span><br/>
              <span style="color:#6b7a99;font-size:12px">{step['description']}</span><br/>
              <span style="font-size:11px">🔍 Filtre : <code>{step['filter']}</code></span>
              {"<br/><span style='color:" + RED + ";font-size:11px'>❌ " + step['error'] + "</span>" if step.get('error') else ""}
            </div>""", unsafe_allow_html=True)

def render_memory_panel(agent: BankReportingAgent):
    history = agent.get_full_memory()
    st.markdown("### 💾 Mémoire de l'agent")
    if not history: st.info("Aucun historique."); return
    st.caption(f"L'agent mémorise les **{len(history)}** derniers échanges.")
    for h in reversed(history):
        with st.expander(f"Tour {h['turn']} — {h['human'][:60]}..."):
            st.markdown(f'<div class="memory-human">👤 <strong>Vous :</strong><br/>{h["human"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="memory-ai">🤖 <strong>Agent :</strong><br/>{h["ai"][:400]}{"..." if len(h["ai"]) > 400 else ""}</div>', unsafe_allow_html=True)
    if st.button("🗑️ Effacer la mémoire", key="mem_clear", use_container_width=True):
        agent.clear_memory(); st.rerun()


# ══════════════════════════════════════════════════════════════
# INTERFACE PRINCIPALE — CHARTE BH BANK
# ══════════════════════════════════════════════════════════════
# ── Header BH Bank ───────────────────────────────────────────
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.markdown(f"""
    <div style="background:{NAVY}; border-radius:10px; padding:8px 14px; text-align:center;
                display:inline-block; margin-top:4px;">
      <span style="color:white; font-weight:900; font-size:18px; letter-spacing:1px;">BH</span>
      <span style="color:{RED}; font-weight:900; font-size:18px;">|</span>
      <span style="color:white; font-size:12px; font-weight:600; letter-spacing:2px;"> BANK</span>
    </div>
    """, unsafe_allow_html=True)
with col_title:
    st.markdown(f"""
    <div style="padding-top:6px;">
      <span style="font-size:20px; font-weight:800; color:{NAVY};">Dashboard Analytique & Reporting IA</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="dash-divider" style="margin-top:12px;">', unsafe_allow_html=True)

# ── Sidebar BH Navy ───────────────────────────────────────────
with st.sidebar:
    # Logo BH dans la sidebar
    st.markdown(f"""
    <div style="text-align:center; padding:16px 0 8px;">
      <div style="background:rgba(255,255,255,0.12); border-radius:10px; padding:10px; display:inline-block;">
        <span style="color:white; font-weight:900; font-size:20px;">BH</span>
        <span style="color:{RED}; font-weight:900; font-size:20px;">|</span>
        <span style="color:white; font-size:13px; font-weight:600; letter-spacing:2px;">BANK</span>
      </div>
      <div style="color:#9aaac5; font-size:11px; margin-top:8px; letter-spacing:0.5px;">DASHBOARD IA</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**💬 Historique récent**")
    agent = get_agent()
    history = agent.get_memory_summary()
    if history:
        for h in reversed(history[-3:]):
            st.markdown(f'<div class="sidebar-item">👤 {h["human"][:48]}...</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="sidebar-item">🤖 {h["ai"][:58]}...</div>', unsafe_allow_html=True)
    else:
        st.caption("Aucun historique.")
    st.divider()

    if st.button("🗑️ Effacer mémoire", use_container_width=True, key="sidebar_clear"):
        agent.clear_memory(); st.rerun()

 

# ── Boutons rapides BH ─────────────────────────────────────────
_section("Analyses rapides")

QUICK = [
    ("📋 Réclamations",  "Analyse complète des réclamations : KPIs, statuts, motifs, évolution, délais SLA"),
    ("💳 Transactions",  "Analyse complète des transactions : KPIs, volume par type, évolution mensuelle, activité horaire, top alertes"),
    ("💼 Crédits",       "Analyse portefeuille crédit : KPIs, grades, objets, taux d'intérêt, scores crédit"),
    ("🏦 Comptes",       "Analyse comptes et recovery : soldes, types, statuts, chèques, prêts en recouvrement"),
    ("👥 Clients",       "Analyse clients : régions, H/F, revenus par région, corrélation score-revenu"),
    
]

cols = st.columns(6)
for i, (col, (label, prompt_ex)) in enumerate(zip(cols, QUICK)):
    if col.button(label, key=f"quick_{i}", use_container_width=True):
        st.session_state["pending"] = prompt_ex

# ── Zone de saisie ─────────────────────────────────────────────
with st.form("chat_form", clear_on_submit=True):
    col_in, col_btn = st.columns([6, 1])
    with col_in:
        default_val = st.session_state.pop("pending", "")
        user_input = st.text_input("Prompt", value=default_val, label_visibility="collapsed",
                                   placeholder='ex: "réclamations 2024-01-01 au 2024-06-30" · "transactions CIN 12345678" ')
    with col_btn:
        submitted = st.form_submit_button("▶ Envoyer", type="primary", use_container_width=True)

st.markdown('<hr class="dash-divider">', unsafe_allow_html=True)

# ── Traitement ──────────────────────────────────────────────────
if submitted and user_input.strip():
    prompt = user_input.strip()
    st.markdown(f'<span class="badge-navy">🔍 {prompt[:]}</span>', unsafe_allow_html=True)
    progress = st.progress(0, text="🤖 Analyse en cours...")

    with st.status("⚙️ Agent BH Bank en cours...", expanded=True) as status:
        st.write("🧠 Sélection des outils d'analyse...")
        progress.progress(20)
        result       = agent.run(prompt)
        progress.progress(75)
        tools_used   = result.get("tools_used", [])
        tool_results = result.get("tool_results", {})
        xai_data     = result.get("xai", {})
        if tools_used:
            st.write(f"✅ Outils utilisés : `{', '.join(tools_used)}`")
        status.update(label="✅ Analyse terminée", state="complete")

    progress.progress(100); progress.empty()

    # Onglets avec couleurs BH
    main_tabs = st.tabs(["📈 Dashboard", "🤖 Rapport", "🧠 XAI", "💾 Mémoire"])

    with main_tabs[0]:
        if tool_results: render_all(tool_results)
        else: st.info("Aucune donnée retournée par l'agent.")

    with main_tabs[1]:
        rapport = result.get("rapport", "")
        if rapport:
            st.markdown(rapport)
            c1, c2, _ = st.columns([1, 1, 4])
            with c1: st.download_button("📥 .md", rapport, "rapport_bh.md", "text/markdown")
            with c2: st.download_button("📄 .txt", rapport, "rapport_bh.txt", "text/plain")
        else: st.info("Aucun rapport textuel généré.")

    with main_tabs[2]: render_xai_panel(xai_data)
    with main_tabs[3]: render_memory_panel(agent)

elif submitted:
    st.warning("⚠️ Saisis un prompt pour commencer.")
