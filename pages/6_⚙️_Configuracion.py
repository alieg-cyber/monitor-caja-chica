"""
pages/6_⚙️_Configuracion.py — Parámetros del sistema y gestión de usuarios.
"""
import streamlit as st
import pandas as pd
import io

from modules.auth import (
    require_auth, require_permission, has_permission,
    get_users, create_user, update_user_status, change_password,
)
from modules.database import get_config, set_config, log_audit
from modules.validators import validate_user_data
from config import (
    APP_NAME, CONFIG_DEFAULTS, ROLES, ROL_ADMIN,
    ESTADO_USUARIO_ACTIVO, ESTADO_USUARIO_INACTIVO,
)

st.set_page_config(page_title=f"Configuración — {APP_NAME}", page_icon="⚙️", layout="wide")

user = require_auth()
require_permission(user, "cambiar_configuracion")

from app import render_sidebar_user
render_sidebar_user()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <p style="color:#6B7280;font-size:0.75rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:600;margin:0">ADMINISTRACIÓN</p>
  <h1 style="color:#E8EDF5;font-size:2rem;font-weight:700;margin:0.2rem 0 0">Configuración del Sistema</h1>
  <p style="color:#6B7280;font-size:0.875rem;margin:0.4rem 0 0">Solo usuarios con rol <strong style="color:#4F8EF7">Admin</strong> pueden acceder a esta sección.</p>
