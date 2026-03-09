"""
modules/database.py — Lógica de negocio para transacciones, bitácora,
configuración, cierres y alertas.
"""
import logging
from datetime import datetime, timedelta

import pandas as pd

from config import (
    SHEET_TRANSACCIONES, SHEET_BITACORA, SHEET_CONFIGURACION,
    SHEET_CIERRES, SHEET_ALERTAS,
    COLS_TRANSACCIONES, COLS_BITACORA, COLS_CONFIGURACION,
    COLS_CIERRES, COLS_ALERTAS,
    TIPO_INGRESO, TIPO_EGRESO, TIPO_REPOSICION, TIPO_AJUSTE, TIPO_TRANSFERENCIA,
    TIPOS_POSITIVOS, TIPOS_NEGATIVOS,
    ESTADO_TX_ACTIVO, ESTADO_TX_ANULADO,
    ESTADO_ALERTA_ACTIVA, ESTADO_ALERTA_RESUELTA, ESTADO_ALERTA_IGNORADA,
    ESTADO_CIERRE_PENDIENTE, ESTADO_CIERRE_CONCILIADO, ESTADO_CIERRE_CON_DIFERENCIA,
    CONFIG_DEFAULTS,
)
from modules.sheets import (
    read_sheet, append_row, update_row_by_index,
    find_row_by_id, generate_next_id,
)

logger = logging.getLogger(__name__)

_TS_FMT = "%Y-%m-%d %H:%M:%S"


def _now() -> str:
    return datetime.now().strftime(_TS_FMT)


# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

def get_config() -> dict[str, str]:
    """
    Devuelve la configuración actual como dict {clave: valor}.
    Si un valor no existe en Sheets, usa el default.
    """
    defaults = {k: v[0] for k, v in CONFIG_DEFAULTS.items()}
    try:
        df = read_sheet(SHEET_CONFIGURACION)
        if not df.empty and "Clave" in df.columns:
            stored = dict(zip(df["Clave"].astype(str), df["Valor"].astype(str)))
            defaults.update(stored)
    except Exception as exc:
        logger.warning("No se pudo leer configuración: %s", exc)
    return defaults


def set_config(clave: str, valor: str, modified_by: str) -> tuple[bool, str]:
    """Actualiza o inserta un valor de configuración."""
    try:
        df = read_sheet(SHEET_CONFIGURACION)
        now = _now()
        if not df.empty and "Clave" in df.columns:
            ws_records = df.to_dict("records")
            for i, rec in enumerate(ws_records, start=2):
                if str(rec.get("Clave")) == clave:
                    desc = CONFIG_DEFAULTS.get(clave, ("", rec.get("Descripcion", "")))[1]
                    new_row = [clave, valor, desc, now, modified_by]
                    update_row_by_index(SHEET_CONFIGURACION, i, new_row)
                    return True, f"Configuración '{clave}' actualizada."
        # Insertar nueva
        desc = CONFIG_DEFAULTS.get(clave, ("", ""))[1]
        append_row(SHEET_CONFIGURACION, [clave, valor, desc, now, modified_by])
        return True, f"Configuración '{clave}' guardada."
    except Exception as exc:
        return False, f"Error al guardar configuración: {exc}"


# ══════════════════════════════════════════════════════════════
# BITÁCORA DE AUDITORÍA
# ══════════════════════════════════════════════════════════════

def log_audit(
    usuario: str,
    accion: str,
    tabla: str = "",
    registro_id: str = "",
    campo: str = "",
    valor_anterior: str = "",
    valor_nuevo: str = "",
    detalles: str = "",
) -> None:
    """Registra una entrada en la bitácora. Fallo silencioso para no interrumpir flujo."""
    try:
        new_id = generate_next_id(SHEET_BITACORA)
        row = [
            new_id, _now(), usuario, accion, tabla,
            registro_id, campo, valor_anterior, valor_nuevo, detalles,
        ]
        append_row(SHEET_BITACORA, row)
    except Exception as exc:
        logger.warning("No se pudo escribir en bitácora: %s", exc)


