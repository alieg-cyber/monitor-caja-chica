"""
modules/sheets.py — Capa de acceso a Google Sheets.
Maneja la conexión, lectura y escritura a bajo nivel.
"""
import logging
import time
import os
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from config import (
    CREDENTIALS_FILE, SPREADSHEET_ID, COLS_MAP,
    SHEET_TRANSACCIONES, SHEET_USUARIOS, SHEET_CONFIGURACION,
    SHEET_BITACORA, SHEET_CIERRES, SHEET_ALERTAS,
)

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ──────────────────────────────────────────────
# Conexión (cacheada como recurso compartido)
# ──────────────────────────────────────────────

def _build_credentials() -> Credentials:
    """
    Construye las credenciales de Google.
    Orden de búsqueda:
      1. st.secrets["gcp_service_account"]  → Streamlit Cloud
      2. Archivo credentials.json local     → desarrollo local
    """
    # 1. Streamlit Cloud / secrets.toml
    try:
        sa_info = dict(st.secrets["gcp_service_account"])
        # Asegurar que el private_key tenga saltos de línea reales (no \n literal)
        if "private_key" in sa_info:
            pk = sa_info["private_key"]
            if "\\n" in pk:
                sa_info["private_key"] = pk.replace("\\n", "\n")
        return Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    except KeyError:
        pass  # No hay secrets configurados, intentar archivo local

    # 2. Archivo local
    if not os.path.exists(CREDENTIALS_FILE):
        st.error(
            f"⚠️ No se encontraron credenciales de Google.\n\n"
            f"**Local:** coloca `{CREDENTIALS_FILE}` en la carpeta del proyecto.\n\n"
            "**Streamlit Cloud:** agrega la sección `[gcp_service_account]` en Secrets."
        )
        st.stop()
    return Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)


def _get_spreadsheet_id() -> str:
    """Obtiene el SPREADSHEET_ID desde st.secrets o desde .env."""
    try:
        sid = st.secrets.get("SPREADSHEET_ID", "")
        if sid:
            return sid
    except Exception:
        pass
    if SPREADSHEET_ID:
        return SPREADSHEET_ID
    st.error(
        "⚠️ **SPREADSHEET_ID** no configurado.\n\n"
        "**Local:** agrega `SPREADSHEET_ID=...` en el archivo `.env`.\n\n"
        "**Streamlit Cloud:** agrégalo en la sección Secrets del proyecto."
    )
    st.stop()


@st.cache_resource(show_spinner=False)
def _get_client() -> gspread.Client:
    """Crea y cachea el cliente de gspread (una sola instancia por proceso)."""
    try:
        creds = _build_credentials()
        return gspread.authorize(creds)
    except Exception as exc:
        st.error(f"⚠️ Error al conectar con Google: {exc}")
        st.stop()


@st.cache_resource(show_spinner=False)
def _get_spreadsheet() -> gspread.Spreadsheet:
    """Obtiene y cachea el objeto Spreadsheet."""
    client = _get_client()
    sid = _get_spreadsheet_id()
    try:
        return client.open_by_key(sid)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("⚠️ Spreadsheet no encontrado. Verifica el SPREADSHEET_ID en `.env`.")
        st.stop()
    except Exception as exc:
        st.error(f"⚠️ Error al abrir el Spreadsheet: {exc}")
        st.stop()


def _get_worksheet(sheet_name: str) -> gspread.Worksheet:
    """Obtiene una hoja específica (sin caché, para garantizar objeto fresco)."""
    ss = _get_spreadsheet()
    try:
        return ss.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(
            f"Hoja '{sheet_name}' no encontrada. Ejecuta `setup_sheets.py` primero."
        )


