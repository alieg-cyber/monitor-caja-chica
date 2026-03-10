"""
config.py — Central configuration for Petty Cash Monitor.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# GOOGLE SHEETS
# ============================================================
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
CREDENTIALS_FILE: str = os.getenv("CREDENTIALS_FILE", "credentials.json")

# ============================================================
# NOMBRES DE HOJAS
# ============================================================
SHEET_TRANSACCIONES = "Transacciones"
SHEET_USUARIOS = "Usuarios"
SHEET_CONFIGURACION = "Configuracion"
SHEET_BITACORA = "Bitacora"
SHEET_CIERRES = "Cierres"
SHEET_ALERTAS = "Alertas"

ALL_SHEETS = [
    SHEET_TRANSACCIONES,
    SHEET_USUARIOS,
    SHEET_CONFIGURACION,
    SHEET_BITACORA,
    SHEET_CIERRES,
    SHEET_ALERTAS,
]

# ============================================================
# COLUMNAS POR HOJA
# ============================================================
COLS_TRANSACCIONES = [
    "ID", "Fecha", "Hora", "Tipo", "Categoria", "Concepto",
    "Monto", "Saldo_Anterior", "Saldo_Posterior", "Usuario",
    "Referencia", "Estado", "Notas",
    "Timestamp_Creacion", "Timestamp_Modificacion", "Modificado_Por",
]

COLS_USUARIOS = [
    "ID", "Usuario", "Password_Hash", "Salt",
    "Nombre", "Email", "Rol", "Estado",
    "Ultimo_Acceso", "Fecha_Creacion",
]

COLS_CONFIGURACION = [
    "Clave", "Valor", "Descripcion", "Ultima_Modificacion", "Modificado_Por",
]

COLS_BITACORA = [
    "ID", "Timestamp", "Usuario", "Accion", "Tabla",
    "Registro_ID", "Campo", "Valor_Anterior", "Valor_Nuevo", "Detalles",
]

COLS_CIERRES = [
    "ID", "Fecha_Cierre", "Periodo_Inicio", "Periodo_Fin",
    "Saldo_Inicial", "Total_Ingresos", "Total_Egresos", "Total_Ajustes",
    "Saldo_Esperado", "Saldo_Real", "Diferencia",
    "Num_Transacciones", "Estado", "Responsable", "Notas", "Timestamp",
]

COLS_ALERTAS = [
    "ID", "Timestamp", "Tipo", "Descripcion", "Severidad",
    "Estado", "Transaccion_ID", "Resuelto_Por", "Fecha_Resolucion", "Notas",
]

COLS_MAP = {
    SHEET_TRANSACCIONES: COLS_TRANSACCIONES,
    SHEET_USUARIOS: COLS_USUARIOS,
    SHEET_CONFIGURACION: COLS_CONFIGURACION,
    SHEET_BITACORA: COLS_BITACORA,
    SHEET_CIERRES: COLS_CIERRES,
    SHEET_ALERTAS: COLS_ALERTAS,
}

# ============================================================
# ROLES Y PERMISOS
# ============================================================
ROL_ADMIN = "admin"
ROL_CAPTURISTA = "capturista"
ROL_AUDITOR = "auditor"
ROLES = [ROL_ADMIN, ROL_CAPTURISTA, ROL_AUDITOR]

PERMISOS: dict[str, dict[str, bool]] = {
    ROL_ADMIN: {
        "ver_dashboard": True,
        "registrar_transaccion": True,
        "editar_transaccion": True,
        "anular_transaccion": True,
        "ver_transacciones": True,
        "hacer_conciliacion": True,
        "ver_conciliacion": True,
        "ver_alertas": True,
        "resolver_alertas": True,
        "ver_bitacora": True,
        "gestionar_usuarios": True,
        "cambiar_configuracion": True,
        "exportar_datos": True,
    },
    ROL_CAPTURISTA: {
        "ver_dashboard": True,
        "registrar_transaccion": True,
        "editar_transaccion": True,
        "anular_transaccion": False,
        "ver_transacciones": True,
        "hacer_conciliacion": True,
        "ver_conciliacion": True,
        "ver_alertas": True,
        "resolver_alertas": False,
        "ver_bitacora": False,
        "gestionar_usuarios": False,
        "cambiar_configuracion": False,
        "exportar_datos": True,
    },
    ROL_AUDITOR: {
        "ver_dashboard": True,
        "registrar_transaccion": False,
        "editar_transaccion": False,
        "anular_transaccion": False,
        "ver_transacciones": True,
        "hacer_conciliacion": False,
        "ver_conciliacion": True,
        "ver_alertas": True,
        "resolver_alertas": True,
        "ver_bitacora": True,
        "gestionar_usuarios": False,
        "cambiar_configuracion": False,
        "exportar_datos": True,
    },
}

# ============================================================
# TRANSACTION TYPES
# ============================================================
TIPO_INGRESO = "Income"
TIPO_EGRESO = "Expense"
TIPO_REPOSICION = "Replenishment"
TIPO_AJUSTE = "Adjustment"
TIPO_TRANSFERENCIA = "Transfer"
TIPOS_TRANSACCION = [TIPO_INGRESO, TIPO_EGRESO, TIPO_REPOSICION, TIPO_AJUSTE, TIPO_TRANSFERENCIA]
TIPOS_POSITIVOS = {TIPO_INGRESO, TIPO_REPOSICION}
TIPOS_NEGATIVOS = {TIPO_EGRESO}
TIPOS_MIXTOS = {TIPO_AJUSTE, TIPO_TRANSFERENCIA}

# ============================================================
# CATEGORIES
# ============================================================
CATEGORIAS: dict[str, list[str]] = {
    TIPO_INGRESO: ["Cash replenishment", "Initial fund", "Refund", "Positive adjustment", "Other"],
    TIPO_EGRESO: [
        "Office supplies",
        "Travel & transport",
        "Cleaning & maintenance",
        "Food & beverages",
        "Services",
        "Entertainment",
        "Work materials",
        "Shipping & courier",
        "Telecommunications",
        "Other",
    ],
    TIPO_REPOSICION: ["Cash replenishment", "Additional fund", "Other"],
    TIPO_AJUSTE: ["Balance adjustment", "Error correction", "Exchange difference", "Other"],
    TIPO_TRANSFERENCIA: ["Internal transfer", "Temporary loan", "Other"],
}
TODAS_CATEGORIAS = sorted({cat for cats in CATEGORIAS.values() for cat in cats})

# ============================================================
# STATES
# ============================================================
ESTADO_TX_ACTIVO = "Active"
ESTADO_TX_ANULADO = "Voided"

ESTADO_ALERTA_ACTIVA = "Active"
ESTADO_ALERTA_RESUELTA = "Resolved"
ESTADO_ALERTA_IGNORADA = "Ignored"

ESTADO_CIERRE_PENDIENTE = "Pending"
ESTADO_CIERRE_CONCILIADO = "Reconciled"
ESTADO_CIERRE_CON_DIFERENCIA = "With Difference"

ESTADO_USUARIO_ACTIVO = "Active"
ESTADO_USUARIO_INACTIVO = "Inactive"

# ============================================================
# ALERT TYPES
# ============================================================
ALERTA_SALDO_MINIMO = "Low Balance"
ALERTA_MOVIMIENTO_INUSUAL = "Unusual Movement"
ALERTA_POSIBLE_DUPLICADO = "Possible Duplicate"
ALERTA_CAMBIO_NO_AUTORIZADO = "Unauthorized Change"
ALERTA_INACTIVIDAD = "Inactivity"
ALERTA_DIFERENCIA_CONCILIACION = "Reconciliation Difference"
ALERTA_GASTO_SIN_AUTORIZACION = "Unauthorized Expense"

SEVERIDAD_ALTA = "High"
SEVERIDAD_MEDIA = "Medium"
SEVERIDAD_BAJA = "Low"

# ============================================================
# CONFIGURACIÓN POR DEFECTO
# (clave: (valor_default, descripcion))
# ============================================================
CONFIG_DEFAULTS: dict[str, tuple[str, str]] = {
    "SALDO_MINIMO": ("300000", "Minimum balance before alert"),
    "MONTO_MAXIMO_SIN_AUTORIZACION": (
        "5000", "Maximum expense amount without special authorization"
    ),
    "DIAS_INACTIVIDAD_ALERTA": ("2", "Days without movements before inactivity alert"),
    "NOMBRE_EMPRESA": ("My Company", "Company name"),
    "MONEDA": ("USD", "System currency (ISO 4217)"),
    "PORCENTAJE_MOVIMIENTO_INUSUAL": (
        "200", "% above historical average classifying a movement as unusual"
    ),
    "EMAIL_ALERTAS": ("", "Email for automatic alerts (empty = disabled)"),
    "SMTP_HOST": ("smtp.gmail.com", "SMTP server for email sending"),
    "SMTP_PORT": ("587", "SMTP port"),
    "SMTP_USER": ("", "SMTP user/email"),
    "VENTANA_DUPLICADO_MINUTOS": (
        "60", "Window in minutes to detect duplicate transactions"
    ),
}

# ============================================================
# METADATA
# ============================================================
APP_VERSION = "2.0.0"
APP_NAME = "Petty Cash Monitor"
MIN_BALANCE = 300_000  # Critical floor — never go below this
