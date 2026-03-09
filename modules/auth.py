"""
modules/auth.py — Autenticación, gestión de sesión y permisos.
Usa PBKDF2-HMAC-SHA256 para el hash de contraseñas.
"""
import hashlib
import os
import binascii
import logging
from datetime import datetime

import streamlit as st

from config import (
    ROL_ADMIN, ROL_CAPTURISTA, ROL_AUDITOR, ROLES, PERMISOS,
    ESTADO_USUARIO_ACTIVO, SHEET_USUARIOS, COLS_USUARIOS,
)
from modules.sheets import read_sheet, find_row_by_id, update_row_by_index, generate_next_id, append_row

logger = logging.getLogger(__name__)

ITERATIONS = 260_000  # NIST recomendado 2024


# ──────────────────────────────────────────────
# Hash / Verificación de contraseña
# ──────────────────────────────────────────────

def hash_password(password: str) -> tuple[str, str]:
    """
    Genera hash seguro de una contraseña.
    Devuelve (password_hash_hex, salt_hex).
    """
    salt = binascii.hexlify(os.urandom(32)).decode()
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    )
    return binascii.hexlify(key).decode(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifica una contraseña contra su hash almacenado."""
    try:
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
        )
        candidate = binascii.hexlify(key).decode()
        # Comparación en tiempo constante para evitar timing attacks
        return hashlib.compare_digest(candidate, stored_hash)
    except Exception:
        return False


# ──────────────────────────────────────────────
# Login / Logout
# ──────────────────────────────────────────────

def login(username: str, password: str) -> bool:
    """
    Valida credenciales contra la hoja Usuarios.
    Actualiza Ultimo_Acceso si es exitoso.
    Devuelve True en éxito, False en fallo.
    """
    if not username or not password:
        return False

    try:
        df = read_sheet(SHEET_USUARIOS)
        if df.empty:
            return False

        mask = df["Usuario"].astype(str).str.lower() == username.strip().lower()
        matches = df[mask]
        if matches.empty:
            return False

        row = matches.iloc[0]

        if str(row.get("Estado", "")).strip() != ESTADO_USUARIO_ACTIVO:
            st.error("Tu cuenta está desactivada. Contacta al administrador.")
            return False

        if not verify_password(password, str(row["Password_Hash"]), str(row["Salt"])):
            return False

        # Guardar sesión
        st.session_state["user"] = {
            "id": str(row["ID"]),
            "usuario": str(row["Usuario"]),
            "nombre": str(row["Nombre"]),
            "email": str(row["Email"]),
            "rol": str(row["Rol"]),
        }

        # Actualizar último acceso
        _update_ultimo_acceso(str(row["ID"]))
        return True

    except Exception as exc:
        logger.error("Error en login: %s", exc)
        st.error(f"Error al verificar credenciales: {exc}")
        return False


def logout() -> None:
    """Elimina la sesión del usuario."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def require_auth() -> dict:
    """
    Llama esta función al inicio de cada página protegida.
    Si el usuario no está autenticado, redirige al login y detiene la ejecución.
    Devuelve el dict del usuario si está autenticado.
    """
    user = st.session_state.get("user")
    if not user:
        st.warning("⚠️ Debes iniciar sesión para acceder a esta página.")
        st.page_link("app.py", label="🔑 Ir al inicio de sesión", icon="🔑")
        st.stop()
    return user


def require_permission(user: dict, permiso: str) -> None:
    """
    Verifica que el usuario tenga el permiso indicado.
    Si no lo tiene, muestra un error y detiene la ejecución.
    """
    rol = user.get("rol", "")
    permisos_rol = PERMISOS.get(rol, {})
    if not permisos_rol.get(permiso, False):
        st.error(
            f"🚫 Tu rol **{rol}** no tiene permiso para realizar esta acción: `{permiso}`."
        )
        st.stop()


def has_permission(user: dict, permiso: str) -> bool:
    """Devuelve True si el usuario tiene el permiso indicado."""
    rol = user.get("rol", "")
    return PERMISOS.get(rol, {}).get(permiso, False)


# ──────────────────────────────────────────────
# Gestión de usuarios (sólo admin)
# ──────────────────────────────────────────────

def get_users() -> list[dict]:
    """Devuelve todos los usuarios (sin campos sensibles)."""
    try:
        df = read_sheet(SHEET_USUARIOS)
        safe_cols = ["ID", "Usuario", "Nombre", "Email", "Rol", "Estado", "Ultimo_Acceso", "Fecha_Creacion"]
        existing = [c for c in safe_cols if c in df.columns]
        return df[existing].to_dict("records") if not df.empty else []
    except Exception as exc:
        logger.error("Error obteniendo usuarios: %s", exc)
        return []


def create_user(
    usuario: str,
    password: str,
    nombre: str,
    email: str,
    rol: str,
    created_by: str,
) -> tuple[bool, str]:
    """
    Crea un nuevo usuario.
    Devuelve (éxito, mensaje).
    """
    usuario = usuario.strip().lower()

    if not all([usuario, password, nombre, rol]):
        return False, "Todos los campos obligatorios deben completarse."

    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."

    if rol not in ROLES:
        return False, f"Rol inválido. Opciones: {', '.join(ROLES)}"

    # Verificar duplicado
    try:
        df = read_sheet(SHEET_USUARIOS)
        if not df.empty and usuario in df["Usuario"].astype(str).str.lower().values:
            return False, f"El usuario '{usuario}' ya existe."
    except Exception as exc:
        return False, f"Error al verificar usuario: {exc}"

    pw_hash, salt = hash_password(password)
    new_id = generate_next_id(SHEET_USUARIOS)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        new_id, usuario, pw_hash, salt, nombre, email,
        rol, ESTADO_USUARIO_ACTIVO, "", now,
    ]
    try:
        append_row(SHEET_USUARIOS, row)
        # Bitácora se registra desde el llamador
        return True, f"Usuario '{usuario}' creado exitosamente (ID: {new_id})."
    except Exception as exc:
        return False, f"Error al guardar usuario: {exc}"