def get_audit_log(
    limit: int = 500,
    usuario_filter: str = "",
    accion_filter: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
) -> pd.DataFrame:
    """Devuelve la bitácora filtrada y ordenada por timestamp descendente."""
    try:
        df = read_sheet(SHEET_BITACORA)
        if df.empty:
            return df

        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        if usuario_filter:
            df = df[df["Usuario"].astype(str).str.contains(usuario_filter, case=False, na=False)]
        if accion_filter:
            df = df[df["Accion"].astype(str).str.contains(accion_filter, case=False, na=False)]
        if fecha_desde:
            df = df[df["Timestamp"] >= pd.to_datetime(fecha_desde)]
        if fecha_hasta:
            df = df[df["Timestamp"] <= pd.to_datetime(fecha_hasta) + timedelta(days=1)]

        df = df.sort_values("Timestamp", ascending=False).head(limit)
        return df.reset_index(drop=True)
    except Exception as exc:
        logger.error("Error obteniendo bitácora: %s", exc)
        return pd.DataFrame(columns=COLS_BITACORA)


# ══════════════════════════════════════════════════════════════
# TRANSACCIONES
# ══════════════════════════════════════════════════════════════

def monto_con_signo(tipo: str, monto: float) -> float:
    """Aplica el signo correcto según el tipo de transacción."""
    if tipo in TIPOS_POSITIVOS:
        return abs(monto)
    if tipo in TIPOS_NEGATIVOS:
        return -abs(monto)
    return monto  # Ajuste / Transferencia: el usuario controla el signo


def get_transactions(
    activas_only: bool = False,
    fecha_desde: str = "",
    fecha_hasta: str = "",
    tipo_filter: str = "",
    categoria_filter: str = "",
    usuario_filter: str = "",
) -> pd.DataFrame:
    """Devuelve las transacciones con filtros opcionales."""
    try:
        df = read_sheet(SHEET_TRANSACCIONES)
        if df.empty:
            return df

        df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)
        df["Saldo_Anterior"] = pd.to_numeric(df["Saldo_Anterior"], errors="coerce").fillna(0.0)
        df["Saldo_Posterior"] = pd.to_numeric(df["Saldo_Posterior"], errors="coerce").fillna(0.0)
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

        if activas_only:
            df = df[df["Estado"].astype(str) == ESTADO_TX_ACTIVO]
        if fecha_desde:
            df = df[df["Fecha"] >= pd.to_datetime(fecha_desde)]
        if fecha_hasta:
            df = df[df["Fecha"] <= pd.to_datetime(fecha_hasta)]
        if tipo_filter:
            df = df[df["Tipo"].astype(str) == tipo_filter]
        if categoria_filter:
            df = df[df["Categoria"].astype(str).str.contains(categoria_filter, case=False, na=False)]
        if usuario_filter:
            df = df[df["Usuario"].astype(str).str.contains(usuario_filter, case=False, na=False)]

        df = df.sort_values("Timestamp_Creacion", ascending=False).reset_index(drop=True)
        return df
    except Exception as exc:
        logger.error("Error obteniendo transacciones: %s", exc)
        return pd.DataFrame(columns=COLS_TRANSACCIONES)


def get_current_balance() -> float:
    """Calcula el saldo actual sumando todos los montos activos."""
    try:
        df = read_sheet(SHEET_TRANSACCIONES)
        if df.empty or "Monto" not in df.columns:
            return 0.0
        df = df[df["Estado"].astype(str) == ESTADO_TX_ACTIVO]
        return float(pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0).sum())
    except Exception as exc:
        logger.error("Error calculando saldo: %s", exc)
        return 0.0


