"""
modules/validators.py — Reglas de validación de entradas.
"""
from datetime import datetime, date
from config import (
    TIPOS_TRANSACCION, TODAS_CATEGORIAS,
    TIPO_AJUSTE, TIPO_TRANSFERENCIA, TIPO_EGRESO,
)


def validate_transaction(
    tipo: str,
    categoria: str,
    concepto: str,
    monto: float,
    fecha: date,
    referencia: str = "",
) -> list[str]:
    """
    Valida los campos de una transacción.
    Devuelve lista de mensajes de error (vacía si todo es válido).
    """
    errors: list[str] = []

    # Tipo
    if tipo not in TIPOS_TRANSACCION:
        errors.append(f"Tipo inválido: '{tipo}'.")

    # Categoría
    if not categoria or not categoria.strip():
        errors.append("La categoría es obligatoria.")

    # Concepto
    if not concepto or not concepto.strip():
        errors.append("El concepto es obligatorio.")
    elif len(concepto.strip()) < 3:
        errors.append("El concepto debe tener al menos 3 caracteres.")
    elif len(concepto.strip()) > 200:
        errors.append("El concepto no puede superar 200 caracteres.")

    # Monto
    if monto is None:
        errors.append("El monto es obligatorio.")
    elif monto == 0:
        errors.append("El monto no puede ser cero.")
    elif abs(monto) > 10_000_000:
        errors.append("El monto supera el límite permitido (10,000,000).")

    # Para ajustes y transferencias, el concepto es más crítico
    if tipo in (TIPO_AJUSTE, TIPO_TRANSFERENCIA):
        if not concepto or len(concepto.strip()) < 10:
            errors.append(
                f"Para '{tipo}', el motivo/concepto debe ser descriptivo (mínimo 10 caracteres)."
            )

    # Fecha
    if fecha is None:
        errors.append("La fecha es obligatoria.")
    else:
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Formato de fecha inválido (usa YYYY-MM-DD).")
                return errors
        today = date.today()
        if fecha > today:
            errors.append("La fecha no puede ser futura.")
        if (today - fecha).days > 365:
            errors.append("La fecha no puede ser mayor a 1 año en el pasado.")

    return errors


def validate_closure_dates(inicio: str, fin: str) -> list[str]:
    """Valida las fechas de un cierre de periodo."""
    errors: list[str] = []
    try:
        d_inicio = datetime.strptime(inicio, "%Y-%m-%d").date()
        d_fin = datetime.strptime(fin, "%Y-%m-%d").date()
    except ValueError:
        errors.append("Formato de fecha inválido (usa YYYY-MM-DD).")
        return errors

    if d_inicio > d_fin:
        errors.append("La fecha de inicio debe ser anterior a la fecha de fin.")
    if (d_fin - d_inicio).days > 365:
        errors.append("El periodo no puede superar un año.")
    if d_fin > date.today():
        errors.append("La fecha de fin no puede ser futura.")
    return errors


def check_possible_duplicate(
    tipo: str,
    concepto: str,
    monto: float,
    transactions_df,
    ventana_minutos: int = 60,
) -> bool:
    """
    Devuelve True si existe una transacción similar reciente (posible duplicado).
    Criterio: mismo tipo + mismo monto + concepto similar en la ventana de tiempo.
    """
    if transactions_df is None or transactions_df.empty:
        return False

    import pandas as pd
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(minutes=ventana_minutos)
    recent = transactions_df.copy()

    try:
        recent["Timestamp_Creacion"] = pd.to_datetime(
            recent["Timestamp_Creacion"], errors="coerce"
        )
        recent = recent[recent["Timestamp_Creacion"] >= cutoff]
        recent["Monto"] = pd.to_numeric(recent["Monto"], errors="coerce")

        concepto_lower = concepto.strip().lower()
        matches = recent[
            (recent["Tipo"].astype(str) == tipo)
            & (recent["Monto"].round(2) == round(monto, 2))
            & (recent["Concepto"].astype(str).str.lower() == concepto_lower)
        ]
        return not matches.empty
    except Exception:
        return False


def validate_user_data(usuario: str, nombre: str, email: str, password: str, rol: str) -> list[str]:
    """Valida los datos de un nuevo usuario."""
    import re
    errors: list[str] = []

    if not usuario or not usuario.strip():
        errors.append("El nombre de usuario es obligatorio.")
    elif len(usuario.strip()) < 3:
        errors.append("El usuario debe tener al menos 3 caracteres.")
    elif not re.match(r"^[a-zA-Z0-9._-]+$", usuario.strip()):
        errors.append("El usuario solo puede contener letras, números, puntos, guiones y guiones bajos.")

    if not nombre or not nombre.strip():
        errors.append("El nombre completo es obligatorio.")

    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()):
        errors.append("El email no tiene un formato válido.")

    if not password:
        errors.append("La contraseña es obligatoria.")
    elif len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres.")
    elif not any(c.isdigit() for c in password):
        errors.append("La contraseña debe contener al menos un número.")
    elif not any(c.isalpha() for c in password):
        errors.append("La contraseña debe contener al menos una letra.")

    from config import ROLES
    if rol not in ROLES:
        errors.append(f"Rol inválido. Opciones: {', '.join(ROLES)}")

    return errors
