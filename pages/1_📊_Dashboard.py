"""
pages/1_📊_Dashboard.py — KPIs, gráficas y resumen ejecutivo.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

from modules.auth import require_auth, require_permission
from modules.database import get_kpis, get_transactions, get_alerts
from modules.alerts import run_alert_checks
from config import APP_NAME, TIPO_EGRESO, TIPO_INGRESO, TIPO_REPOSICION

st.set_page_config(page_title=f"Dashboard — {APP_NAME}", page_icon="📊", layout="wide")

# ──────────────────────────────────────────────
user = require_auth()
require_permission(user, "ver_dashboard")

from app import render_sidebar_user
render_sidebar_user()

try:
    run_alert_checks()
except Exception:
    pass

st.markdown("""
<div style="margin-bottom:1.5rem;">
    <p style="font-size:0.7rem; color:#4F8EF7; text-transform:uppercase; letter-spacing:0.1em; margin:0 0 0.3rem;">PANEL</p>
    <h1 style="font-size:2rem; font-weight:700; color:#E8EDF5; letter-spacing:-0.03em; margin:0;">Dashboard</h1>
</div>
""", unsafe_allow_html=True)
st.divider()

# Filtro de periodo
col_f1, col_f2, _ = st.columns([2, 2, 4])
with col_f1:
    hoy = date.today()
    opciones_periodo = {
        "Hoy": (hoy, hoy),
        "Esta semana": (hoy - timedelta(days=hoy.weekday()), hoy),
        "Este mes": (hoy.replace(day=1), hoy),
        "Últimos 30 días": (hoy - timedelta(days=30), hoy),
        "Últimos 90 días": (hoy - timedelta(days=90), hoy),
        "Todo el tiempo": (date(2000, 1, 1), hoy),
    }
    periodo_label = st.selectbox("Periodo", list(opciones_periodo.keys()), index=2)
    fecha_desde, fecha_hasta = opciones_periodo[periodo_label]

kpis = get_kpis(
    fecha_desde=fecha_desde.strftime("%Y-%m-%d"),
    fecha_hasta=fecha_hasta.strftime("%Y-%m-%d"),
)
moneda = kpis["moneda"]

# KPI Cards
k1, k2, k3, k4, k5 = st.columns(5)

saldo = kpis["saldo_actual"]
saldo_min = kpis["saldo_minimo"]
saldo_delta_color = "normal" if saldo >= saldo_min else "inverse"

with k1:
    st.metric(
        label="Saldo Actual",
        value=f"{moneda} {saldo:,.2f}",
        delta=f"Mín: {moneda} {saldo_min:,.2f}",
        delta_color=saldo_delta_color,
    )
with k2:
    st.metric(
        label="Total Ingresos",
        value=f"{moneda} {kpis['total_ingresos']:,.2f}",
    )
with k3:
    st.metric(
        label="Total Egresos",
        value=f"{moneda} {kpis['total_egresos']:,.2f}",
    )
with k4:
    st.metric(
        label="Movimientos",
        value=kpis["num_movimientos"],
    )
with k5:
    alertas = kpis["alertas_activas"]
    st.metric(
        label="Alertas Activas",
        value=alertas,
        delta="Requieren atención" if alertas > 0 else "Sin alertas",
        delta_color="inverse" if alertas > 0 else "normal",
    )

st.divider()

# Gráficas
df = get_transactions(
    activas_only=True,
    fecha_desde=fecha_desde.strftime("%Y-%m-%d"),
    fecha_hasta=fecha_hasta.strftime("%Y-%m-%d"),
)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#9CA3AF", size=11),
    xaxis=dict(gridcolor="#1F2937", linecolor="#1F2937", showline=True),
    yaxis=dict(gridcolor="#1F2937", linecolor="#1F2937", showline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1F2937"),
    margin=dict(l=0, r=0, t=30, b=0),
    height=310,
)

if df.empty:
    st.info("No hay transacciones en el periodo seleccionado.")
else:
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0)

    col_g1, col_g2 = st.columns(2)

    # 1. Evolución del saldo
    with col_g1:
        st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#E8EDF5; margin-bottom:0.5rem;'>EVOLUCIÓN DEL SALDO</p>", unsafe_allow_html=True)
        df_sorted = df.sort_values("Timestamp_Creacion").copy()
        df_sorted["Saldo_Posterior"] = pd.to_numeric(
            df_sorted["Saldo_Posterior"], errors="coerce"
        ).ffill()
        fig_saldo = go.Figure()
        fig_saldo.add_trace(go.Scatter(
            x=df_sorted["Fecha"],
            y=df_sorted["Saldo_Posterior"],
            mode="lines+markers",
            name="Saldo",
            line=dict(color="#4F8EF7", width=2),
            marker=dict(size=4),
            fill="tozeroy",
            fillcolor="rgba(79,142,247,0.08)",
        ))
        fig_saldo.add_hline(
            y=saldo_min,
            line_dash="dash",
            line_color="#F87171",
            annotation_text=f"Mínimo",
            annotation_font_color="#F87171",
        )
        fig_saldo.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig_saldo, use_container_width=True)

    # 2. Ingresos vs Egresos por día
    with col_g2:
        st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#E8EDF5; margin-bottom:0.5rem;'>INGRESOS VS EGRESOS</p>", unsafe_allow_html=True)
        df_daily = df.copy()
        df_daily["Dia"] = df_daily["Fecha"].dt.date
        df_daily["Ingresos"] = df_daily["Monto"].apply(lambda x: x if x > 0 else 0)
        df_daily["Egresos"] = df_daily["Monto"].apply(lambda x: abs(x) if x < 0 else 0)
        daily_grouped = df_daily.groupby("Dia").agg(
            Ingresos=("Ingresos", "sum"),
            Egresos=("Egresos", "sum"),
        ).reset_index()
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=daily_grouped["Dia"], y=daily_grouped["Ingresos"],
            name="Ingresos", marker_color="#34D399", marker_opacity=0.85,
        ))
        fig_bar.add_trace(go.Bar(
            x=daily_grouped["Dia"], y=daily_grouped["Egresos"],
            name="Egresos", marker_color="#F87171", marker_opacity=0.85,
        ))
        fig_bar.update_layout(barmode="group", **CHART_LAYOUT)
        st.plotly_chart(fig_bar, use_container_width=True)

    col_g3, col_g4 = st.columns(2)

    # 3. Egresos por categoría
    with col_g3:
        st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#E8EDF5; margin-bottom:0.5rem;'>EGRESOS POR CATEGORÍA</p>", unsafe_allow_html=True)
        df_egresos = df[df["Monto"] < 0].copy()
        if df_egresos.empty:
            st.info("Sin egresos en el periodo.")
        else:
            cat_data = (
                df_egresos.groupby("Categoria")["Monto"]
                .apply(lambda x: abs(x.sum()))
                .reset_index()
                .rename(columns={"Monto": "Total"})
                .sort_values("Total", ascending=False)
            )
            fig_pie = px.pie(
                cat_data, values="Total", names="Categoria",
                hole=0.55,
                color_discrete_sequence=["#4F8EF7","#34D399","#A78BFA","#F59E0B","#F87171","#60A5FA"],
            )
            fig_pie.update_traces(textfont_color="white")
            layout_pie = {**CHART_LAYOUT}
            layout_pie.pop("xaxis", None)
            layout_pie.pop("yaxis", None)
            fig_pie.update_layout(**layout_pie)
            st.plotly_chart(fig_pie, use_container_width=True)

    # 4. Top 5 mayores egresos
    with col_g4:
        st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#E8EDF5; margin-bottom:0.5rem;'>TOP 5 MAYORES EGRESOS</p>", unsafe_allow_html=True)
        df_top = df[df["Monto"] < 0].copy()
        if df_top.empty:
            st.info("Sin egresos en el periodo.")
        else:
            df_top["Absoluto"] = df_top["Monto"].abs()
            top5 = df_top.nlargest(5, "Absoluto")[["Fecha", "Concepto", "Categoria", "Absoluto", "Usuario"]]
            top5 = top5.rename(columns={"Absoluto": f"Monto ({moneda})"})
            top5[f"Monto ({moneda})"] = top5[f"Monto ({moneda})"].apply(lambda x: f"{x:,.2f}")
            top5["Fecha"] = top5["Fecha"].dt.strftime("%Y-%m-%d")
            st.dataframe(top5, use_container_width=True, hide_index=True)

    st.divider()

    # 5. Últimas transacciones
    st.subheader("🕐 Últimas 10 Transacciones")
    cols_show = ["ID", "Fecha", "Tipo", "Categoria", "Concepto", "Monto", "Saldo_Posterior", "Usuario"]
    cols_exist = [c for c in cols_show if c in df.columns]
    df_last = df.head(10)[cols_exist].copy()
    df_last["Fecha"] = df_last["Fecha"].dt.strftime("%Y-%m-%d")
    df_last["Monto"] = df_last["Monto"].apply(lambda x: f"{x:+,.2f}")
    if "Saldo_Posterior" in df_last.columns:
        df_last["Saldo_Posterior"] = pd.to_numeric(
            df_last["Saldo_Posterior"], errors="coerce"
        ).apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
    st.dataframe(df_last, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
# Alertas activas (resumen)
# ──────────────────────────────────────────────
df_alertas = get_alerts(activas_only=True)
if not df_alertas.empty:
    st.divider()
    st.subheader(f"🔔 Alertas Activas ({len(df_alertas)})")
    for _, alerta in df_alertas.iterrows():
        sev = str(alerta.get("Severidad", ""))
        icon = "🔴" if sev == "Alta" else ("🟡" if sev == "Media" else "🟢")
        with st.expander(f"{icon} [{sev}] {alerta.get('Tipo', '')}"):
            st.write(alerta.get("Descripcion", ""))
            st.caption(f"Registrada: {alerta.get('Timestamp', '')}")
            st.page_link("pages/4_🔔_Alertas.py", label="Gestionar alertas →")
