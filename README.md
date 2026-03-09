# Monitor de Caja Chica 💰

Sistema de control operativo y financiero de caja chica, basado en **Streamlit + Google Sheets**. Registro, consulta, auditoría y alertas en tiempo real.

---

## Características

| Módulo | Descripción |
|---|---|
| 📊 Dashboard | KPIs en tiempo real: saldo, ingresos, egresos, alertas activas |
| 💰 Transacciones | Registro de ingresos, egresos, reposiciones, ajustes y transferencias |
| 🔄 Conciliación | Cierres de periodo con comparación saldo esperado vs real |
| 🔔 Alertas | Detección automática de anomalías (saldo mínimo, duplicados, inactividad…) |
| 📋 Bitácora | Registro inmutable de todos los cambios con usuario y timestamp |
| ⚙️ Configuración | Gestión de usuarios, roles y parámetros del sistema |

---

## Requisitos previos

- Python 3.10 o superior
- Cuenta Google con acceso a Google Sheets
- Proyecto en Google Cloud Console con las APIs habilitadas

---

## Configuración paso a paso

### 1. Google Cloud Console

1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuevo proyecto (o usa uno existente)
3. Habilita las APIs:
   - **Google Sheets API**
   - **Google Drive API**
4. Ve a **IAM y administración → Cuentas de servicio**
5. Crea una cuenta de servicio con cualquier nombre
6. Genera una clave JSON y descárgala
7. Renómbrala como `credentials.json` y colócala en la carpeta del proyecto

### 2. Google Sheets

1. Crea una nueva hoja de cálculo en Google Sheets
2. Copia el **ID** de la URL:
   ```
   https://docs.google.com/spreadsheets/d/**AQUI_VA_EL_ID**/edit
   ```
3. Comparte la hoja con el **email del Service Account** (ej. `mi-cuenta@mi-proyecto.iam.gserviceaccount.com`) con permisos de **Editor**

### 3. Variables de entorno

```bash
# Copia el archivo de ejemplo
cp .env.example .env

# Edita .env y completa:
SPREADSHEET_ID=tu_id_aqui
CREDENTIALS_FILE=credentials.json
```

### 4. Instalación de dependencias

```bash
pip install -r requirements.txt
```

### 5. Inicialización

```bash
python setup_sheets.py
```

Esto creará todas las hojas necesarias y el usuario administrador inicial:
- **Usuario:** `admin`
- **Contraseña:** `Admin1234`

> ⚠️ **Cambia la contraseña del admin** en el primer inicio de sesión desde Configuración → Cambiar Contraseña.

### 6. Ejecutar la aplicación

```bash
streamlit run app.py
```

---

## Estructura del proyecto

```
MONITOR DE CAJA CHICA/
├── app.py                    # Punto de entrada (login + home)
├── config.py                 # Constantes y configuración global
├── setup_sheets.py           # Inicialización de Google Sheets
├── requirements.txt
├── .env.example              # Plantilla de variables de entorno
├── .env                      # Tu configuración (NO subir a control de versiones)
├── credentials.json          # Credenciales Google (NO subir a control de versiones)
│
├── modules/
│   ├── auth.py               # Autenticación y permisos
│   ├── sheets.py             # Acceso bajo nivel a Google Sheets
│   ├── database.py           # Lógica de negocio
│   ├── validators.py         # Validaciones de entrada
│   └── alerts.py             # Motor de reglas de alerta
│
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_💰_Transacciones.py
│   ├── 3_🔄_Conciliacion.py
│   ├── 4_🔔_Alertas.py
│   ├── 5_📋_Bitacora.py
│   └── 6_⚙️_Configuracion.py
│
└── .streamlit/
    └── config.toml           # Tema y configuración de Streamlit
```

---

## Roles y permisos

| Permiso | Admin | Capturista | Auditor |
|---|:---:|:---:|:---:|
| Ver dashboard | ✅ | ✅ | ✅ |
| Registrar transacciones | ✅ | ✅ | ❌ |
| Editar transacciones | ✅ | ✅ | ❌ |
| Anular transacciones | ✅ | ❌ | ❌ |
| Crear cierres | ✅ | ✅ | ❌ |
| Resolver alertas | ✅ | ❌ | ✅ |
| Ver bitácora | ✅ | ❌ | ✅ |
| Gestionar usuarios | ✅ | ❌ | ❌ |
| Cambiar configuración | ✅ | ❌ | ❌ |
| Exportar datos | ✅ | ✅ | ✅ |

---

## Alertas automáticas

El sistema detecta y genera alertas automáticamente por:

| Alerta | Condición |
|---|---|
| **Saldo Mínimo** | Saldo actual < umbral configurado |
| **Inactividad** | Sin movimientos por N días |
| **Gasto sin autorización** | Egreso > monto máximo configurado |
| **Movimiento inusual** | Egreso > N% del promedio histórico |
| **Posible duplicado** | Misma transacción en ventana de tiempo |

---

## Despliegue en Streamlit Community Cloud (gratis)

1. Sube el código a un repositorio GitHub (sin `.env` ni `credentials.json`)
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. En **Secrets** agrega:
   ```toml
   SPREADSHEET_ID = "tu_id"
   # Contenido completo del credentials.json:
   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   # ... resto de campos
   ```
5. Ajusta `modules/sheets.py` para leer credenciales desde `st.secrets` cuando no hay archivo local

---

## Seguridad

- Contraseñas hasheadas con **PBKDF2-HMAC-SHA256** (260,000 iteraciones)
- Comparación de hashes en **tiempo constante** (protección contra timing attacks)
- El archivo `credentials.json` y `.env` **nunca** deben subirse a repositorios públicos
- Permisos granulares por rol en todas las páginas
- Bitácora inmutable de todos los cambios

---

## Licencia

Proyecto de uso interno. Adaptar según necesidades de la organización.
