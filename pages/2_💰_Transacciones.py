"""
pages/2_💰_Transacciones.py — Registro, consulta y gestión de transacciones.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io

from modules.auth import require_auth, has_permission
from modules.database import (
    get_transactions, add_transaction, update_transaction,
    void_transaction, get_current_balance, get_config,
)
from modules.validators import validate_transaction, check_possible_duplicate
from modules.alerts import run_alert_checks
from config import (
    APP_NAME, TIPOS_TRANSACCION, CATEGORIAS,
    TIPO_INGRESO, TIPO_EGRESO, TIPO_REPOSICION, TIPO_AJUSTE, TIPO_TRANSFERENCIA,
    ESTADO_TX_ACTIVO, ESTADO_TX_ANULADO,
)

st.set_page_config(page_title=f"Transacciones — {APP_NAME}", page_icon="💰", layout="wide")

user = require_auth()
from app import render_sidebar_user
render_sidebar_user()

try:
    run_alert_checks()
except Exception:
    pass

cfg = get_config()
moneda = cfg.get("MONEDA", "MXN")

st.title("💰 Transacciones")

tab_nueva, tab_lista, tab_editar = st.tabs(["➕ Nueva Transacción", "📋 Historial", "✏️ Editar / Anular"])

# ══════════════════════════════════════════════
# TAB 1 — Nueva Transacción
# ══════════════════════════════════════════════
with tab_nueva:
    if not has_permission(user, "registrar_transaccion"):
        st.error("🚫 No tienes permiso para registrar transacciones.")
        st.stop()

    saldo_actual = get_current_balance()
    st.metric("Saldo Actual", f"{moneda} {saldo_actual:,.2f}")
    st.divider()

    with st.form("form_nueva_tx", clear_on_submit=True):
        st.subheader("Registrar movimiento")
        col1, col2 = st.columns(2)

        with col1:
            tipo = st.selectbox("Tipo *", TIPOS_TRANSACCION)
            categorias_tipo = CATEGORIAS.get(tipo, ["Otros"])
            categoria = st.selectbox("Categoría *", categorias_tipo)
            concepto = st.text_input(
                "Concepto / Descripción *",
                max_chars=200,
                help="Mínimo 3 caracteres. Para ajustes, sé descriptivo (mín. 10).",
            )

        with col2:
            monto_label = "Monto *"
            if tipo in (TIPO_AJUSTE, TIPO_TRANSFERENCIA):
                monto_label += " (+ positivo, − negativo)"
            monto_input = st.number_input(
                monto_label,
                min_value=-10_000_000.0,
                max_value=10_000_000.0,
                step=0.01,
                format="%.2f",
                help="Para Ajuste/Transferencia usa valores negativos para restar.",
            )
            fecha_tx = st.date_input("Fecha *", value=date.today(), max_value=date.today())
            referencia = st.text_input(
                "Referencia / No. Comprobante",
                max_chars=100,
                placeholder="Folio de ticket, factura, etc.",
            )

        notas = st.text_area("Notas adicionales", max_chars=500)
        submitted = st.form_submit_button("💾 Registrar Transacción", type="primary", use_container_width=True)

    if submitted:
        # Determinar monto_raw según tipo
        if tipo in (TIPO_INGRESO, TIPO_REPOSICION):
            monto_raw = abs(monto_input)
        elif tipo == TIPO_EGRESO:
            monto_raw = abs(monto_input)
        else:
            monto_raw = monto_input  # Ajuste/Transferencia: conservar signo

        # Validar
        errores = validate_transaction(tipo, categoria, concepto, monto_raw, fecha_tx)
        if errores:
            for err in errores:
                st.error(f"❌ {err}")
        else:
            # Verificar posible duplicado
            df_recientes = get_transactions(activas_only=True)
            ventana = int(cfg.get("VENTANA_DUPLICADO_MINUTOS", 60))
            if check_possible_duplicate(tipo, concepto, abs(monto_raw), df_recientes, ventana):
                st.warning(
                    f"⚠️ **Posible duplicado detectado**: existe una transacción similar "
                    f"en los últimos {ventana} minutos. ¿Deseas registrarla de todos modos?"
                )
                col_dup1, col_dup2 = st.columns(2)
                with col_dup1:
                    if st.button("✅ Sí, registrar de todos modos"):
                        _do_save = True
                    else:
                        _do_save = False
                with col_dup2:
                    if st.button("❌ Cancelar"):
                        _do_save = None
            else:
                _do_save = True

            if _do_save:
                ok, msg, new_id = add_transaction(
                    tipo=tipo,
                    categoria=categoria,
                    concepto=concepto,
                    monto_raw=monto_raw,
                    usuario=user["usuario"],
                    referencia=referencia,
                    notas=notas,
                    fecha_override=fecha_tx.strftime("%Y-%m-%d"),
                )
                if ok:
                    nuevo_saldo = get_current_balance()
                    st.success(f"✅ {msg}")
                    st.info(f"💰 Nuevo saldo: **{moneda} {nuevo_saldo:,.2f}**")
                    try:
                        run_alert_checks()
                    except Exception:
                        pass
                else:
                    st.error(f"❌ {msg}")


# ══════════════════════════════════════════════
# TAB 2 — Historial
# ══════════════════════════════════════════════
with tab_lista:
    st.subheader("Historial de Transacciones")

    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            hoy = date.today()
            f_desde = st.date_input("Desde", value=hoy.replace(day=1), key="f_desde")
        with fc2:
            f_hasta = st.date_input("Hasta", value=hoy, key="f_hasta")
        with fc3:
            tipo_f = st.selectbox("Tipo", ["Todos"] + TIPOS_TRANSACCION, key="tipo_f")
        with fc4:
            estado_f = st.selectbox("Estado", ["Todos", ESTADO_TX_ACTIVO, ESTADO_TX_ANULADO], key="estado_f")
        concepto_f = st.text_input("Buscar en concepto / categoría", key="concepto_f")

    df = get_transactions(
        fecha_desde=f_desde.strftime("%Y-%m-%d"),
        fecha_hasta=f_hasta.strftime("%Y-%m-%d"),
        tipo_filter=tipo_f if tipo_f != "Todos" else "",
    )

    if estado_f != "Todos":
        df = df[df["Estado"].astype(str) == estado_f]
    if concepto_f:
        mask = (
            df["Concepto"].astype(str).str.contains(concepto_f, case=False, na=False)
            | df["Categoria"].astype(str).str.contains(concepto_f, case=False, na=False)
        )
        df = df[mask]

    if df.empty:
        st.info("ℹ️ No hay transacciones con los filtros aplicados.")
    else:
        # Resumen rápido
        activas = df[df["Estado"] == ESTADO_TX_ACTIVO]
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total registros", len(df))
        r2.metric("Ingresos", f"{moneda} {activas[activas['Monto']>0]['Monto'].sum():,.2f}")
        r3.metric("Egresos", f"{moneda} {activas[activas['Monto']<0]['Monto'].abs().sum():,.2f}")
        r4.metric("Anuladas", len(df[df["Estado"] == ESTADO_TX_ANULADO]))

        st.divider()

        # Tabla
        cols_show = ["ID", "Fecha", "Hora", "Tipo", "Categoria", "Concepto", "Monto", "Saldo_Posterior", "Usuario", "Referencia", "Estado", "Notas"]
        cols_exist = [c for c in cols_show if c in df.columns]
        df_display = df[cols_exist].copy()
        df_display["Fecha"] = pd.to_datetime(df_display["Fecha"], errors="coerce").dt.strftime("%Y-%m-%d")
        df_display["Monto"] = pd.to_numeric(df_display["Monto"], errors="coerce").apply(
            lambda x: f"{x:+,.2f}" if pd.notna(x) else ""
        )
        if "Saldo_Posterior" in df_display.columns:
            df_display["Saldo_Posterior"] = pd.to_numeric(
                df_display["Saldo_Posterior"], errors="coerce"
            ).apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=400,
        )

        # Exportar CSV
        csv_buf = io.StringIO()
        df[cols_exist].to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            label="⬇️ Exportar CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"transacciones_{f_desde}_{f_hasta}.csv",
            mime="text/csv",
        )


# ══════════════════════════════════════════════
# TAB 3 — Editar / Anular
# ══════════════════════════════════════════════
with tab_editar:
    if not has_permission(user, "editar_transaccion"):
        st.error("🚫 No tienes permiso para editar transacciones.")
    else:
        st.subheader("Editar o Anular una Transacción")
        st.info("💡 Ingresa el ID de la transacción que deseas modificar.")

        tx_id_input = st.text_input("ID de Transacción", placeholder="ej. TRX-0001")

        if tx_id_input:
            df_all = get_transactions()
            match = df_all[df_all["ID"].astype(str) == tx_id_input.strip()]

            if match.empty:
                st.error(f"No se encontró la transacción con ID '{tx_id_input}'.")
            else:
                tx = match.iloc[0].to_dict()
                anulada = str(tx.get("Estado", "")) == ESTADO_TX_ANULADO

                st.write("**Transacción encontrada:**")
                info_cols = st.columns(4)
                info_cols[0].markdown(f"**Tipo:** {tx.get('Tipo')}")
                info_cols[1].markdown(f"**Monto:** {moneda} {float(tx.get('Monto', 0)):,.2f}")
                info_cols[2].markdown(f"**Fecha:** {tx.get('Fecha')}")
                info_cols[3].markdown(f"**Estado:** {tx.get('Estado')}")
                st.markdown(f"**Concepto:** {tx.get('Concepto')}")

                if anulada:
                    st.warning("⚠️ Esta transacción ya está anulada y no puede modificarse.")
                else:
                    st.divider()
                    edit_tab, void_tab = st.tabs(["✏️ Editar", "🗑️ Anular"])

                    with edit_tab:
                        with st.form("form_edit_tx"):
                            tipo_e = st.selectbox(
                                "Tipo", TIPOS_TRANSACCION,
                                index=TIPOS_TRANSACCION.index(tx.get("Tipo", TIPO_EGRESO))
                                if tx.get("Tipo") in TIPOS_TRANSACCION else 0,
                            )
                            cats_e = CATEGORIAS.get(tipo_e, ["Otros"])
                            cat_e = st.selectbox(
                                "Categoría",
                                cats_e,
                                index=cats_e.index(tx.get("Categoria")) if tx.get("Categoria") in cats_e else 0,
                            )
                            concepto_e = st.text_input("Concepto", value=str(tx.get("Concepto", "")))
                            monto_e = st.number_input(
                                "Monto",
                                value=float(tx.get("Monto", 0) or 0),
                                step=0.01, format="%.2f",
                            )
                            ref_e = st.text_input("Referencia", value=str(tx.get("Referencia", "")))
                            notas_e = st.text_area("Notas", value=str(tx.get("Notas", "")))
                            save_edit = st.form_submit_button("💾 Guardar Cambios", type="primary")

                        if save_edit:
                            errores_e = validate_transaction(tipo_e, cat_e, concepto_e, abs(monto_e), date.today())
                            if errores_e:
                                for err in errores_e:
                                    st.error(f"❌ {err}")
                            else:
                                changes = {
                                    "Tipo": tipo_e,
                                    "Categoria": cat_e,
                                    "Concepto": concepto_e,
                                    "Monto": monto_e,
                                    "Referencia": ref_e,
                                    "Notas": notas_e,
                                }
                                ok, msg = update_transaction(tx_id_input.strip(), changes, user["usuario"])
                                if ok:
                                    st.success(f"✅ {msg}")
                                else:
                                    st.error(f"❌ {msg}")

                    with void_tab:
                        if not has_permission(user, "anular_transaccion"):
                            st.error("🚫 No tienes permiso para anular transacciones.")
                        else:
                            st.warning(
                                f"⚠️ Vas a **anular** la transacción **{tx_id_input}**. "
                                "Esta acción queda registrada en la bitácora."
                            )
                            motivo = st.text_area("Motivo de anulación *", height=100)
                            if st.button("🗑️ Confirmar Anulación", type="primary"):
                                if not motivo.strip() or len(motivo.strip()) < 10:
                                    st.error("El motivo debe tener al menos 10 caracteres.")
                                else:
                                    ok, msg = void_transaction(tx_id_input.strip(), motivo, user["usuario"])
                                    if ok:
                                        st.success(f"✅ {msg}")
                                    else:
                                        st.error(f"❌ {msg}")