</div>
""", unsafe_allow_html=True)

tab_params, tab_users, tab_cambio_pw = st.tabs([
    "🔧 Parámetros", "👥 Usuarios", "🔑 Cambiar Contraseña"
])

cfg = get_config()

# ══════════════════════════════════════════════
# TAB 1 — Parámetros
# ══════════════════════════════════════════════
with tab_params:
    st.subheader("Parámetros del Sistema")

    grupos = {
        "💰 Caja Chica": ["SALDO_MINIMO", "MONTO_MAXIMO_SIN_AUTORIZACION", "MONEDA", "NOMBRE_EMPRESA"],
        "🔔 Alertas": [
            "DIAS_INACTIVIDAD_ALERTA", "PORCENTAJE_MOVIMIENTO_INUSUAL",
            "VENTANA_DUPLICADO_MINUTOS",
        ],
        "📧 Notificaciones por Email": ["EMAIL_ALERTAS", "SMTP_HOST", "SMTP_PORT", "SMTP_USER"],
    }

    with st.form("form_config"):
        nuevos_valores: dict[str, str] = {}

        for grupo, claves in grupos.items():
            st.markdown(f"### {grupo}")
            for clave in claves:
                default_val, desc = CONFIG_DEFAULTS.get(clave, ("", ""))
                val_actual = cfg.get(clave, default_val)

                if clave == "MONEDA":
                    new_val = st.selectbox(
                        f"{clave}",
                        ["MXN", "USD", "EUR", "COP", "PEN", "ARS", "CLP"],
                        index=["MXN", "USD", "EUR", "COP", "PEN", "ARS", "CLP"].index(val_actual)
                        if val_actual in ["MXN", "USD", "EUR", "COP", "PEN", "ARS", "CLP"] else 0,
                        help=desc,
                        key=f"cfg_{clave}",
                    )
                elif clave in ("SMTP_PORT",):
                    new_val = str(st.number_input(
                        clave, value=int(val_actual or 587), step=1, help=desc, key=f"cfg_{clave}"
                    ))
                elif clave in ("SALDO_MINIMO", "MONTO_MAXIMO_SIN_AUTORIZACION"):
                    new_val = str(st.number_input(
                        f"{clave}",
                        value=float(val_actual or 0),
                        step=0.01, format="%.2f", help=desc, key=f"cfg_{clave}",
                    ))
                elif clave in ("DIAS_INACTIVIDAD_ALERTA", "PORCENTAJE_MOVIMIENTO_INUSUAL", "VENTANA_DUPLICADO_MINUTOS"):
                    new_val = str(st.number_input(
                        clave, value=int(val_actual or 0), step=1, help=desc, key=f"cfg_{clave}"
                    ))
                else:
                    input_type = "password" if "PASSWORD" in clave.upper() else "default"
                    new_val = st.text_input(
                        clave,
                        value="" if "PASSWORD" in clave.upper() else val_actual,
                        type=input_type,
                        help=desc,
                        key=f"cfg_{clave}",
                    )
                nuevos_valores[clave] = new_val
            st.divider()

        guardar = st.form_submit_button("💾 Guardar Configuración", type="primary", use_container_width=True)

    if guardar:
        errores_cfg = []
        if float(nuevos_valores.get("SALDO_MINIMO", 0) or 0) < 0:
            errores_cfg.append("El saldo mínimo no puede ser negativo.")
        if float(nuevos_valores.get("MONTO_MAXIMO_SIN_AUTORIZACION", 0) or 0) <= 0:
            errores_cfg.append("El monto máximo debe ser mayor a cero.")

        if errores_cfg:
            for e in errores_cfg:
                st.error(f"❌ {e}")
        else:
            all_ok = True
            for clave, valor in nuevos_valores.items():
                if not valor and "PASSWORD" in clave.upper():
                    continue  # No sobrescribir contraseña SMTP si se deja vacía
                ok, msg = set_config(clave, valor, user["usuario"])
                if not ok:
                    st.error(f"❌ {clave}: {msg}")
                    all_ok = False
            if all_ok:
                log_audit(
                    usuario=user["usuario"],
                    accion="ACTUALIZAR_CONFIGURACION",
                    detalles=f"Claves actualizadas: {', '.join(nuevos_valores.keys())}",
                )
                st.success("✅ Configuración guardada exitosamente.")
                st.rerun()


# ══════════════════════════════════════════════
# TAB 2 — Usuarios
# ══════════════════════════════════════════════
with tab_users:
    st.subheader("Gestión de Usuarios")

    col_list, col_form = st.columns([3, 2])

    with col_list:
        st.markdown("#### Usuarios Registrados")
        users = get_users()
        if not users:
            st.info("No hay usuarios registrados aún (ejecuta setup_sheets.py).")
        else:
            df_users = pd.DataFrame(users)
            cols_u = ["ID", "Usuario", "Nombre", "Email", "Rol", "Estado", "Ultimo_Acceso"]
            cols_ex_u = [c for c in cols_u if c in df_users.columns]
            st.dataframe(df_users[cols_ex_u], use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("#### Cambiar Estado de Usuario")
            user_ids = [str(u.get("ID", "")) for u in users if str(u.get("ID")) != user["id"]]
            user_labels = {
                str(u.get("ID")): f"{u.get('Usuario')} ({u.get('Nombre')})"
                for u in users if str(u.get("ID")) != user["id"]
            }
            if user_ids:
                sel_uid = st.selectbox(
                    "Usuario a modificar",
                    user_ids,
                    format_func=lambda x: user_labels.get(x, x),
                )
                new_status = st.radio(
                    "Nuevo estado",
                    [ESTADO_USUARIO_ACTIVO, ESTADO_USUARIO_INACTIVO],
                    horizontal=True,
                )
                if st.button("⚡ Aplicar Estado"):
                    ok, msg = update_user_status(sel_uid, new_status, user["usuario"])
                    if ok:
                        log_audit(
                            usuario=user["usuario"],
                            accion=f"CAMBIAR_ESTADO_USUARIO",
                            tabla="Usuarios",
                            registro_id=sel_uid,
                            campo="Estado",
                            valor_nuevo=new_status,
                        )
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
            else:
                st.info("No hay otros usuarios disponibles.")

    with col_form:
        st.markdown("#### Crear Nuevo Usuario")
        with st.form("form_nuevo_usuario", clear_on_submit=True):
            nu_usuario = st.text_input("Nombre de usuario *", placeholder="sin espacios")
            nu_nombre = st.text_input("Nombre completo *")
            nu_email = st.text_input("Email", placeholder="usuario@empresa.com")
            nu_rol = st.selectbox("Rol *", ROLES)
            nu_password = st.text_input("Contraseña *", type="password", help="Mínimo 8 caracteres, incluye letras y números.")
            nu_password2 = st.text_input("Confirmar contraseña *", type="password")
            crear_user = st.form_submit_button("👤 Crear Usuario", type="primary", use_container_width=True)

        if crear_user:
            if nu_password != nu_password2:
                st.error("❌ Las contraseñas no coinciden.")
            else:
                errores_u = validate_user_data(nu_usuario, nu_nombre, nu_email, nu_password, nu_rol)
                if errores_u:
                    for e in errores_u:
                        st.error(f"❌ {e}")
                else:
                    ok, msg = create_user(
                        usuario=nu_usuario,
                        password=nu_password,
                        nombre=nu_nombre,
                        email=nu_email,
                        rol=nu_rol,
                        created_by=user["usuario"],
                    )
                    if ok:
                        log_audit(
                            usuario=user["usuario"],
                            accion="CREAR_USUARIO",
                            tabla="Usuarios",
                            detalles=f"Usuario: {nu_usuario} | Rol: {nu_rol}",
                        )
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")


# ══════════════════════════════════════════════
# TAB 3 — Cambiar Contraseña propia
# ══════════════════════════════════════════════
with tab_cambio_pw:
    st.subheader("Cambiar Mi Contraseña")
    st.info("Esta acción solo afecta tu propia cuenta.")

    with st.form("form_cambio_pw", clear_on_submit=True):
        pw_nueva = st.text_input("Nueva contraseña *", type="password")
        pw_nueva2 = st.text_input("Confirmar nueva contraseña *", type="password")
        cambiar_pw = st.form_submit_button("🔑 Cambiar Contraseña", type="primary")

    if cambiar_pw:
        if pw_nueva != pw_nueva2:
            st.error("❌ Las contraseñas no coinciden.")
        elif len(pw_nueva) < 8:
            st.error("❌ La contraseña debe tener al menos 8 caracteres.")
        elif not any(c.isdigit() for c in pw_nueva) or not any(c.isalpha() for c in pw_nueva):
            st.error("❌ La contraseña debe contener letras y números.")
        else:
            ok, msg = change_password(user["id"], pw_nueva)
            if ok:
                log_audit(
                    usuario=user["usuario"],
                    accion="CAMBIO_CONTRASEÑA",
                    tabla="Usuarios",
                    registro_id=user["id"],
                )
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")
