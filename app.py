"""
app.py — Punto de entrada principal: elige entre pantalla de login o home.
"""
import streamlit as st
from config import APP_NAME, APP_VERSION
from modules.auth import login, logout, has_permission
from modules.alerts import run_alert_checks

st.set_page_config(
    page_title=APP_NAME,
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Sidebar con info de sesión (visible si logueado)
# ──────────────────────────────────────────────
def render_sidebar_user():
    user = st.session_state.get("user")
    if user:
        with st.sidebar:
            st.markdown(f"### 👤 {user['nombre']}")
            st.caption(f"🎭 Rol: **{user['rol'].capitalize()}**")
            st.caption(f"📧 {user['email']}")
            st.divider()
            if st.button("🚪 Cerrar sesión", use_container_width=True):
                logout()
                st.rerun()
            st.divider()
            st.caption(f"v{APP_VERSION} · Monitor de Caja Chica")


# ──────────────────────────────────────────────
# Pantalla de login
# ──────────────────────────────────────────────
def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.markdown(
            f"<h1 style='text-align:center'>💰 {APP_NAME}</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; color:gray;'>Control operativo y financiero en tiempo real</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        with st.form("login_form", clear_on_submit=False):
            st.subheader("🔑 Iniciar sesión")
            usuario = st.text_input("Usuario", placeholder="tu_usuario")
            password = st.text_input("Contraseña", type="password", placeholder="········")
            submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")

        if submitted:
            if not usuario or not password:
                st.error("Ingresa usuario y contraseña.")
            else:
                with st.spinner("Verificando credenciales…"):
                    ok = login(usuario, password)
                if ok:
                    st.success("✅ Acceso concedido. Redirigiendo…")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")

        st.markdown("---")
        st.caption("¿Primera vez? Ejecuta `setup_sheets.py` y usa el usuario `admin` / `Admin1234`.")


# ──────────────────────────────────────────────
# Home (post-login)
# ──────────────────────────────────────────────
def render_home():
    user = st.session_state["user"]
    render_sidebar_user()

    # Revisar alertas en background
    with st.spinner(""):
        try:
            run_alert_checks()
        except Exception:
            pass

    st.title(f"💰 {APP_NAME}")
    st.markdown(f"Bienvenido, **{user['nombre']}** — Rol: `{user['rol']}`")
    st.divider()

    # Cards de acceso rápido
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("### 📊 Dashboard\nKPIs, saldo actual y gráficas.")
        st.page_link("pages/1_📊_Dashboard.py", label="Abrir Dashboard →")
    with col2:
        st.info("### 💰 Transacciones\nRegistrar y consultar movimientos.")
        st.page_link("pages/2_💰_Transacciones.py", label="Abrir Transacciones →")
    with col3:
        st.info("### 🔄 Conciliación\nCierres y comparación de saldos.")
        st.page_link("pages/3_🔄_Conciliacion.py", label="Abrir Conciliación →")

    col4, col5, col6 = st.columns(3)
    with col4:
        st.info("### 🔔 Alertas\nDetección automática de anomalías.")
        st.page_link("pages/4_🔔_Alertas.py", label="Abrir Alertas →")
    with col5:
        st.info("### 📋 Bitácora\nHistorial completo de cambios.")
        if has_permission(user, "ver_bitacora"):
            st.page_link("pages/5_📋_Bitacora.py", label="Abrir Bitácora →")
        else:
            st.caption("🔒 Requiere rol Auditor o Admin")
    with col6:
        st.info("### ⚙️ Configuración\nUsuarios y parámetros del sistema.")
        if has_permission(user, "cambiar_configuracion"):
            st.page_link("pages/6_⚙️_Configuracion.py", label="Abrir Configuración →")
        else:
            st.caption("🔒 Requiere rol Admin")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if st.session_state.get("user"):
    render_home()
else:
    render_login()
