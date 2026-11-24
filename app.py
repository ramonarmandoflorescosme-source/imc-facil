
from pathlib import Path
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape
import textwrap

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from PIL import Image, ImageDraw, ImageFont

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from calculos_oms import (
    ARCHIVOS_OMS,
    resolver_archivo_oms,
    calcular_puntaje_z_oms,
    clasificar_bmi_oms,
)


st.set_page_config(
    page_title="IMC Fácil",
    page_icon="📊",
    layout="centered"
)


AVISO_SALUD = (
    "Los resultados proporcionados por IMC Fácil son orientativos "
    "y tienen fines informativos y educativos. No constituyen un "
    "diagnóstico médico ni sustituyen la evaluación de un profesional "
    "de la salud. Si tienes dudas sobre tu peso, crecimiento o estado "
    "nutricional, consulta con un profesional sanitario."
)


@st.cache_data(show_spinner="Cargando tablas de referencia OMS...")
def cargar_tablas():
    tablas = {}
    problemas = []

    for clave, nombre_archivo in ARCHIVOS_OMS.items():

        ruta = resolver_archivo_oms(nombre_archivo)

        if ruta is None:
            problemas.append(
                f"No se encontró: {nombre_archivo}"
            )
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


def crear_pdf(datos):

    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloIMC",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1976D2"),
        fontSize=23,
        spaceAfter=8
    )

    subtitulo = ParagraphStyle(
        "SubtituloIMC",
        parent=estilos["Normal"],
        alignment=TA_CENTER,
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=20
    )

    aviso = ParagraphStyle(
        "AvisoIMC",
        parent=estilos["Normal"],
        fontSize=9,
        leading=14
    )

    contenido = [
        Paragraph("IMC Fácil", titulo),
        Paragraph(
            "Evaluación nutricional orientativa",
            subtitulo
        ),
        Paragraph("<b>RESULTADO DE EVALUACIÓN</b>", estilos["Heading2"]),
        Spacer(1, 10)
    ]

    filas = [
        ["Dato", "Resultado"],
        ["IMC calculado", f"{datos['imc']:.2f} kg/m²"],
        ["Clasificación", datos["clasificacion"]],
        ["Edad", datos["edad"]],
        ["Sexo", datos["sexo"]],
        ["Peso", f"{datos['peso']:.2f} kg"],
        ["Estatura", f"{datos['estatura']:.1f} cm"],
        ["Fecha", datos["fecha"]],
    ]

    if datos["z"] is not None:
        filas.insert(
            3,
            ["Puntaje Z (OMS)", f"{datos['z']:+.2f} DE"]
        )

    tabla = Table(
        filas,
        colWidths=[180, 290]
    )

    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#1976D2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1),
             colors.HexColor("#F3F7FB")),
            ("PADDING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )

    contenido.append(tabla)
    contenido.append(Spacer(1, 25))
    contenido.append(
        Paragraph("Aviso importante sobre la salud", estilos["Heading3"])
    )
    contenido.append(
        Paragraph(escape(AVISO_SALUD), aviso)
    )
    contenido.append(Spacer(1, 25))
    contenido.append(
        Paragraph(
            "IMC Fácil v1.0 • Creado por RAFC",
            subtitulo
        )
    )

    documento.build(contenido)

    buffer.seek(0)
    return buffer.getvalue()


def crear_png(datos):

    ancho = 1200
    margen = 75

    try:
        fuente_path = (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )
        fuente = ImageFont.truetype(fuente_path, 32)
        fuente_titulo = ImageFont.truetype(fuente_path, 58)
        fuente_pequena = ImageFont.truetype(fuente_path, 25)
    except OSError:
        fuente = ImageFont.load_default()
        fuente_titulo = ImageFont.load_default()
        fuente_pequena = ImageFont.load_default()

    lineas = [
        f"IMC: {datos['imc']:.2f} kg/m2",
        f"Clasificacion: {datos['clasificacion']}",
    ]

    if datos["z"] is not None:
        lineas.append(
            f"Puntaje Z OMS: {datos['z']:+.2f} DE"
        )

    lineas.extend([
        f"Edad: {datos['edad']}",
        f"Sexo: {datos['sexo']}",
        f"Peso: {datos['peso']:.2f} kg",
        f"Estatura: {datos['estatura']:.1f} cm",
        f"Fecha: {datos['fecha']}",
    ])

    aviso_lineas = textwrap.wrap(
        AVISO_SALUD,
        width=75
    )

    alto = 250 + len(lineas) * 65 + len(aviso_lineas) * 40 + 180

    imagen = Image.new(
        "RGB",
        (ancho, alto),
        "white"
    )

    dibujo = ImageDraw.Draw(imagen)

    dibujo.rounded_rectangle(
        (25, 25, ancho - 25, alto - 25),
        radius=30,
        outline="#1976D2",
        width=6
    )

    y = 75

    dibujo.text(
        (margen, y),
        "IMC Facil",
        fill="#1976D2",
        font=fuente_titulo
    )

    y += 100

    dibujo.text(
        (margen, y),
        "RESULTADO DE EVALUACION",
        fill="#444444",
        font=fuente
    )

    y += 85

    for linea in lineas:
        dibujo.text(
            (margen, y),
            linea,
            fill="#222222",
            font=fuente
        )
        y += 65

    y += 25

    dibujo.text(
        (margen, y),
        "Aviso importante sobre la salud",
        fill="#1976D2",
        font=fuente
    )

    y += 55

    for linea in aviso_lineas:
        dibujo.text(
            (margen, y),
            linea,
            fill="#444444",
            font=fuente_pequena
        )
        y += 40

    y += 45

    dibujo.text(
        (margen, y),
        "IMC Facil v1.0 - Creado por RAFC",
        fill="#777777",
        font=fuente_pequena
    )

    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def mostrar_opcion_imprimir(datos):

    z_html = ""

    if datos["z"] is not None:
        z_html = (
            f"<p><b>Puntaje Z (OMS):</b> "
            f"{datos['z']:+.2f} DE</p>"
        )

    aviso_html = escape(AVISO_SALUD)

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            color: #222;
        }}
        .reporte {{
            border: 2px solid #1976D2;
            border-radius: 12px;
            padding: 25px;
            background: white;
        }}
        h1 {{
            color: #1976D2;
            text-align: center;
        }}
        .aviso {{
            font-size: 13px;
            line-height: 1.5;
            margin-top: 25px;
        }}
        button {{
            background: #1976D2;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-bottom: 15px;
        }}
        @media print {{
            button {{ display: none; }}
            body {{ padding: 0; }}
        }}
    </style>
    </head>
    <body>
        <button onclick="window.print()">IMPRIMIR RESULTADO</button>
        <div class="reporte">
            <h1>IMC Fácil</h1>
            <h3>Resultado de evaluación</h3>
            <p><b>IMC:</b> {datos['imc']:.2f} kg/m²</p>
            {z_html}
            <p><b>Clasificación:</b> {escape(datos['clasificacion'])}</p>
            <p><b>Edad:</b> {escape(datos['edad'])}</p>
            <p><b>Sexo:</b> {escape(datos['sexo'])}</p>
            <p><b>Peso:</b> {datos['peso']:.2f} kg</p>
            <p><b>Estatura:</b> {datos['estatura']:.1f} cm</p>
            <p><b>Fecha:</b> {escape(datos['fecha'])}</p>
            <div class="aviso">
                <h3>Aviso importante sobre la salud</h3>
                {aviso_html}
            </div>
            <p>IMC Fácil v1.0 • Creado por RAFC</p>
        </div>
    </body>
    </html>
    """

    components.html(
        html,
        height=570,
        scrolling=True
    )


# Cargar referencias OMS
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


# Mostrar problemas de archivos
if problemas_archivos:

    st.error("Problemas con los archivos OMS:")

    for problema in problemas_archivos:
        st.write("- " + problema)

else:

    st.success("¡Tablas OMS cargadas correctamente!")


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
            value=None,
            step=1
        )

    with col_edad2:
        edad_meses = st.number_input(
            "Meses adicionales",
            min_value=0,
            max_value=11,
            value=None,
            step=1
        )

    col_peso1, col_peso2 = st.columns([2, 1])

    with col_peso1:
        peso_val = st.number_input(
            "⚖️ Peso",
            min_value=0.1,
            max_value=300.0,
            value=None,
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
                value=None,
                step=1
            )

        with col_in:
            pulgadas = st.number_input(
                "Pulgadas adicionales",
                min_value=0.0,
                max_value=11.9,
                value=None,
                step=0.5
            )

    elif unidad_talla == "in (Pulgadas totales)":

        talla_val = st.number_input(
            "📏 Talla / Estatura (Pulgadas)",
            min_value=12.0,
            max_value=100.0,
            value=None,
            step=0.5
        )

    else:

        talla_val = st.number_input(
            "📏 Talla / Estatura (cm)",
            min_value=30.0,
            max_value=250.0,
            value=None,
            step=0.5
        )

    calcular = st.form_submit_button(
        "CALCULAR IMC (OMS)",
        type="primary",
        use_container_width=True
    )


# Realizar cálculo
if calcular:

    try:

        if (
            edad_anios is None
            or edad_meses is None
            or peso_val is None
        ):
            raise ValueError(
                "Completa la edad, los meses adicionales y el peso."
            )

        if unidad_talla == "ft / in (Pies y Pulgadas)":

            if pies is None or pulgadas is None:
                raise ValueError(
                    "Completa los pies y las pulgadas."
                )

        elif talla_val is None:
            raise ValueError(
                "Completa la estatura."
            )

        edad_total_meses = edad_anios * 12 + edad_meses

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

        if peso_kg <= 0 or talla_cm <= 0:
            raise ValueError(
                "El peso y la estatura deben ser mayores que cero."
            )

        imc = peso_kg / ((talla_cm / 100) ** 2)

        z = None

        if edad_total_meses <= 228:

            if problemas_archivos:
                raise ValueError(
                    "No se pudieron cargar todas las tablas OMS."
                )

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

        else:

            clasificacion, icono = clasificar_bmi_adulto(imc)

        fecha = datetime.now().strftime("%d/%m/%Y")

        edad_texto = (
            f"{edad_anios} años y {edad_meses} meses"
        )

        datos_resultado = {
            "imc": imc,
            "z": z,
            "clasificacion": clasificacion,
            "edad": edad_texto,
            "sexo": sexo,
            "peso": peso_kg,
            "estatura": talla_cm,
            "fecha": fecha,
        }

        st.success("### 📋 Resultado de Evaluación")

        col1, col2 = st.columns(2)

        col1.metric(
            "IMC Calculado",
            f"{imc:.2f} kg/m²"
        )

        if z is not None:
            col2.metric(
                "Puntaje Z (OMS)",
                f"{z:+.2f} DE"
            )

        st.markdown(
            f"**Clasificación orientativa:** "
            f"{icono} **{clasificacion}**"
        )

        st.caption(
            f"Peso: {peso_kg:.2f} kg | "
            f"Estatura: {talla_cm:.1f} cm | "
            f"Edad: {edad_texto} | Sexo: {sexo}"
        )

        st.divider()

        st.subheader("Guardar o imprimir resultado")

        st.download_button(
            "📄 DESCARGAR RESULTADO EN PDF",
            data=crear_pdf(datos_resultado),
            file_name="resultado_imc_facil.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        st.download_button(
            "🖼️ DESCARGAR RESULTADO EN PNG",
            data=crear_png(datos_resultado),
            file_name="resultado_imc_facil.png",
            mime="image/png",
            use_container_width=True
        )

        st.subheader("Imprimir resultado")
        mostrar_opcion_imprimir(datos_resultado)

        st.info(
            "Aviso importante sobre la salud\n\n" + AVISO_SALUD
        )

    except Exception as error:

        st.error(
            f"⚠️ No se pudo completar el cálculo: {error}"
        )


st.divider()

st.markdown(
    """
    <p style="text-align:center; color:gray; font-size:0.85em;">
        IMC Fácil v1.0 • Creado por RAFC (2026)
    </p>
    """,
    unsafe_allow_html=True
)