# ──────────────────────────────────────────────
# Lectura
# ──────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def read_sheet(sheet_name: str) -> pd.DataFrame:
    """
    Lee todos los datos de una hoja y devuelve un DataFrame.
    Cacheado 30 segundos (TTL). Tras cualquier escritura llama a clear_cache().
    """
    try:
        ws = _get_worksheet(sheet_name)
        records = ws.get_all_records(default_blank="")
        if not records:
            return pd.DataFrame(columns=COLS_MAP.get(sheet_name, []))
        df = pd.DataFrame(records)
        return df
    except ValueError:
        raise
    except gspread.exceptions.APIError as exc:
        logger.error("APIError leyendo %s: %s", sheet_name, exc)
        raise RuntimeError(f"Error de API al leer '{sheet_name}': {exc}") from exc


def clear_cache() -> None:
    """Invalida todos los datos cacheados para forzar lectura fresca."""
    st.cache_data.clear()


# ──────────────────────────────────────────────
# Escritura
# ──────────────────────────────────────────────

def append_row(sheet_name: str, row_data: list) -> None:
    """Agrega una fila al final de la hoja."""
    try:
        ws = _get_worksheet(sheet_name)
        ws.append_row(row_data, value_input_option="USER_ENTERED")
        clear_cache()
    except gspread.exceptions.APIError as exc:
        logger.error("APIError escribiendo en %s: %s", sheet_name, exc)
        raise RuntimeError(f"Error al escribir en '{sheet_name}': {exc}") from exc


def update_row_by_index(sheet_name: str, row_index: int, row_data: list) -> None:
    """
    Actualiza una fila por índice (1-based, donde 1 = encabezado, 2 = primera fila de datos).
    """
    try:
        ws = _get_worksheet(sheet_name)
        num_cols = len(row_data)
        end_col = _col_letter(num_cols)
        ws.update(
            f"A{row_index}:{end_col}{row_index}",
            [row_data],
            value_input_option="USER_ENTERED",
        )
        clear_cache()
    except gspread.exceptions.APIError as exc:
        logger.error("APIError actualizando fila %d en %s: %s", row_index, sheet_name, exc)
        raise RuntimeError(f"Error al actualizar fila en '{sheet_name}': {exc}") from exc


def update_cell(sheet_name: str, row_index: int, col_index: int, value) -> None:
    """Actualiza una celda específica (índices 1-based)."""
    try:
        ws = _get_worksheet(sheet_name)
        ws.update_cell(row_index, col_index, value)
        clear_cache()
    except gspread.exceptions.APIError as exc:
        raise RuntimeError(f"Error al actualizar celda: {exc}") from exc


def find_row_by_id(sheet_name: str, record_id: str) -> tuple[int, dict]:
    """
    Busca una fila por su columna ID.
    Devuelve (row_number_1based, row_dict).
    Lanza ValueError si no se encuentra.
    """
    ws = _get_worksheet(sheet_name)
    records = ws.get_all_records(default_blank="")
    for i, record in enumerate(records, start=2):  # fila 1 = encabezado
        if str(record.get("ID", "")) == str(record_id):
            return i, record
    raise ValueError(f"Registro ID='{record_id}' no encontrado en '{sheet_name}'.")


# ──────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────

def generate_next_id(sheet_name: str) -> str:
    """Genera el próximo ID secuencial para una hoja (ej. TRX-0001)."""
    prefix_map = {
        SHEET_TRANSACCIONES: "TRX",
        SHEET_USUARIOS: "USR",
        SHEET_BITACORA: "BIT",
        SHEET_CIERRES: "CIE",
        SHEET_ALERTAS: "ALT",
    }
    prefix = prefix_map.get(sheet_name, sheet_name[:3].upper())
    try:
        df = read_sheet(sheet_name)
        if df.empty or "ID" not in df.columns:
            return f"{prefix}-0001"
        nums = []
        for val in df["ID"].dropna():
            parts = str(val).split("-")
            if len(parts) >= 2:
                try:
                    nums.append(int(parts[-1]))
                except ValueError:
                    pass
        nxt = max(nums) + 1 if nums else 1
        return f"{prefix}-{nxt:04d}"
    except Exception:
        return f"{prefix}-{int(time.time())}"


def _col_letter(n: int) -> str:
    """Convierte un número de columna (1-based) a letra de hoja de cálculo (A, B, …, Z, AA…)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result