def add_transaction(
    tipo: str,
    categoria: str,
    concepto: str,
    monto_raw: float,
    usuario: str,
    referencia: str = "",
    notas: str = "",
    fecha_override: str = "",
) -> tuple[bool, str, str]:
    """
    Registra una nueva transacción.
    Devuelve (éxito, mensaje, nuevo_id).
    """
    now_dt = datetime.now()
    fecha = fecha_override if fecha_override else now_dt.strftime("%Y-%m-%d")
    hora = now_dt.strftime("%H:%M:%S")
    ts = now_dt.strftime(_TS_FMT)

    monto = monto_con_signo(tipo, monto_raw)
    saldo_anterior = get_current_balance()
    saldo_posterior = saldo_anterior + monto
    new_id = generate_next_id(SHEET_TRANSACCIONES)

    row = [
        new_id, fecha, hora, tipo, categoria, concepto,
        monto, saldo_anterior, saldo_posterior, usuario,
        referencia, ESTADO_TX_ACTIVO, notas, ts, "", "",
    ]
    try:
        append_row(SHEET_TRANSACCIONES, row)
        log_audit(
            usuario=usuario,
            accion="CREAR_TRANSACCION",
            tabla=SHEET_TRANSACCIONES,
            registro_id=new_id,
            detalles=f"{tipo} | {concepto} | ${monto:,.2f}",
        )
        return True, f"Transacción {new_id} registrada exitosamente.", new_id
    except Exception as exc:
        return False, f"Error al guardar transacción: {exc}", ""


def update_transaction(
    tx_id: str,
    changes: dict,
    modified_by: str,
) -> tuple[bool, str]:
    """
    Actualiza campos de una transacción existente.
    `changes` es un dict {campo: nuevo_valor}.
    Recalcula el saldo_posterior si se modifica el monto.
    """
    try:
        row_idx, record = find_row_by_id(SHEET_TRANSACCIONES, tx_id)

        if str(record.get("Estado")) == ESTADO_TX_ANULADO:
            return False, "No se puede editar una transacción anulada."

        old_values = {k: record.get(k, "") for k in changes}

        # Si cambia el monto o el tipo, recalcular saldo_posterior
        tipo = changes.get("Tipo", record.get("Tipo"))
        monto_raw = changes.get("Monto", record.get("Monto", 0))
        try:
            monto_raw = float(monto_raw)
        except (ValueError, TypeError):
            monto_raw = 0.0

        new_monto = monto_con_signo(tipo, monto_raw)
        if "Monto" in changes or "Tipo" in changes:
            saldo_ant = float(record.get("Saldo_Anterior", 0) or 0)
            changes["Monto"] = new_monto
            changes["Saldo_Posterior"] = saldo_ant + new_monto

        now = _now()
        for k, v in changes.items():
            record[k] = v
        record["Timestamp_Modificacion"] = now
        record["Modificado_Por"] = modified_by

        row_data = [record.get(c, "") for c in COLS_TRANSACCIONES]
        update_row_by_index(SHEET_TRANSACCIONES, row_idx, row_data)

        for campo, val_ant in old_values.items():
            log_audit(
                usuario=modified_by,
                accion="EDITAR_TRANSACCION",
                tabla=SHEET_TRANSACCIONES,
                registro_id=tx_id,
                campo=campo,
                valor_anterior=str(val_ant),
                valor_nuevo=str(changes.get(campo, "")),
            )
        return True, f"Transacción {tx_id} actualizada."
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, f"Error al actualizar transacción: {exc}"


def void_transaction(tx_id: str, motivo: str, modified_by: str) -> tuple[bool, str]:
    """Anula una transacción (cambio de estado, no elimina)."""
    try:
        row_idx, record = find_row_by_id(SHEET_TRANSACCIONES, tx_id)
        if str(record.get("Estado")) == ESTADO_TX_ANULADO:
            return False, "La transacción ya está anulada."

        record["Estado"] = ESTADO_TX_ANULADO
        record["Notas"] = f"[ANULADA: {motivo}] " + str(record.get("Notas", ""))
        record["Timestamp_Modificacion"] = _now()
        record["Modificado_Por"] = modified_by

        row_data = [record.get(c, "") for c in COLS_TRANSACCIONES]
        update_row_by_index(SHEET_TRANSACCIONES, row_idx, row_data)

        log_audit(
            usuario=modified_by,
            accion="ANULAR_TRANSACCION",
            tabla=SHEET_TRANSACCIONES,
            registro_id=tx_id,
            detalles=f"Motivo: {motivo}",
        )
        return True, f"Transacción {tx_id} anulada."
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, f"Error al anular transacción: {exc}"


# ══════════════════════════════════════════════════════════════
# ALERTAS
# ══════════════════════════════════════════════════════════════

