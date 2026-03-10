"""
pages/1_Dashboard.py — Visual cash fund monitoring.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

from modules.auth import require_auth
from modules.database import get_kpis, get_transactions
from config import APP_NAME, MIN_BALANCE

MIN_BALANCE = 300_000  # Cash floor — never go below this

st.set_page_config(page_title=f"Dashboard — {APP_NAME}", page_icon="$", layout="wide")

user = require_auth()
from modules.ui import render_sidebar_user
render_sidebar_user()

# ── Period selector ───────────────────────────────────────────────────────────
hoy = date.today()
PERIODS = {
    "Today":       (hoy, hoy),
    "This week":   (hoy - timedelta(days=hoy.weekday()), hoy),
    "This month":  (hoy.replace(day=1), hoy),
    "Last 30 days":(hoy - timedelta(days=30), hoy),
    "Last 90 days":(hoy - timedelta(days=90), hoy),
    "All time":    (date(2000, 1, 1), hoy),
}
col_period, _ = st.columns([2, 6])
with col_period:
    label = st.selectbox("Period", list(PERIODS.keys()), index=2, label_visibility="collapsed")
fecha_desde, fecha_hasta = PERIODS[label]

kpis = get_kpis(
    fecha_desde=fecha_desde.strftime("%Y-%m-%d"),
    fecha_hasta=fecha_hasta.strftime("%Y-%m-%d"),
)

saldo = kpis["saldo_actual"]
total_in = kpis["total_ingresos"]
total_out = kpis["total_egresos"]
net = total_in - total_out

# ── Status logic ──────────────────────────────────────────────────────────────
pct = saldo / MIN_BALANCE if MIN_BALANCE > 0 else 999
if saldo < MIN_BALANCE:
    status_color  = "#F87171"
    status_bg     = "rgba(248,113,113,0.08)"
    status_border = "rgba(248,113,113,0.3)"
    status_label  = "CRITICAL — BELOW MINIMUM"
    status_glow   = "0 0 40px rgba(248,113,113,0.25)"
elif saldo < MIN_BALANCE * 1.1:
    status_color  = "#F59E0B"
    status_bg     = "rgba(245,158,11,0.08)"
    status_border = "rgba(245,158,11,0.3)"
    status_label  = "WARNING — NEAR MINIMUM"
    status_glow   = "0 0 40px rgba(245,158,11,0.2)"
else:
    status_color  = "#34D399"
    status_bg     = "rgba(52,211,153,0.06)"
    status_border = "rgba(52,211,153,0.2)"
    status_label  = "HEALTHY"
    status_glow   = "0 0 40px rgba(52,211,153,0.15)"

gap = saldo - MIN_BALANCE
gap_str = f"+${gap:,.0f}" if gap >= 0 else f"-${abs(gap):,.0f}"

# ── Hero balance card ─────────────────────────────────────────────────────────
st.markdown(f"""
<div style="
    background:{status_bg}; border:1px solid {status_border};
    border-radius:20px; padding:2.2rem 2.4rem;
    box-shadow:{status_glow}; margin-bottom:1.5rem;
    display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1.5rem;
">
    <div>
        <div style="font-size:0.7rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.12em; margin-bottom:0.6rem;">CURRENT BALANCE</div>
        <div style="font-size:3.2rem; font-weight:800; color:#E8EDF5; letter-spacing:-0.04em; line-height:1;">${saldo:,.2f}</div>
        <div style="margin-top:0.8rem; display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap;">
            <div style="
                font-size:0.72rem; font-weight:700; color:{status_color};
                background:rgba(0,0,0,0.3); border:1px solid {status_border};
                border-radius:6px; padding:3px 10px; letter-spacing:0.08em;
            ">{status_label}</div>
            <div style="font-size:0.82rem; color:{status_color}; font-weight:600;">{gap_str} vs $300,000 floor</div>
        </div>
    </div>
    <div style="display:flex; gap:2.5rem; flex-wrap:wrap;">
        <div style="text-align:right;">
            <div style="font-size:0.65rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.1em;">Total In</div>
            <div style="font-size:1.4rem; font-weight:700; color:#34D399; margin-top:0.2rem;">+${total_in:,.0f}</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.65rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.1em;">Total Out</div>
            <div style="font-size:1.4rem; font-weight:700; color:#F87171; margin-top:0.2rem;">-${total_out:,.0f}</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.65rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.1em;">Net Flow</div>
            <div style="font-size:1.4rem; font-weight:700; color:{'#34D399' if net >= 0 else '#F87171'}; margin-top:0.2rem;">{'+'if net>=0 else ''}${net:,.0f}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Base chart layout
