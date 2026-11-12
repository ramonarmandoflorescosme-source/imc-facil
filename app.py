import streamlit as st
import pandas as pd
from calculos_oms import (
    DATA_DIR,
    ARCHIVOS_OMS,
    calcular_puntaje_z_oms,
    clasificar_bmi_oms,
)

st.set_page_config(page_title="IMC Fácil", page_icon="📊", layout="centered")

@st.cache_data
def cargar_tablas():
    tablas = {}
    for clave, nombre_archivo in ARCHIVOS_OMS.items():
        ruta = DATA_DIR / nombre_archivo
        if not ruta.exists():
            st.error(f"❌ No se encontró el archivo: `{ruta}`")
            st.stop()
        tablas[clave] = pd.read_excel(ruta)
    return tablas

tablas = cargar_tablas()

# Encabezado
st.markdown("<h1 style='text-align: center; color: #1976D2; margin-bottom: 0;'>📊 IMC Fácil</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Evaluación Nutricional • Estándares OMS (2 a 19 años)</p>", unsafe_allow_html=True)
st.divider()

# Formulario de entrada
with st.form("form_imc"):
    sexo = st.selectbox("👤 Sexo", ["Masculino", "Femenino"])

    col_edad1, col_edad2 = st.columns(2)
    with col_edad1:
        edad_anios = st.number_input("📅 Edad (años)", min_value=2, max_value=19, value=5, step=1)
    with col_edad2:
        edad_meses = st.number_input("Meses adicionales", min_value=0, max_value=11, value=0, step=1)

    col_peso1, col_peso2 = st.columns([2, 1])
    with col_peso1:
        peso_val = st.number_input("⚖️ Peso", min_value=0.1, max_value=300.0, value=18.0, step=0.1, format="%.2f")
    with col_peso2:
        unidad_peso = st.selectbox("Unidad", ["kg", "lb"], key="u_peso")

    col_talla1, col_talla2 = st.columns([2, 1])
    with col_talla1:
        talla_val = st.number_input("📏 Talla / Estatura", min_value=30.0, max_value=250.0, value=110.0, step=0.5, format="%.1f")
    with col_talla2:
        unidad_talla = st.selectbox("Unidad", ["cm", "in"], key="u_talla")

    calcular = st.form_submit_button("CALCULAR IMC (OMS)", type="primary", use_container_width=True)

# Procesamiento y Resultados
if calcular:
    edad_total_meses = edad_anios * 12 + edad_meses

    if not (24 <= edad_total_meses <= 228):
        st.error("⚠️ La edad total debe estar entre 2 años (24 meses) y 19 años (228 meses).")
    else:
        try:
            peso_kg = peso_val * 0.45359237 if unidad_peso == "lb" else peso_val
            talla_cm = talla_val * 2.54 if unidad_talla == "in" else talla_val

            imc = peso_kg / ((talla_cm / 100) ** 2)
            z = calcular_puntaje_z_oms(imc, edad_total_meses, sexo, tablas)
            clasificacion, icono = clasificar_bmi_oms(z, edad_total_meses)

            st.success("### 📋 Resultado de Evaluación")
            
            c1, c2 = st.columns(2)
            c1.metric(label="IMC Calculado", value=f"{imc:.2f} kg/m²")
            c2.metric(label="Puntaje Z (OMS)", value=f"{z:+.2f} DE")

            st.markdown(f"**Diagnóstico:** {icono} **{clasificacion}**")
            st.caption(f"Datos estandarizados: {peso_kg:.2f} kg | {talla_cm:.1f} cm | {edad_total_meses} meses")

        except ValueError as e:
            st.error(f"⚠️ {e}")

st.divider()
st.markdown("<p style='text-align: center; color: gray; font-size: 0.85em;'>IMC Fácil v1.1 • Creado por RAFC (2026)</p>", unsafe_allow_html=True)
