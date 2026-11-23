import streamlit as st
import pandas as pd
from calculos_oms import (
    DATA_DIR,
    ARCHIVOS_OMS,
    calcular_puntaje_z_oms,
    clasificar_bmi_oms,
)

st.set_page_config(page_title="IMC Fácil", page_icon="📊", layout="centered")


@st.cache_data(show_spinner="Cargando tablas de referencia OMS...")
def cargar_tablas():
    tablas = {}
    faltantes = []
    for clave, nombre_archivo in ARCHIVOS_OMS.items():
        ruta = DATA_DIR / nombre_archivo
        if ruta.exists():
            tablas[clave] = pd.read_excel(ruta)
        else:
            faltantes.append(f"{clave} -> {nombre_archivo}")
    return tablas, faltantes


def clasificar_bmi_adulto(imc):
    if imc < 18.5:
        return "Bajo peso", "🔵"
    elif 18.5 <= imc < 25.0:
        return "Peso normal", "🟢"
    elif 25.0 <= imc < 30.0:
        return "Sobrepeso", "🟡"
    elif 30.0 <= imc < 35.0:
        return "Obesidad grado I", "🟠"
    elif 35.0 <= imc < 40.0:
        return "Obesidad grado II", "🔴"
    else:
        return "Obesidad grado III", "🚨"


tablas, archivos_faltantes = cargar_tablas()

# Encabezado
st.markdown("<h1 style='text-align: center; color: #1976D2; margin-bottom: 0;'>📊 IMC Fácil</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray; margin-bottom: 5px;'>Evaluación Nutricional • Estándares OMS (Niños, Adolescentes y Adultos)</p>", unsafe_allow_html=True)
st.divider()

if archivos_faltantes:
    st.warning(
        "⚠️ Faltan archivos OMS en la carpeta `data/`:\n- " + "\n- ".join(archivos_faltantes)
    )

# Selector de unidad de estatura fuera del formulario para que los campos cambien dinámicamente
unidad_talla = st.selectbox(
    "📏 Unidad de Talla / Estatura",
    ["cm (Centímetros)", "ft / in (Pies y Pulgadas)", "in (Pulgadas totales)"]
)

# Formulario de entrada
with st.form("form_imc"):
    sexo = st.selectbox("👤 Sexo", ["Masculino", "Femenino"])

    col_edad1, col_edad2 = st.columns(2)
    with col_edad1:
        edad_anios = st.number_input("📅 Edad (años)", min_value=2, max_value=120, value=5, step=1)
    with col_edad2:
        edad_meses = st.number_input("Meses adicionales", min_value=0, max_value=11, value=0, step=1)

    col_peso1, col_peso2 = st.columns([2, 1])
    with col_peso1:
        peso_val = st.number_input("⚖️ Peso", min_value=0.1, max_value=300.0, value=18.0, step=0.1, format="%.2f")
    with col_peso2:
        unidad_peso = st.selectbox("Unidad", ["kg", "lb"], key="u_peso")

    # Campos dinámicos según la unidad de estatura elegida
    if unidad_talla == "ft / in (Pies y Pulgadas)":
        col_ft, col_in = st.columns(2)
        with col_ft:
            pies = st.number_input("📏 Estatura (Pies / ft)", min_value=1, max_value=8, value=5, step=1)
        with col_in:
            pulgadas = st.number_input("Pulgadas adicionales (in)", min_value=0.0, max_value=11.9, value=6.0, step=0.5, format="%.1f")
    elif unidad_talla == "in (Pulgadas totales)":
        talla_val = st.number_input("📏 Talla / Estatura (Pulgadas totales)", min_value=12.0, max_value=100.0, value=45.0, step=0.5, format="%.1f")
    else:
        talla_val = st.number_input("📏 Talla / Estatura (cm)", min_value=30.0, max_value=250.0, value=110.0, step=0.5, format="%.1f")

    calcular = st.form_submit_button("CALCULAR IMC (OMS)", type="primary", use_container_width=True)

# Procesamiento y Resultados
if calcular:
    edad_total_meses = edad_anios * 12 + edad_meses

    if edad_total_meses < 24:
        st.error("⚠️ La edad mínima para esta calculadora es de 2 años (24 meses).")
    else:
        try:
            peso_kg = peso_val * 0.45359237 if unidad_peso == "lb" else peso_val

            # Conversión exacta de estatura a centímetros
            if unidad_talla == "ft / in (Pies y Pulgadas)":
                talla_cm = (pies * 30.48) + (pulgadas * 2.54)
            elif unidad_talla == "in (Pulgadas totales)":
                talla_cm = talla_val * 2.54
            else:
                talla_cm = talla_val

            imc = peso_kg / ((talla_cm / 100) ** 2)

            st.success("### 📋 Resultado de Evaluación")

            # Caso 1: Niños y adolescentes (2 a 19 años -> 24 a 228 meses)
            if edad_total_meses <= 228:
                z = calcular_puntaje_z_oms(imc, edad_total_meses, sexo, tablas)
                clasificacion, icono = clasificar_bmi_oms(z, edad_total_meses)

                c1, c2 = st.columns(2)
                c1.metric(label="IMC Calculado", value=f"{imc:.2f} kg/m²")
                c2.metric(label="Puntaje Z (OMS)", value=f"{z:+.2f} DE")

                st.markdown(f"**Diagnóstico:** {icono} **{clasificacion}**")
                st.caption(f"Datos estandarizados: {peso_kg:.2f} kg | {talla_cm:.1f} cm | {edad_total_meses} meses (Estándar infantil/juvenil)")

            # Caso 2: Adultos (mayores de 19 años -> más de 228 meses)
            else:
                clasificacion, icono = clasificar_bmi_adulto(imc)

                st.metric(label="IMC Calculado", value=f"{imc:.2f} kg/m²")
                st.markdown(f"**Diagnóstico:** {icono} **{clasificacion}**")
                st.caption(f"Datos estandarizados: {peso_kg:.2f} kg | {talla_cm:.1f} cm | {edad_anios} años (Estándar adultos OMS)")

        except (ValueError, KeyError) as e:
            st.error(f"⚠️ {e}")

st.divider()
st.markdown("<p style='text-align: center; color: gray; font-size: 0.85em;'>IMC Fácil v1.0 • Creado por RAFC (2026)</p>", unsafe_allow_html=True)