CHART = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#6B7280", size=11),
    xaxis=dict(gridcolor="#1A2233", linecolor="#1F2937", showline=True, zeroline=False),
    yaxis=dict(gridcolor="#1A2233", linecolor="#1F2937", showline=False, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1F2937", orientation="h", y=1.08),
    margin=dict(l=0, r=0, t=10, b=0),
)

df = get_transactions(
    activas_only=True,
    fecha_desde=fecha_desde.strftime("%Y-%m-%d"),
    fecha_hasta=fecha_hasta.strftime("%Y-%m-%d"),
)

if df.empty:
    st.info("No transactions found for the selected period.")
else:
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0)
    df["Saldo_Posterior"] = pd.to_numeric(df["Saldo_Posterior"], errors="coerce")
    df_sorted = df.sort_values("Timestamp_Creacion").reset_index(drop=True)

    # ── 1. Balance Evolution (full width, tall) ───────────────────────────────
    st.markdown("""
    <p style="font-size:0.75rem; font-weight:600; color:#9CA3AF; letter-spacing:0.1em; text-transform:uppercase; margin:0 0 0.5rem;">BALANCE EVOLUTION</p>
    """, unsafe_allow_html=True)

    fig_evo = go.Figure()

    # Red danger zone below $300k
    fig_evo.add_hrect(
        y0=0, y1=MIN_BALANCE,
        fillcolor="rgba(248,113,113,0.04)",
        line_width=0,
    )
    # Safe zone above $300k (subtle)
    bal_max = max(df_sorted["Saldo_Posterior"].max() * 1.15, MIN_BALANCE * 1.3) if not df_sorted["Saldo_Posterior"].isna().all() else MIN_BALANCE * 1.5
    fig_evo.add_hrect(
        y0=MIN_BALANCE, y1=bal_max,
        fillcolor="rgba(79,142,247,0.03)",
        line_width=0,
    )
    # $300k floor line
    fig_evo.add_hline(
        y=MIN_BALANCE,
        line_dash="dot",
        line_color="#F87171",
        line_width=1.5,
        annotation_text="$300K FLOOR",
        annotation_font_color="#F87171",
        annotation_font_size=10,
        annotation_position="right",
    )
    # Balance line
    fig_evo.add_trace(go.Scatter(
        x=df_sorted["Fecha"],
        y=df_sorted["Saldo_Posterior"],
        mode="lines+markers",
        name="Balance",
        line=dict(color="#4F8EF7", width=2.5),
        marker=dict(size=5, color="#4F8EF7"),
        fill="tozeroy",
        fillcolor="rgba(79,142,247,0.07)",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Balance: $%{y:,.2f}<extra></extra>",
    ))

    layout_evo = {**CHART}
    layout_evo["height"] = 340
    layout_evo["yaxis"] = {**CHART["yaxis"], "tickprefix": "$", "tickformat": ",.0f"}
    fig_evo.update_layout(**layout_evo)
    st.plotly_chart(fig_evo, use_container_width=True)

    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

    # ── 2. Income vs Expenses + Category breakdown ────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("""
        <p style="font-size:0.75rem; font-weight:600; color:#9CA3AF; letter-spacing:0.1em; text-transform:uppercase; margin:0 0 0.5rem;">DAILY CASH FLOW</p>
        """, unsafe_allow_html=True)

        df_daily = df_sorted.copy()
        df_daily["Day"] = df_daily["Fecha"].dt.date
        df_daily["In"]  = df_daily["Monto"].apply(lambda x: x if x > 0 else 0)
        df_daily["Out"] = df_daily["Monto"].apply(lambda x: abs(x) if x < 0 else 0)
        grp = df_daily.groupby("Day").agg(In=("In","sum"), Out=("Out","sum")).reset_index()

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=grp["Day"], y=grp["In"],
            name="Income", marker_color="#34D399", marker_opacity=0.9,
            hovertemplate="<b>%{x}</b><br>In: $%{y:,.2f}<extra></extra>",
        ))
        fig_bar.add_trace(go.Bar(
            x=grp["Day"], y=grp["Out"],
            name="Expenses", marker_color="#F87171", marker_opacity=0.9,
            hovertemplate="<b>%{x}</b><br>Out: $%{y:,.2f}<extra></extra>",
        ))
        layout_bar = {**CHART, "height": 280, "barmode": "group"}
        layout_bar["yaxis"] = {**CHART["yaxis"], "tickprefix": "$", "tickformat": ",.0f"}
        fig_bar.update_layout(**layout_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.markdown("""
        <p style="font-size:0.75rem; font-weight:600; color:#9CA3AF; letter-spacing:0.1em; text-transform:uppercase; margin:0 0 0.5rem;">SPENDING BY CATEGORY</p>
        """, unsafe_allow_html=True)

        df_out = df_sorted[df_sorted["Monto"] < 0].copy()
        if df_out.empty:
            st.info("No expenses in this period.")
        else:
            cat_data = (
                df_out.groupby("Categoria")["Monto"]
                .apply(lambda x: abs(x.sum()))
                .reset_index()
                .rename(columns={"Monto": "Total"})
                .sort_values("Total", ascending=False)
            )
            fig_pie = px.pie(
                cat_data, values="Total", names="Categoria",
                hole=0.6,
                color_discrete_sequence=["#4F8EF7","#34D399","#A78BFA","#F59E0B","#F87171","#60A5FA","#818CF8"],
            )
            fig_pie.update_traces(
                textfont_color="white",
                hovertemplate="<b>%{label}</b><br>$%{value:,.2f} (%{percent})<extra></extra>",
            )
            layout_pie = {**CHART, "height": 280}
            layout_pie.pop("xaxis", None)
            layout_pie.pop("yaxis", None)
            fig_pie.update_layout(**layout_pie)
            st.plotly_chart(fig_pie, use_container_width=True)

    # ── 3. Recent transactions ────────────────────────────────────────────────
    st.divider()
    st.markdown("""
    <p style="font-size:0.75rem; font-weight:600; color:#9CA3AF; letter-spacing:0.1em; text-transform:uppercase; margin:0 0 0.75rem;">RECENT TRANSACTIONS</p>
    """, unsafe_allow_html=True)

    cols_show = ["ID", "Fecha", "Tipo", "Categoria", "Concepto", "Monto", "Saldo_Posterior"]
    cols_exist = [c for c in cols_show if c in df_sorted.columns]
    df_last = df_sorted.head(15)[cols_exist].copy()
    df_last["Fecha"] = df_last["Fecha"].dt.strftime("%b %d, %Y")
    df_last["Monto"] = df_last["Monto"].apply(lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}")
    if "Saldo_Posterior" in df_last.columns:
        df_last["Saldo_Posterior"] = df_last["Saldo_Posterior"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else ""
        )
    df_last = df_last.rename(columns={
        "Fecha": "Date", "Tipo": "Type", "Categoria": "Category",
        "Concepto": "Description", "Monto": "Amount", "Saldo_Posterior": "Balance After",
    })
    st.dataframe(df_last, use_container_width=True, hide_index=True)

