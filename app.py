
import pandas as pd
import streamlit as st

from calculos_oms import (
    ARCHIVOS_OMS,
    DATA_DIR,
    calcular_puntaje_z_oms,
    clasificar_bmi_oms,
)

st.set_page_config(
    page_title="IMC Fácil",
    page_icon="📊",
    layout="centered"
)


@st.cache_data(show_spinner="Cargando tablas de referencia OMS...")
def cargar_tablas():
    tablas = {}
    problemas = []

    for clave, nombre_archivo in ARCHIVOS_OMS.items():
        ruta = DATA_DIR / nombre_archivo

        if not ruta.is_file():
            problemas.append(f"No se encontró: {nombre_archivo}")
            continue

        try:
            tablas[clave] = pd.read_excel(
                ruta,
                engine="openpyxl"
            )
        except Exception as exc:
            problemas.append(
                f"Error leyendo {nombre_archivo}: {exc}"
            )

    return tablas, problemas


def clasificar_bmi_adulto(imc):
    if imc < 18.5:
        return "Bajo peso", "🔵"
    elif imc < 25:
        return "Peso normal", "🟢"
    elif imc < 30:
        return "Sobrepeso", "🟡"
    elif imc < 35:
        return "Obesidad grado I", "🟠"
    elif imc < 40:
        return "Obesidad grado II", "🔴"
    else:
        return "Obesidad grado III", "🚨"


# Cargar las tablas
tablas, problemas_archivos = cargar_tablas()


# Encabezado
st.markdown(
    """
    <h1 style="text-align:center; color:#1976D2;">
        📊 IMC Fácil
    </h1>
    <p style="text-align:center; color:gray;">
        Evaluación Nutricional • Estándares OMS
    </p>
    """,
    unsafe_allow_html=True
)

st.divider()


if problemas_archivos:
    st.error("Hay problemas con los archivos OMS:")
    for problema in problemas_archivos:
        st.write("- " + problema)


# Unidad de estatura
unidad_talla = st.selectbox(
    "📏 Unidad de Talla / Estatura",
    [
        "cm (Centímetros)",
        "ft / in (Pies y Pulgadas)",
        "in (Pulgadas totales)"
    ]
)


# Formulario
with st.form("form_imc"):

    sexo = st.selectbox(
        "👤 Sexo",
        ["Masculino", "Femenino"]
    )

    col_edad1, col_edad2 = st.columns(2)

    with col_edad1:
        edad_anios = st.number_input(
            "📅 Edad (años)",
            min_value=2,
            max_value=120,
            value=5,
            step=1
        )

    with col_edad2:
        edad_meses = st.number_input(
            "Meses adicionales",
            min_value=0,
            max_value=11,
            value=0,
            step=1
        )

    col_peso1, col_peso2 = st.columns([2, 1])

    with col_peso1:
        peso_val = st.number_input(
            "⚖️ Peso",
            min_value=0.1,
            max_value=300.0,
            value=18.0,
            step=0.1,
            format="%.2f"
        )

    with col_peso2:
        unidad_peso = st.selectbox(
            "Unidad",
            ["kg", "lb"]
        )

    if unidad_talla == "ft / in (Pies y Pulgadas)":

        col_ft, col_in = st.columns(2)

        with col_ft:
            pies = st.number_input(
                "Estatura (Pies / ft)",
                min_value=1,
                max_value=8,
                value=5,
                step=1
            )

        with col_in:
            pulgadas = st.number_input(
                "Pulgadas adicionales",
                min_value=0.0,
                max_value=11.9,
                value=6.0,
                step=0.5
            )

    elif unidad_talla == "in (Pulgadas totales)":

        talla_val = st.number_input(
            "📏 Talla / Estatura (Pulgadas)",
            min_value=12.0,
            max_value=100.0,
            value=45.0,
            step=0.5
        )

    else:

        talla_val = st.number_input(
            "📏 Talla / Estatura (cm)",
            min_value=30.0,
            max_value=250.0,
            value=110.0,
            step=0.5
        )

    calcular = st.form_submit_button(
        "CALCULAR IMC (OMS)",
        type="primary",
        use_container_width=True
    )


# Cálculo
if calcular:

    edad_total_meses = edad_anios * 12 + edad_meses

    try:

        if edad_total_meses < 24:
            raise ValueError(
                "La edad mínima es de 2 años (24 meses)."
            )

        peso_kg = (
            peso_val * 0.45359237
            if unidad_peso == "lb"
            else peso_val
        )

        if unidad_talla == "ft / in (Pies y Pulgadas)":
            talla_cm = (
                pies * 30.48
                + pulgadas * 2.54
            )

        elif unidad_talla == "in (Pulgadas totales)":
            talla_cm = talla_val * 2.54

        else:
            talla_cm = talla_val

        if talla_cm <= 0 or peso_kg <= 0:
            raise ValueError(
                "El peso y la estatura deben ser mayores que cero."
            )

        imc = peso_kg / ((talla_cm / 100) ** 2)

        st.success("### 📋 Resultado de Evaluación")

        if edad_total_meses <= 228:

            z = calcular_puntaje_z_oms(
                imc,
                edad_total_meses,
                sexo,
                tablas
            )

            clasificacion, icono = clasificar_bmi_oms(
                z,
                edad_total_meses
            )

            col1, col2 = st.columns(2)

            col1.metric(
                "IMC Calculado",
                f"{imc:.2f} kg/m²"
            )

            col2.metric(
                "Puntaje Z (OMS)",
                f"{z:+.2f} DE"
            )

            st.markdown(
                f"**Diagnóstico:** {icono} **{clasificacion}**"
            )

            st.caption(
                f"Peso: {peso_kg:.2f} kg | "
                f"Estatura: {talla_cm:.1f} cm | "
                f"Edad: {edad_total_meses} meses"
            )

        else:

            clasificacion, icono = clasificar_bmi_adulto(imc)

            st.metric(
                "IMC Calculado",
                f"{imc:.2f} kg/m²"
            )

            st.markdown(
                f"**Diagnóstico:** {icono} **{clasificacion}**"
            )

            st.caption(
                f"Peso: {peso_kg:.2f} kg | "
                f"Estatura: {talla_cm:.1f} cm | "
                f"Edad: {edad_anios} años"
            )

    except Exception as error:
        st.error(f"⚠️ No se pudo completar el cálculo: {error}")


st.divider()

st.markdown(
    """
    <p style="text-align:center; color:gray; font-size:0.85em;">
        IMC Fácil v1.0 • Creado por RAFC (2026)
    </p>
    """,
    unsafe_allow_html=True
)