def get_alerts(activas_only: bool = True) -> pd.DataFrame:
    """Devuelve alertas, opcionalmente sólo las activas."""
    try:
        df = read_sheet(SHEET_ALERTAS)
        if df.empty:
            return df
        if activas_only:
            df = df[df["Estado"].astype(str) == ESTADO_ALERTA_ACTIVA]
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        return df.sort_values("Timestamp", ascending=False).reset_index(drop=True)
    except Exception as exc:
        logger.error("Error obteniendo alertas: %s", exc)
        return pd.DataFrame(columns=COLS_ALERTAS)


def create_alert(
    tipo: str,
    descripcion: str,
    severidad: str,
    transaccion_id: str = "",
) -> None:
    """Crea una nueva alerta. Evita duplicados activos del mismo tipo."""
    try:
        df = read_sheet(SHEET_ALERTAS)
        # Evitar alerta duplicada activa del mismo tipo
        if not df.empty:
            dup = df[
                (df["Tipo"].astype(str) == tipo)
                & (df["Estado"].astype(str) == ESTADO_ALERTA_ACTIVA)
            ]
            if not dup.empty:
                return  # Ya existe alerta activa de este tipo

        new_id = generate_next_id(SHEET_ALERTAS)
        row = [
            new_id, _now(), tipo, descripcion, severidad,
            ESTADO_ALERTA_ACTIVA, transaccion_id, "", "", "",
        ]
        append_row(SHEET_ALERTAS, row)
    except Exception as exc:
        logger.warning("No se pudo crear alerta: %s", exc)


def resolve_alert(
    alert_id: str,
    resolved_by: str,
    notas: str = "",
    ignore: bool = False,
) -> tuple[bool, str]:
    """Marca una alerta como resuelta o ignorada."""
    try:
        row_idx, record = find_row_by_id(SHEET_ALERTAS, alert_id)
        record["Estado"] = ESTADO_ALERTA_IGNORADA if ignore else ESTADO_ALERTA_RESUELTA
        record["Resuelto_Por"] = resolved_by
        record["Fecha_Resolucion"] = _now()
        record["Notas"] = notas
        row_data = [record.get(c, "") for c in COLS_ALERTAS]
        update_row_by_index(SHEET_ALERTAS, row_idx, row_data)
        log_audit(
            usuario=resolved_by,
            accion="RESOLVER_ALERTA" if not ignore else "IGNORAR_ALERTA",
            tabla=SHEET_ALERTAS,
            registro_id=alert_id,
            detalles=notas,
        )
        return True, "Alerta actualizada."
    except Exception as exc:
        return False, f"Error al actualizar alerta: {exc}"


# ══════════════════════════════════════════════════════════════
# CIERRES / CONCILIACIÓN
# ══════════════════════════════════════════════════════════════

def get_closures() -> pd.DataFrame:
    """Devuelve todos los cierres ordenados por fecha descendente."""
    try:
        df = read_sheet(SHEET_CIERRES)
        if df.empty:
            return df
        df["Fecha_Cierre"] = pd.to_datetime(df["Fecha_Cierre"], errors="coerce")
        return df.sort_values("Fecha_Cierre", ascending=False).reset_index(drop=True)
    except Exception as exc:
        logger.error("Error obteniendo cierres: %s", exc)
        return pd.DataFrame(columns=COLS_CIERRES)


