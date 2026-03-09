"""
modules/alerts.py — Motor de reglas de alerta.
Se llama al cargar cada página para detectar condiciones anómalas.
"""
import logging
from datetime import datetime, timedelta

import pandas as pd

from config import (
    ALERTA_SALDO_MINIMO, ALERTA_MOVIMIENTO_INUSUAL, ALERTA_POSIBLE_DUPLICADO,
    ALERTA_INACTIVIDAD, ALERTA_GASTO_SIN_AUTORIZACION,
    SEVERIDAD_ALTA, SEVERIDAD_MEDIA, SEVERIDAD_BAJA,
    TIPO_EGRESO,
)
from modules.database import (
    get_transactions, get_current_balance, get_config, create_alert,
)

logger = logging.getLogger(__name__)


def run_alert_checks() -> None:
    """
    Ejecuta todas las reglas de alerta.
    Diseñado para llamarse en el arranque de cada página (falla silenciosamente).
    """
    try:
        cfg = get_config()
        saldo = get_current_balance()
        df = get_transactions(activas_only=True)

        _check_saldo_minimo(saldo, cfg)
        _check_inactividad(df, cfg)
        _check_gastos_sin_autorizacion(df, cfg)
        _check_movimientos_inusuales(df, cfg)
    except Exception as exc:
        logger.warning("Error en run_alert_checks: %s", exc)


# ──────────────────────────────────────────────
# Reglas individuales
# ──────────────────────────────────────────────

def _check_saldo_minimo(saldo: float, cfg: dict) -> None:
    try:
        minimo = float(cfg.get("SALDO_MINIMO", 500))
        if saldo < minimo:
            moneda = cfg.get("MONEDA", "MXN")
            create_alert(
                tipo=ALERTA_SALDO_MINIMO,
                descripcion=(
                    f"Saldo actual ({moneda} {saldo:,.2f}) está por debajo "
                    f"del mínimo configurado ({moneda} {minimo:,.2f})."
                ),
                severidad=SEVERIDAD_ALTA,
            )
    except Exception as exc:
        logger.warning("_check_saldo_minimo error: %s", exc)


def _check_inactividad(df: pd.DataFrame, cfg: dict) -> None:
    try:
        dias = int(cfg.get("DIAS_INACTIVIDAD_ALERTA", 2))
        if df.empty:
            create_alert(
                tipo=ALERTA_INACTIVIDAD,
                descripcion="No hay transacciones registradas en el sistema.",
                severidad=SEVERIDAD_BAJA,
            )
            return
        df2 = df.copy()
        df2["Timestamp_Creacion"] = pd.to_datetime(df2["Timestamp_Creacion"], errors="coerce")
        ultimo = df2["Timestamp_Creacion"].max()
        if pd.isna(ultimo):
            return
        delta = datetime.now() - ultimo
        if delta.days >= dias:
            create_alert(
                tipo=ALERTA_INACTIVIDAD,
                descripcion=(
                    f"Han pasado {delta.days} días sin movimientos en caja chica "
                    f"(último: {ultimo.strftime('%Y-%m-%d %H:%M')})."
                ),
                severidad=SEVERIDAD_MEDIA,
            )
    except Exception as exc:
        logger.warning("_check_inactividad error: %s", exc)


def _check_gastos_sin_autorizacion(df: pd.DataFrame, cfg: dict) -> None:
    try:
        monto_max = float(cfg.get("MONTO_MAXIMO_SIN_AUTORIZACION", 1000))
        if df.empty:
            return
        moneda = cfg.get("MONEDA", "MXN")
        cutoff = datetime.now() - timedelta(hours=24)
        df2 = df.copy()
        df2["Timestamp_Creacion"] = pd.to_datetime(df2["Timestamp_Creacion"], errors="coerce")
        df2["Monto"] = pd.to_numeric(df2["Monto"], errors="coerce")
        egresos_altos = df2[
            (df2["Tipo"] == TIPO_EGRESO)
            & (df2["Monto"].abs() > monto_max)
            & (df2["Timestamp_Creacion"] >= cutoff)
        ]
        for _, row in egresos_altos.iterrows():
            create_alert(
                tipo=ALERTA_GASTO_SIN_AUTORIZACION,
                descripcion=(
                    f"Egreso de {moneda} {abs(row['Monto']):,.2f} supera el máximo "
                    f"({moneda} {monto_max:,.2f}). Concepto: {row.get('Concepto', 'N/A')}."
                ),
                severidad=SEVERIDAD_ALTA,
                transaccion_id=str(row.get("ID", "")),
            )
    except Exception as exc:
        logger.warning("_check_gastos_sin_autorizacion error: %s", exc)


def _check_movimientos_inusuales(df: pd.DataFrame, cfg: dict) -> None:
    try:
        pct = float(cfg.get("PORCENTAJE_MOVIMIENTO_INUSUAL", 200)) / 100.0
        if df.empty:
            return
        moneda = cfg.get("MONEDA", "MXN")

        df2 = df[df["Tipo"] == TIPO_EGRESO].copy()
        if len(df2) < 5:
            return  # Necesitamos suficientes datos para calcular promedio

        df2["Monto"] = pd.to_numeric(df2["Monto"], errors="coerce").abs()
        promedio = df2["Monto"].mean()
        umbral = promedio * pct

        df2["Timestamp_Creacion"] = pd.to_datetime(df2["Timestamp_Creacion"], errors="coerce")
        cutoff = datetime.now() - timedelta(hours=24)
        recientes = df2[
            (df2["Monto"] > umbral)
            & (df2["Timestamp_Creacion"] >= cutoff)
        ]
        for _, row in recientes.iterrows():
            create_alert(
                tipo=ALERTA_MOVIMIENTO_INUSUAL,
                descripcion=(
                    f"Egreso de {moneda} {row['Monto']:,.2f} supera el {pct*100:.0f}% "
                    f"del promedio histórico ({moneda} {promedio:,.2f}). "
                    f"Concepto: {row.get('Concepto', 'N/A')}."
                ),
                severidad=SEVERIDAD_MEDIA,
                transaccion_id=str(row.get("ID", "")),
            )
    except Exception as exc:
        logger.warning("_check_movimientos_inusuales error: %s", exc)
