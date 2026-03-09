"""
pages/4_🔔_Alertas.py — Gestión de alertas automáticas.
"""
import streamlit as st
import pandas as pd

from modules.auth import require_auth, has_permission
from modules.database import get_alerts, resolve_alert, get_config
from modules.alerts import run_alert_checks
from config import (
    APP_NAME,
    ESTADO_ALERTA_ACTIVA, ESTADO_ALERTA_RESUELTA, ESTADO_ALERTA_IGNORADA,
    SEVERIDAD_ALTA, SEVERIDAD_MEDIA, SEVERIDAD_BAJA,
)

st.set_page_config(page_title=f"Alertas — {APP_NAME}", page_icon="🔔", layout="wide")

user = require_auth()
from app import render_sidebar_user
render_sidebar_user()

# Correr detección
with st.spinner("Verificando condiciones de alerta…"):
    try:
        run_alert_checks()
    except Exception as exc:
        st.warning(f"No se pudo completar la verificación de alertas: {exc}")

st.title("🔔 Centro de Alertas")

# ──────────────────────────────────────────────
# Tabs por estado
# ──────────────────────────────────────────────
tab_activas, tab_hist = st.tabs(["🔴 Alertas Activas", "📚 Historial"])

def _severity_icon(sev: str) -> str:
    return {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}.get(sev, "⚪")


def render_alert_card(alerta: dict, allow_actions: bool) -> None:
    icon = _severity_icon(str(alerta.get("Severidad", "")))
    sev = alerta.get("Severidad", "")
    tipo = alerta.get("Tipo", "")
    desc = alerta.get("Descripcion", "")
    ts = alerta.get("Timestamp", "")
    aid = str(alerta.get("ID", ""))

    with st.container(border=True):
        hdr_col, act_col = st.columns([3, 1])
        with hdr_col:
            st.markdown(f"**{icon} [{sev}] {tipo}**")
            st.write(desc)
            st.caption(f"ID: {aid} · Registrada: {ts}")
            if alerta.get("Transaccion_ID"):
                st.caption(f"Transacción relacionada: {alerta.get('Transaccion_ID')}")

        if allow_actions:
            with act_col:
                with st.expander("⚙️ Acciones"):
                    notas_res = st.text_input("Notas (opcional)", key=f"notas_{aid}")
                    if st.button("✅ Resolver", key=f"res_{aid}", type="primary"):
                        ok, msg = resolve_alert(aid, user["usuario"], notas_res, ignore=False)
                        st.success(msg) if ok else st.error(msg)
                        st.rerun()
                    if st.button("🙈 Ignorar", key=f"ign_{aid}"):
                        ok, msg = resolve_alert(aid, user["usuario"], notas_res, ignore=True)
                        st.success(msg) if ok else st.error(msg)
                        st.rerun()


# ──────────────────────────────────────────────
# Tab Activas
# ──────────────────────────────────────────────
with tab_activas:
    df_act = get_alerts(activas_only=True)

    if df_act.empty:
        st.success("✅ No hay alertas activas en este momento.")
    else:
        # Resumen por severidad
        n_alta = len(df_act[df_act["Severidad"] == SEVERIDAD_ALTA])
        n_media = len(df_act[df_act["Severidad"] == SEVERIDAD_MEDIA])
        n_baja = len(df_act[df_act["Severidad"] == SEVERIDAD_BAJA])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Alertas", len(df_act))
        c2.metric("🔴 Alta Severidad", n_alta)
        c3.metric("🟡 Media Severidad", n_media)
        c4.metric("🟢 Baja Severidad", n_baja)
        st.divider()

        allow = has_permission(user, "resolver_alertas")

        # Ordenar por severidad (Alta > Media > Baja)
        sev_order = {SEVERIDAD_ALTA: 0, SEVERIDAD_MEDIA: 1, SEVERIDAD_BAJA: 2}
        df_act["_order"] = df_act["Severidad"].map(sev_order).fillna(3)
        df_act = df_act.sort_values("_order").drop(columns=["_order"])

        for _, row in df_act.iterrows():
            render_alert_card(row.to_dict(), allow_actions=allow)


# ──────────────────────────────────────────────
# Tab Historial
# ──────────────────────────────────────────────
with tab_hist:
    st.subheader("Historial de Alertas")

    with st.expander("🔍 Filtros"):
        fh1, fh2 = st.columns(2)
        with fh1:
            estado_h = st.selectbox(
                "Estado",
                ["Todos", ESTADO_ALERTA_ACTIVA, ESTADO_ALERTA_RESUELTA, ESTADO_ALERTA_IGNORADA],
            )
        with fh2:
            sev_h = st.selectbox("Severidad", ["Todas", SEVERIDAD_ALTA, SEVERIDAD_MEDIA, SEVERIDAD_BAJA])

    df_all_alerts = get_alerts(activas_only=False)

    if not df_all_alerts.empty:
        if estado_h != "Todos":
            df_all_alerts = df_all_alerts[df_all_alerts["Estado"].astype(str) == estado_h]
        if sev_h != "Todas":
            df_all_alerts = df_all_alerts[df_all_alerts["Severidad"].astype(str) == sev_h]

    if df_all_alerts.empty:
        st.info("ℹ️ No hay alertas con los filtros aplicados.")
    else:
        cols_show = ["ID", "Timestamp", "Tipo", "Descripcion", "Severidad", "Estado",
                     "Transaccion_ID", "Resuelto_Por", "Fecha_Resolucion"]
        cols_ex = [c for c in cols_show if c in df_all_alerts.columns]
        df_disp = df_all_alerts[cols_ex].copy()
        if "Timestamp" in df_disp.columns:
            df_disp["Timestamp"] = pd.to_datetime(df_disp["Timestamp"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

        st.dataframe(df_disp, use_container_width=True, hide_index=True, height=400)

        import io
        csv_buf = io.StringIO()
        df_all_alerts[cols_ex].to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ Exportar Alertas CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name="alertas.csv",
            mime="text/csv",
        )
