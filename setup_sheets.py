"""
setup_sheets.py — Inicialización única de la hoja de cálculo Google Sheets.
Crea todas las hojas necesarias con sus encabezados y el usuario admin por defecto.

Ejecutar UNA VEZ antes de iniciar la aplicación:
    python setup_sheets.py
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

from config import (
    SPREADSHEET_ID, CREDENTIALS_FILE,
    ALL_SHEETS, COLS_MAP,
    SHEET_USUARIOS, SHEET_CONFIGURACION,
    COLS_USUARIOS, COLS_CONFIGURACION,
    CONFIG_DEFAULTS,
    ESTADO_USUARIO_ACTIVO, ROL_ADMIN,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin1234"
DEFAULT_ADMIN_NAME = "Administrador"
DEFAULT_ADMIN_EMAIL = ""


def get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def ensure_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str, headers: list[str]) -> gspread.Worksheet:
    """Crea la hoja si no existe y agrega encabezados; si ya existe, la respeta."""
    try:
        ws = spreadsheet.worksheet(sheet_name)
        print(f"  → Hoja '{sheet_name}' ya existe, se omite creación.")
        return ws
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="USER_ENTERED")
        print(f"  ✅ Hoja '{sheet_name}' creada con {len(headers)} columnas.")
        return ws


def create_default_admin(spreadsheet: gspread.Spreadsheet) -> None:
    """Crea el usuario admin por defecto si no existe ya uno."""
    import hashlib, binascii, os as _os

    ws = spreadsheet.worksheet(SHEET_USUARIOS)
    records = ws.get_all_records(default_blank="")

    for r in records:
        if str(r.get("Rol", "")).lower() == ROL_ADMIN:
            print(f"  → Usuario admin ya existe ({r.get('Usuario')}), se omite.")
            return

    # Hash de contraseña
    salt = binascii.hexlify(_os.urandom(32)).decode()
    ITERATIONS = 260_000
    key = hashlib.pbkdf2_hmac(
        "sha256",
        DEFAULT_ADMIN_PASSWORD.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS,
    )
    pw_hash = binascii.hexlify(key).decode()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        "USR-0001",
        DEFAULT_ADMIN_USER,
        pw_hash,
        salt,
        DEFAULT_ADMIN_NAME,
        DEFAULT_ADMIN_EMAIL,
        ROL_ADMIN,
        ESTADO_USUARIO_ACTIVO,
        now,
        now,
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    print(f"  ✅ Usuario admin creado: usuario='{DEFAULT_ADMIN_USER}' / contraseña='{DEFAULT_ADMIN_PASSWORD}'")
    print("  ⚠️  IMPORTANTE: Cambia la contraseña del admin en el primer inicio de sesión.")


def populate_default_config(spreadsheet: gspread.Spreadsheet) -> None:
    """Inserta la configuración por defecto si la hoja está vacía."""
    ws = spreadsheet.worksheet(SHEET_CONFIGURACION)
    records = ws.get_all_records(default_blank="")
    existing_keys = {str(r.get("Clave")) for r in records}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    added = 0
    for clave, (valor, desc) in CONFIG_DEFAULTS.items():
        if clave not in existing_keys:
            ws.append_row([clave, valor, desc, now, "setup"], value_input_option="USER_ENTERED")
            added += 1

    if added:
        print(f"  ✅ {added} parámetros de configuración cargados.")
    else:
        print("  → Configuración ya existente, se omite.")


def main() -> None:
    print("=" * 60)
    print("  Monitor de Caja Chica — Inicialización de Google Sheets")
    print("=" * 60)

    if not SPREADSHEET_ID:
        print("\n❌ ERROR: SPREADSHEET_ID no configurado en .env")
        print("   1. Copia .env.example como .env")
        print("   2. Completa SPREADSHEET_ID y CREDENTIALS_FILE")
        sys.exit(1)

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ ERROR: Archivo '{CREDENTIALS_FILE}' no encontrado.")
        print("   Descarga las credenciales del Service Account desde Google Cloud Console.")
        sys.exit(1)

    print(f"\nConectando a Google Sheets (ID: {SPREADSHEET_ID[:20]}…)")
    try:
        client = get_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"  ✅ Conectado: '{spreadsheet.title}'")
    except gspread.exceptions.SpreadsheetNotFound:
        print("❌ Spreadsheet no encontrado. Verifica SPREADSHEET_ID.")
        sys.exit(1)
    except Exception as exc:
        print(f"❌ Error de conexión: {exc}")
        sys.exit(1)

    print("\nCreando hojas…")
    for sheet_name in ALL_SHEETS:
        headers = COLS_MAP.get(sheet_name, [])
        ensure_sheet(spreadsheet, sheet_name, headers)

    print("\nCreando usuario admin por defecto…")
    create_default_admin(spreadsheet)

    print("\nCargando configuración por defecto…")
    populate_default_config(spreadsheet)

    print("\n" + "=" * 60)
    print("  ✅ Inicialización completada.")
    print("  Ahora ejecuta:  streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
