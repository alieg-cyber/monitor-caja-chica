"""
config.py — Configuración central del sistema Monitor de Caja Chica.
Todas las constantes, nombres de hojas, columnas, roles y defaults se definen aquí.
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
# TIPOS DE TRANSACCIÓN
# ============================================================
TIPO_INGRESO = "Ingreso"
TIPO_EGRESO = "Egreso"
TIPO_REPOSICION = "Reposición"
TIPO_AJUSTE = "Ajuste"
TIPO_TRANSFERENCIA = "Transferencia"
TIPOS_TRANSACCION = [TIPO_INGRESO, TIPO_EGRESO, TIPO_REPOSICION, TIPO_AJUSTE, TIPO_TRANSFERENCIA]
TIPOS_POSITIVOS = {TIPO_INGRESO, TIPO_REPOSICION}
TIPOS_NEGATIVOS = {TIPO_EGRESO}
TIPOS_MIXTOS = {TIPO_AJUSTE, TIPO_TRANSFERENCIA}

# ============================================================
# CATEGORÍAS
# ============================================================
CATEGORIAS: dict[str, list[str]] = {
    TIPO_INGRESO: ["Reposición de caja", "Fondo inicial", "Devolución", "Ajuste positivo", "Otros"],
    TIPO_EGRESO: [
        "Papelería y oficina",
        "Transporte y viáticos",
        "Limpieza y mantenimiento",
        "Alimentos",
        "Servicios",
        "Gastos de representación",
        "Material de trabajo",
        "Mensajería y envíos",
        "Telecomunicaciones",
        "Otros",
    ],
    TIPO_REPOSICION: ["Reposición de caja", "Fondo adicional", "Otros"],
    TIPO_AJUSTE: ["Ajuste de saldo", "Corrección de error", "Diferencia de cambio", "Otros"],
    TIPO_TRANSFERENCIA: ["Transferencia interna", "Préstamo temporal", "Otros"],
}
TODAS_CATEGORIAS = sorted({cat for cats in CATEGORIAS.values() for cat in cats})

# ============================================================
# ESTADOS
# ============================================================
ESTADO_TX_ACTIVO = "Activo"
ESTADO_TX_ANULADO = "Anulado"

ESTADO_ALERTA_ACTIVA = "Activa"
ESTADO_ALERTA_RESUELTA = "Resuelta"
ESTADO_ALERTA_IGNORADA = "Ignorada"

ESTADO_CIERRE_PENDIENTE = "Pendiente"
ESTADO_CIERRE_CONCILIADO = "Conciliado"
ESTADO_CIERRE_CON_DIFERENCIA = "Con Diferencia"

ESTADO_USUARIO_ACTIVO = "Activo"
ESTADO_USUARIO_INACTIVO = "Inactivo"

# ============================================================
# TIPOS DE ALERTA
# ============================================================
ALERTA_SALDO_MINIMO = "Saldo Mínimo"
ALERTA_MOVIMIENTO_INUSUAL = "Movimiento Inusual"
ALERTA_POSIBLE_DUPLICADO = "Posible Duplicado"
ALERTA_CAMBIO_NO_AUTORIZADO = "Cambio No Autorizado"
ALERTA_INACTIVIDAD = "Inactividad"
ALERTA_DIFERENCIA_CONCILIACION = "Diferencia en Conciliación"
ALERTA_GASTO_SIN_AUTORIZACION = "Gasto Sin Autorización"

SEVERIDAD_ALTA = "Alta"
SEVERIDAD_MEDIA = "Media"
SEVERIDAD_BAJA = "Baja"

# ============================================================
# CONFIGURACIÓN POR DEFECTO
# (clave: (valor_default, descripcion))
# ============================================================
CONFIG_DEFAULTS: dict[str, tuple[str, str]] = {
    "SALDO_MINIMO": ("500", "Saldo mínimo antes de generar alerta"),
    "MONTO_MAXIMO_SIN_AUTORIZACION": (
        "1000", "Monto máximo de egreso sin autorización especial"
    ),
    "DIAS_INACTIVIDAD_ALERTA": ("2", "Días sin movimientos para alerta de inactividad"),
    "NOMBRE_EMPRESA": ("Mi Empresa", "Nombre de la empresa"),
    "MONEDA": ("MXN", "Moneda del sistema (ISO 4217)"),
    "PORCENTAJE_MOVIMIENTO_INUSUAL": (
        "200", "% sobre el promedio histórico que clasifica un movimiento como inusual"
    ),
    "EMAIL_ALERTAS": ("", "Email para recibir alertas automáticas (vacío = desactivado)"),
    "SMTP_HOST": ("smtp.gmail.com", "Servidor SMTP para envío de correos"),
    "SMTP_PORT": ("587", "Puerto SMTP"),
    "SMTP_USER": ("", "Usuario/email SMTP"),
    "VENTANA_DUPLICADO_MINUTOS": (
        "60", "Ventana en minutos para detectar transacciones duplicadas"
    ),
}

# ============================================================
# METADATA
# ============================================================
APP_VERSION = "1.0.0"
APP_NAME = "Monitor de Caja Chica"
