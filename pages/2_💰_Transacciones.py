"""
pages/2_Transactions.py — Log and view petty cash movements.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io

from modules.auth import require_auth, has_permission
from modules.database import (
    get_transactions, add_transaction, get_current_balance,
)
from config import (
    APP_NAME, TIPOS_TRANSACCION, CATEGORIAS,
    TIPO_INGRESO, TIPO_EGRESO, TIPO_REPOSICION, TIPO_AJUSTE, TIPO_TRANSFERENCIA,
    ESTADO_TX_ACTIVO, ESTADO_TX_ANULADO,
)

st.set_page_config(page_title=f"Transactions — {APP_NAME}", page_icon="$", layout="wide")

user = require_auth()
from modules.ui import render_sidebar_user
render_sidebar_user()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <p style="color:#6B7280;font-size:0.75rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:600;margin:0">MOVEMENTS</p>
  <h1 style="color:#E8EDF5;font-size:2rem;font-weight:800;margin:0.2rem 0 0;letter-spacing:-0.03em">Transactions</h1>
</div>
""", unsafe_allow_html=True)

tab_add, tab_history = st.tabs(["Add Transaction", "History"])

# ══════════════════════════════════════════════
# TAB 1 — Add Transaction
# ══════════════════════════════════════════════
with tab_add:
    if not has_permission(user, "registrar_transaccion"):
        st.error("You don't have permission to record transactions.")
        st.stop()

    saldo_actual = get_current_balance()
    st.metric("Current Balance", f"${saldo_actual:,.2f}")
    st.divider()

    with st.form("form_add_tx", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Type", TIPOS_TRANSACCION)
            cats = CATEGORIAS.get(tipo, ["Other"])
            categoria = st.selectbox("Category", cats)
            concepto = st.text_input("Description", max_chars=200, placeholder="Brief description of the movement")

        with col2:
            monto_input = st.number_input(
                "Amount (USD)",
                min_value=0.01,
                max_value=10_000_000.0,
                step=0.01,
                format="%.2f",
            )
            fecha_tx = st.date_input("Date", value=date.today(), max_value=date.today())
            referencia = st.text_input("Reference / Receipt #", max_chars=100, placeholder="Invoice, folio, etc.")

        notas = st.text_area("Notes (optional)", max_chars=300)
        submitted = st.form_submit_button("Save Transaction", type="primary", use_container_width=True)

    if submitted:
        if not concepto or len(concepto.strip()) < 3:
            st.error("Description must be at least 3 characters.")
        elif monto_input <= 0:
            st.error("Amount must be greater than 0.")
        else:
            if tipo in (TIPO_INGRESO, TIPO_REPOSICION):
                monto_raw = abs(monto_input)
            elif tipo == TIPO_EGRESO:
                monto_raw = abs(monto_input)
            else:
                monto_raw = monto_input

            ok, msg, new_id = add_transaction(
                tipo=tipo,
                categoria=categoria,
                concepto=concepto.strip(),
                monto_raw=monto_raw,
                usuario=user["usuario"],
                referencia=referencia,
                notas=notas,
                fecha_override=fecha_tx.strftime("%Y-%m-%d"),
            )
            if ok:
                nuevo_saldo = get_current_balance()
                st.success(f"Transaction saved — ID: {new_id}")
                st.info(f"New balance: **${nuevo_saldo:,.2f}**")
            else:
                st.error(f"Error: {msg}")


# ══════════════════════════════════════════════
# TAB 2 — History
# ══════════════════════════════════════════════
with tab_history:
    hoy = date.today()
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_desde = st.date_input("From", value=hoy.replace(day=1), key="f_desde")
    with fc2:
        f_hasta = st.date_input("To", value=hoy, key="f_hasta")
    with fc3:
        tipo_f = st.selectbox("Type", ["All"] + TIPOS_TRANSACCION, key="tipo_f")

    df = get_transactions(
        fecha_desde=f_desde.strftime("%Y-%m-%d"),
        fecha_hasta=f_hasta.strftime("%Y-%m-%d"),
        tipo_filter=tipo_f if tipo_f != "All" else "",
    )

    if df.empty:
        st.info("No transactions found for the selected filters.")
    else:
        activas = df[df["Estado"].astype(str) == ESTADO_TX_ACTIVO]
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Records", len(df))
        r2.metric("Total In",  f"${activas[activas['Monto']>0]['Monto'].sum():,.2f}")
        r3.metric("Total Out", f"${activas[activas['Monto']<0]['Monto'].abs().sum():,.2f}")
        r4.metric("Voided", len(df[df["Estado"].astype(str) == ESTADO_TX_ANULADO]))

        st.divider()

        df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce")
        df["Saldo_Posterior"] = pd.to_numeric(df["Saldo_Posterior"], errors="coerce")

        cols_show = ["ID", "Fecha", "Tipo", "Categoria", "Concepto", "Monto", "Saldo_Posterior", "Usuario", "Estado"]
        cols_exist = [c for c in cols_show if c in df.columns]
        df_display = df[cols_exist].copy()
        df_display["Fecha"] = pd.to_datetime(df_display["Fecha"], errors="coerce").dt.strftime("%b %d, %Y")
        df_display["Monto"] = df_display["Monto"].apply(
            lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}" if pd.notna(x) else ""
        )
        if "Saldo_Posterior" in df_display.columns:
            df_display["Saldo_Posterior"] = df_display["Saldo_Posterior"].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) else ""
            )
        df_display = df_display.rename(columns={
            "Fecha": "Date", "Tipo": "Type", "Categoria": "Category",
            "Concepto": "Description", "Monto": "Amount",
            "Saldo_Posterior": "Balance After", "Usuario": "User", "Estado": "Status",
        })
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=420)

        csv_buf = io.StringIO()
        df[cols_exist].to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            label="Download CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"transactions_{f_desde}_{f_hasta}.csv",
            mime="text/csv",
        )