def update_user_status(user_id: str, new_status: str, modified_by: str) -> tuple[bool, str]:
    """Activa o desactiva un usuario."""
    try:
        row_idx, record = find_row_by_id(SHEET_USUARIOS, user_id)
        record["Estado"] = new_status
        row_data = [record.get(c, "") for c in COLS_USUARIOS]
        update_row_by_index(SHEET_USUARIOS, row_idx, row_data)
        return True, f"Estado actualizado a '{new_status}'."
    except Exception as exc:
        return False, f"Error al actualizar estado: {exc}"


def change_password(user_id: str, new_password: str) -> tuple[bool, str]:
    """Cambia la contraseña de un usuario."""
    if len(new_password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    try:
        row_idx, record = find_row_by_id(SHEET_USUARIOS, user_id)
        new_hash, new_salt = hash_password(new_password)
        record["Password_Hash"] = new_hash
        record["Salt"] = new_salt
        row_data = [record.get(c, "") for c in COLS_USUARIOS]
        update_row_by_index(SHEET_USUARIOS, row_idx, row_data)
        return True, "Contraseña actualizada."
    except Exception as exc:
        return False, f"Error al cambiar contraseña: {exc}"


def _update_ultimo_acceso(user_id: str) -> None:
    """Actualiza el timestamp de último acceso (fallo silencioso)."""
    try:
        row_idx, record = find_row_by_id(SHEET_USUARIOS, user_id)
        record["Ultimo_Acceso"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [record.get(c, "") for c in COLS_USUARIOS]
        update_row_by_index(SHEET_USUARIOS, row_idx, row_data)
    except Exception as exc:
        logger.warning("No se pudo actualizar Ultimo_Acceso para %s: %s", user_id, exc)
