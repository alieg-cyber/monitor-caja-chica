"""
pages/3_🔄_Conciliacion.py — Cierres de periodo y conciliación de saldos.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io

from modules.auth import require_auth, has_permission
from modules.database import (
    get_closures, create_closure, get_transactions,
    get_current_balance, get_config,
)
from modules.validators import validate_closure_dates
from config import (
    APP_NAME, ESTADO_CIERRE_CONCILIADO, ESTADO_CIERRE_CON_DIFERENCIA,
    ESTADO_CIERRE_PENDIENTE,
)

st.set_page_config(page_title=f"Conciliación — {APP_NAME}", page_icon="🔄", layout="wide")

user = require_auth()
from app import render_sidebar_user
render_sidebar_user()

cfg = get_config()
moneda = cfg.get("MONEDA", "MXN")

st.title("🔄 Conciliación y Cierres")

tab_nuevo, tab_hist = st.tabs(["📝 Nuevo Cierre", "📚 Historial de Cierres"])

# ══════════════════════════════════════════════
# TAB 1 — Nuevo Cierre
# ══════════════════════════════════════════════
with tab_nuevo:
    if not has_permission(user, "hacer_conciliacion"):
        st.error("🚫 No tienes permiso para crear cierres.")
        st.stop()

    st.subheader("Crear Cierre de Periodo")
    st.info(
        "El sistema calculará automáticamente: ingresos, egresos, saldo esperado. "
        "Tú ingresas el **saldo real** contado físicamente."
    )

    today = date.today()
    col1, col2 = st.columns(2)
    with col1:
        periodo_inicio = st.date_input(
            "Inicio del periodo *",
            value=today.replace(day=1),
            max_value=today,
        )
    with col2:
        periodo_fin = st.date_input(
            "Fin del periodo *",
            value=today,
            max_value=today,
        )

    # Vista previa del periodo
    if periodo_inicio and periodo_fin and periodo_inicio <= periodo_fin:
        df_periodo = get_transactions(
            activas_only=True,
            fecha_desde=periodo_inicio.strftime("%Y-%m-%d"),
            fecha_hasta=periodo_fin.strftime("%Y-%m-%d"),
        )

        st.divider()
        st.subheader("📊 Resumen del Periodo")

        if df_periodo.empty:
            st.warning("No hay transacciones activas en el periodo seleccionado.")
            total_ing = total_egr = num_tx = 0.0
        else:
            df_periodo["Monto"] = pd.to_numeric(df_periodo["Monto"], errors="coerce").fillna(0)
            total_ing = float(df_periodo[df_periodo["Monto"] > 0]["Monto"].sum())
            total_egr = float(df_periodo[df_periodo["Monto"] < 0]["Monto"].abs().sum())
            num_tx = len(df_periodo)

        # Saldo previo al periodo
        all_tx = get_transactions(activas_only=True)
        if not all_tx.empty:
            all_tx["Fecha"] = pd.to_datetime(all_tx["Fecha"], errors="coerce")
            previas = all_tx[all_tx["Fecha"] < pd.to_datetime(periodo_inicio.strftime("%Y-%m-%d"))]
            if previas.empty:
                saldo_inicial = 0.0
            else:
                previas = previas.sort_values("Timestamp_Creacion")
                saldo_inicial = float(previas.iloc[-1].get("Saldo_Posterior", 0) or 0)
        else:
            saldo_inicial = 0.0

        saldo_esperado = saldo_inicial + total_ing - total_egr

        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("Saldo Inicial", f"{moneda} {saldo_inicial:,.2f}")
        p2.metric("Total Ingresos", f"{moneda} {total_ing:,.2f}")
        p3.metric("Total Egresos", f"{moneda} {total_egr:,.2f}")
        p4.metric("Saldo Esperado", f"{moneda} {saldo_esperado:,.2f}")
        p5.metric("No. Transacciones", num_tx)

        st.divider()

        with st.form("form_cierre"):
            saldo_real = st.number_input(
                f"Saldo Real Contado ({moneda}) *",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                help="Ingresa el monto exacto que tienes físicamente en caja.",
            )
            diferencia_preview = saldo_real - saldo_esperado
            if saldo_real != 0:
                color = "green" if abs(diferencia_preview) < 0.01 else "red"
                st.markdown(
                    f"**Diferencia calculada:** "
                    f"<span style='color:{color}'>{moneda} {diferencia_preview:+,.2f}</span>",
                    unsafe_allow_html=True,
                )
            notas_cierre = st.text_area("Notas / Observaciones", max_chars=500)
            cerrar = st.form_submit_button("🔒 Crear Cierre", type="primary", use_container_width=True)

        if cerrar:
            errores = validate_closure_dates(
                periodo_inicio.strftime("%Y-%m-%d"),
                periodo_fin.strftime("%Y-%m-%d"),
            )
            if errores:
                for e in errores:
                    st.error(f"❌ {e}")
            elif saldo_real < 0:
                st.error("❌ El saldo real no puede ser negativo.")
            else:
                ok, msg, resumen = create_closure(
                    periodo_inicio=periodo_inicio.strftime("%Y-%m-%d"),
                    periodo_fin=periodo_fin.strftime("%Y-%m-%d"),
                    saldo_real=saldo_real,
                    responsable=user["usuario"],
                    notas=notas_cierre,
                )
                if ok:
                    st.success(f"✅ {msg}")
                    dif = resumen["diferencia"]
                    if abs(dif) < 0.01:
                        st.balloons()
                        st.info("🎉 ¡Caja cuadrada! No hay diferencia.")
                    else:
                        st.warning(
                            f"⚠️ Diferencia de **{moneda} {dif:+,.2f}**. "
                            "Revisa los movimientos del periodo."
                        )
                else:
                    st.error(f"❌ {msg}")


# ══════════════════════════════════════════════
# TAB 2 — Historial de Cierres
# ══════════════════════════════════════════════
with tab_hist:
    if not has_permission(user, "ver_conciliacion"):
        st.error("🚫 No tienes permiso para ver los cierres.")
        st.stop()

    st.subheader("Historial de Cierres")

    df_cierres = get_closures()
    if df_cierres.empty:
        st.info("ℹ️ No hay cierres registrados.")
    else:
        # Resumen de cierres
        total_cierres = len(df_cierres)
        conciliados = len(df_cierres[df_cierres["Estado"] == ESTADO_CIERRE_CONCILIADO])
        con_dif = len(df_cierres[df_cierres["Estado"] == ESTADO_CIERRE_CON_DIFERENCIA])

        cs1, cs2, cs3 = st.columns(3)
        cs1.metric("Total Cierres", total_cierres)
        cs2.metric("✅ Conciliados", conciliados)
        cs3.metric("⚠️ Con Diferencia", con_dif)
        st.divider()

        # Tabla
        cols_show = [
            "ID", "Fecha_Cierre", "Periodo_Inicio", "Periodo_Fin",
            "Saldo_Inicial", "Total_Ingresos", "Total_Egresos",
            "Saldo_Esperado", "Saldo_Real", "Diferencia",
            "Num_Transacciones", "Estado", "Responsable",
        ]
        cols_ex = [c for c in cols_show if c in df_cierres.columns]
        df_disp = df_cierres[cols_ex].copy()

        for col_num in ["Saldo_Inicial", "Total_Ingresos", "Total_Egresos", "Saldo_Esperado", "Saldo_Real", "Diferencia"]:
            if col_num in df_disp.columns:
                df_disp[col_num] = pd.to_numeric(df_disp[col_num], errors="coerce").apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) else ""
                )

        st.dataframe(
            df_disp,
            use_container_width=True,
            hide_index=True,
            height=400,
        )

        # Detalle de cierre seleccionado
        st.divider()
        st.subheader("Detalle de Cierre")
        ids = df_cierres["ID"].astype(str).tolist()
        cierre_sel = st.selectbox("Selecciona un cierre", ids)
        if cierre_sel:
            c_row = df_cierres[df_cierres["ID"].astype(str) == cierre_sel].iloc[0]
            with st.expander("📄 Ver detalle completo", expanded=True):
                d1, d2, d3 = st.columns(3)
                d1.markdown(f"**Periodo:** {c_row.get('Periodo_Inicio')} → {c_row.get('Periodo_Fin')}")
                d2.markdown(f"**Estado:** {c_row.get('Estado')}")
                d3.markdown(f"**Responsable:** {c_row.get('Responsable')}")

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Saldo Inicial", f"{moneda} {float(c_row.get('Saldo_Inicial', 0) or 0):,.2f}")
                m2.metric("Ingresos", f"{moneda} {float(c_row.get('Total_Ingresos', 0) or 0):,.2f}")
                m3.metric("Egresos", f"{moneda} {float(c_row.get('Total_Egresos', 0) or 0):,.2f}")
                m4.metric("Esperado", f"{moneda} {float(c_row.get('Saldo_Esperado', 0) or 0):,.2f}")
                dif_val = float(c_row.get("Diferencia", 0) or 0)
                m5.metric("Diferencia", f"{moneda} {dif_val:+,.2f}", delta_color="inverse" if abs(dif_val) > 0 else "normal")

                if c_row.get("Notas"):
                    st.info(f"📝 Notas: {c_row.get('Notas')}")

        # Exportar
        csv_buf = io.StringIO()
        df_cierres[cols_ex].to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ Exportar Cierres CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name="cierres.csv",
            mime="text/csv",
        )