def create_closure(
    periodo_inicio: str,
    periodo_fin: str,
    saldo_real: float,
    responsable: str,
    notas: str = "",
) -> tuple[bool, str, dict]:
    """
    Crea un cierre de periodo.
    Calcula automáticamente ingresos, egresos, saldo esperado y diferencia.
    Devuelve (éxito, mensaje, resumen_dict).
    """
    try:
        df_tx = get_transactions(
            activas_only=True,
            fecha_desde=periodo_inicio,
            fecha_hasta=periodo_fin,
        )

        # Saldo inicial: saldo_posterior del último movimiento ANTES del periodo
        all_tx = get_transactions(activas_only=True)
        all_tx["Fecha"] = pd.to_datetime(all_tx["Fecha"], errors="coerce")
        previas = all_tx[all_tx["Fecha"] < pd.to_datetime(periodo_inicio)]
        if previas.empty:
            saldo_inicial = 0.0
        else:
            previas = previas.sort_values("Timestamp_Creacion")
            saldo_inicial = float(previas.iloc[-1].get("Saldo_Posterior", 0) or 0)

        total_ingresos = float(
            df_tx[df_tx["Monto"] > 0]["Monto"].sum() if not df_tx.empty else 0
        )
        total_egresos = float(
            abs(df_tx[df_tx["Monto"] < 0]["Monto"].sum()) if not df_tx.empty else 0
        )
        total_ajustes = float(
            df_tx[df_tx["Tipo"].isin([TIPO_AJUSTE, TIPO_TRANSFERENCIA])]["Monto"].sum()
            if not df_tx.empty else 0
        )
        saldo_esperado = saldo_inicial + total_ingresos - total_egresos
        diferencia = round(saldo_real - saldo_esperado, 2)
        estado = ESTADO_CIERRE_CONCILIADO if diferencia == 0 else ESTADO_CIERRE_CON_DIFERENCIA
        num_tx = len(df_tx)
        new_id = generate_next_id(SHEET_CIERRES)
        fecha_cierre = datetime.now().strftime("%Y-%m-%d")

        row = [
            new_id, fecha_cierre, periodo_inicio, periodo_fin,
            round(saldo_inicial, 2), round(total_ingresos, 2),
            round(total_egresos, 2), round(total_ajustes, 2),
            round(saldo_esperado, 2), round(saldo_real, 2),
            diferencia, num_tx, estado, responsable, notas, _now(),
        ]
        append_row(SHEET_CIERRES, row)

        log_audit(
            usuario=responsable,
            accion="CREAR_CIERRE",
            tabla=SHEET_CIERRES,
            registro_id=new_id,
            detalles=(
                f"Periodo {periodo_inicio}→{periodo_fin} | "
                f"Esperado: ${saldo_esperado:,.2f} | Real: ${saldo_real:,.2f} | "
                f"Diferencia: ${diferencia:,.2f}"
            ),
        )

        resumen = {
            "id": new_id,
            "saldo_inicial": saldo_inicial,
            "total_ingresos": total_ingresos,
            "total_egresos": total_egresos,
            "total_ajustes": total_ajustes,
            "saldo_esperado": saldo_esperado,
            "saldo_real": saldo_real,
            "diferencia": diferencia,
            "num_tx": num_tx,
            "estado": estado,
        }
        return True, f"Cierre {new_id} creado. Estado: {estado}.", resumen
    except Exception as exc:
        return False, f"Error al crear cierre: {exc}", {}


# ══════════════════════════════════════════════════════════════
# KPIs PARA DASHBOARD
# ══════════════════════════════════════════════════════════════

def get_kpis(fecha_desde: str = "", fecha_hasta: str = "") -> dict:
    """Calcula KPIs principales para el dashboard."""
    cfg = get_config()
    saldo_actual = get_current_balance()

    all_tx = get_transactions(activas_only=True)
    if all_tx.empty:
        return {
            "saldo_actual": saldo_actual,
            "total_ingresos": 0.0,
            "total_egresos": 0.0,
            "num_movimientos": 0,
            "alertas_activas": len(get_alerts(activas_only=True)),
            "saldo_minimo": float(cfg.get("SALDO_MINIMO", 500)),
            "moneda": cfg.get("MONEDA", "MXN"),
        }

    all_tx["Fecha"] = pd.to_datetime(all_tx["Fecha"], errors="coerce")
    periodo = all_tx.copy()
    if fecha_desde:
        periodo = periodo[periodo["Fecha"] >= pd.to_datetime(fecha_desde)]
    if fecha_hasta:
        periodo = periodo[periodo["Fecha"] <= pd.to_datetime(fecha_hasta)]

    total_ingresos = float(periodo[periodo["Monto"] > 0]["Monto"].sum())
    total_egresos = float(abs(periodo[periodo["Monto"] < 0]["Monto"].sum()))

    return {
        "saldo_actual": saldo_actual,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "num_movimientos": len(periodo),
        "alertas_activas": len(get_alerts(activas_only=True)),
        "saldo_minimo": float(cfg.get("SALDO_MINIMO", 500)),
        "moneda": cfg.get("MONEDA", "MXN"),
    }
