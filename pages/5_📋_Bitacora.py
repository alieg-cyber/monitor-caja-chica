"""
pages/5_📋_Bitacora.py — Historial de auditoría: quién hizo qué y cuándo.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io

from modules.auth import require_auth, require_permission
from modules.database import get_audit_log
from config import APP_NAME

st.set_page_config(page_title=f"Bitácora — {APP_NAME}", page_icon="📋", layout="wide")

user = require_auth()
require_permission(user, "ver_bitacora")

from app import render_sidebar_user
render_sidebar_user()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <p style="color:#6B7280;font-size:0.75rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:600;margin:0">AUDITORÍA</p>
  <h1 style="color:#E8EDF5;font-size:2rem;font-weight:700;margin:0.2rem 0 0">Bitácora de Auditoría</h1>
  <p style="color:#6B7280;font-size:0.875rem;margin:0.4rem 0 0">Registro inmutable de todos los cambios realizados en el sistema.</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Filtros
# ──────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=True):
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        hoy = date.today()
        f_desde = st.date_input("Desde", value=hoy - timedelta(days=30), key="bit_desde")
    with fc2:
        f_hasta = st.date_input("Hasta", value=hoy, key="bit_hasta")
    with fc3:
        user_f = st.text_input("Usuario", placeholder="Buscar por usuario")
    with fc4:
        accion_f = st.text_input("Acción", placeholder="ej. CREAR, EDITAR, ANULAR")

    limit_f = st.slider("Máximo de registros", min_value=50, max_value=2000, value=500, step=50)

# ──────────────────────────────────────────────
# Datos
# ──────────────────────────────────────────────
df = get_audit_log(
    limit=limit_f,
    usuario_filter=user_f,
    accion_filter=accion_f,
    fecha_desde=f_desde.strftime("%Y-%m-%d"),
    fecha_hasta=f_hasta.strftime("%Y-%m-%d"),
)

if df.empty:
    st.info("ℹ️ No hay registros de auditoría con los filtros aplicados.")
else:
    # Métricas rápidas
    acciones_unicas = df["Accion"].nunique() if "Accion" in df.columns else 0
    usuarios_unicas = df["Usuario"].nunique() if "Usuario" in df.columns else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Registros encontrados", len(df))
    m2.metric("Acciones distintas", acciones_unicas)
    m3.metric("Usuarios involucrados", usuarios_unicas)
    st.divider()

    # Si hay columna Timestamp, formatearla
    df_disp = df.copy()
    if "Timestamp" in df_disp.columns:
        df_disp["Timestamp"] = pd.to_datetime(df_disp["Timestamp"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    cols_order = ["ID", "Timestamp", "Usuario", "Accion", "Tabla",
                  "Registro_ID", "Campo", "Valor_Anterior", "Valor_Nuevo", "Detalles"]
    cols_ex = [c for c in cols_order if c in df_disp.columns]

    st.dataframe(
        df_disp[cols_ex],
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "Valor_Anterior": st.column_config.TextColumn(width="medium"),
            "Valor_Nuevo": st.column_config.TextColumn(width="medium"),
            "Detalles": st.column_config.TextColumn(width="large"),
        },
    )

    # Detalle de entrada seleccionada
    st.divider()
    st.subheader("🔎 Detalle de Entrada")
    ids = df["ID"].astype(str).tolist()
    sel_id = st.selectbox("Selecciona un registro", ["— seleccionar —"] + ids, key="bit_sel")
    if sel_id and sel_id != "— seleccionar —":
        row = df[df["ID"].astype(str) == sel_id]
        if not row.empty:
            r = row.iloc[0].to_dict()
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**ID:** {r.get('ID')}")
                st.markdown(f"**Timestamp:** {r.get('Timestamp')}")
                st.markdown(f"**Usuario:** {r.get('Usuario')}")
                st.markdown(f"**Acción:** `{r.get('Accion')}`")
                st.markdown(f"**Tabla:** {r.get('Tabla')}")
                st.markdown(f"**Registro ID:** {r.get('Registro_ID')}")
            with col_b:
                if r.get("Campo"):
                    st.markdown(f"**Campo modificado:** `{r.get('Campo')}`")
                    st.markdown("**Valor anterior:**")
                    st.code(str(r.get("Valor_Anterior", "")))
                    st.markdown("**Valor nuevo:**")
                    st.code(str(r.get("Valor_Nuevo", "")))
                if r.get("Detalles"):
                    st.markdown(f"**Detalles:** {r.get('Detalles')}")

    # Exportar
    st.divider()
    csv_buf = io.StringIO()
    df[cols_ex].to_csv(csv_buf, index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ Exportar Bitácora CSV",
        data=csv_buf.getvalue().encode("utf-8-sig"),
        file_name=f"bitacora_{f_desde}_{f_hasta}.csv",
        mime="text/csv",
    )
