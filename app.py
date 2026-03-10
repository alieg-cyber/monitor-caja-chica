"""
app.py — Main entry point: login screen or home.
"""
import streamlit as st
from config import APP_NAME, APP_VERSION
from modules.auth import login, logout
from modules.ui import render_sidebar_user

st.set_page_config(
    page_title=APP_NAME,
    page_icon="$",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

[data-testid="stHeader"] { display: none; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1B2A 0%, #0A0F1E 100%);
    border-right: 1px solid #1F2937;
}

[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    color: #6B7280 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
[data-testid="stMetricValue"] {
    font-size: 1.55rem !important;
    font-weight: 600 !important;
    color: #E8EDF5 !important;
}

[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #4F8EF7, #3B6FD4) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
[data-testid="baseButton-primary"]:hover { opacity: 0.85 !important; }

[data-testid="baseButton-secondary"] {
    background: #1A2233 !important;
    border: 1px solid #1F2937 !important;
    border-radius: 8px !important;
    color: #E8EDF5 !important;
}

[data-baseweb="input"] > div {
    background: #111827 !important;
    border: 1px solid #1F2937 !important;
    border-radius: 8px !important;
}
[data-baseweb="input"]:focus-within > div {
    border-color: #4F8EF7 !important;
    box-shadow: 0 0 0 3px rgba(79,142,247,0.15) !important;
}
input, textarea { color: #E8EDF5 !important; }

[data-baseweb="select"] > div {
    background: #111827 !important;
    border: 1px solid #1F2937 !important;
    border-radius: 8px !important;
}

[data-baseweb="tab-list"] { border-bottom: 1px solid #1F2937 !important; gap: 0.25rem; }
button[data-baseweb="tab"] {
    border-radius: 6px 6px 0 0 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

hr { border-color: #1F2937 !important; opacity: 1 !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0A0F1E; }
::-webkit-scrollbar-thumb { background: #1F2937; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #374151; }

[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #1F2937; }
[data-testid="stAlert"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


def render_home():
    user = st.session_state["user"]
    render_sidebar_user()────────────────
def render_login():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center; margin-bottom:2.5rem;">
            <div style="
                display:inline-flex; align-items:center; justify-content:center;
                width:56px; height:56px; border-radius:16px;
                background:linear-gradient(135deg, #4F8EF7, #3B6FD4);
                margin-bottom:1.2rem;
            ">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                    <rect x="2" y="7" width="20" height="14" rx="3" stroke="white" stroke-width="1.8" fill="none"/>
                    <path d="M16 7V5a4 4 0 0 0-8 0v2" stroke="white" stroke-width="1.8" stroke-linecap="round" fill="none"/>
                    <circle cx="12" cy="14" r="2" fill="white"/>
                </svg>
            </div>
            <h2 style="margin:0; font-size:1.6rem; font-weight:800; color:#E8EDF5; letter-spacing:-0.04em;">Petty Cash Monitor</h2>
            <p style="margin:0.5rem 0 0; font-size:0.82rem; color:#4B5563;">Real-time cash fund tracking</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#111827; border:1px solid #1F2937; border-radius:16px;
            padding:2rem 2rem 1.5rem; box-shadow:0 30px 60px rgba(0,0,0,0.6);">
            <p style="font-size:0.7rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.1em; margin:0 0 1.5rem;">System Access</p>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            usuario = st.text_input("Username", placeholder="your username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if not usuario or not password:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Verifying…"):
                    ok = login(usuario, password)
                if ok:
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.caption("First time: `admin` / `Admin1234`")


# ── Home ──────────────────────────────────────────────────────────────────────
NAV_CARDS = [
    {"title": "Dashboard",    "desc": "Balance evolution, charts & fund health.", "page": "pages/1_📊_Dashboard.py",    "color": "#4F8EF7"},
    {"title": "Transactions", "desc": "Record income, expenses & replenishments.", "page": "pages/2_💰_Transacciones.py", "color": "#34D399"},
]

def render_home():
    user = st.session_state["user"]
    render_sidebar_user()

    st.markdown(f"""
    <div style="margin-bottom:2.5rem;">
        <p style="font-size:0.7rem; color:#4F8EF7; text-transform:uppercase; letter-spacing:0.1em; margin:0 0 0.3rem;">MAIN PANEL</p>
        <h1 style="font-size:2.2rem; font-weight:800; color:#E8EDF5; letter-spacing:-0.04em; margin:0 0 0.4rem;">Petty Cash Monitor</h1>
        <p style="color:#6B7280; margin:0;">Welcome back, <span style="color:#E8EDF5; font-weight:500;">{user['nombre']}</span></p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    cols = st.columns(2)
    for i, card in enumerate(NAV_CARDS):
        with cols[i]:
            st.markdown(f"""
            <div style="
                background:#111827; border:1px solid #1F2937;
                border-top:3px solid {card['color']};
                border-radius:14px; padding:1.6rem 1.6rem 1.2rem;
            ">
                <div style="font-size:1.05rem; font-weight:700; color:#E8EDF5; margin-bottom:0.5rem;">{card['title']}</div>
                <div style="font-size:0.82rem; color:#9CA3AF; line-height:1.7;">{card['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.page_link(card["page"], label=f"Open {card['title']} →")


# ── Main ──────────────────────────────────────────────────────────────────────
if st.session_state.get("user"):
    render_home()
else:
    render_login()


