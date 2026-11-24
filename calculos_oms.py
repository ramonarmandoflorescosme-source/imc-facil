
from pathlib import Path
import numpy as np
import pandas as pd

# Carpeta principal del proyecto
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Archivos originales de referencia de la OMS
ARCHIVOS_OMS = {
    "Masculino_2_5": "bmi_boys_2-to-5-years_zscores.xlsx",
    "Femenino_2_5": "bmi_girls_2-to-5-years_zscores.xlsx",
    "Masculino_5_19": "bmi-boys-z-who-2007-exp.xlsx",
    "Femenino_5_19": "bmi-girls-z-who-2007-exp.xlsx",
}


def _normalizar_columnas(df):
    """Normaliza los nombres de las columnas."""
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "").replace("_", "")
        for col in df.columns
    ]
    return df


def _obtener_columna(df, nombre):
    """Busca una columna aunque cambie el uso de mayúsculas."""
    nombre = nombre.lower().replace(" ", "").replace("_", "")
    if nombre not in df.columns:
        raise ValueError(
            f"La tabla OMS no contiene la columna necesaria: {nombre}"
        )
    return nombre


def obtener_lms(tabla, edad_meses):
    """
    Obtiene L, M y S para la edad indicada.
    Si la edad está entre dos meses, interpola los valores.
    """
    if tabla is None or tabla.empty:
        raise ValueError("La tabla OMS está vacía.")

    df = _normalizar_columnas(tabla)

    col_mes = _obtener_columna(df, "Month")
    col_l = _obtener_columna(df, "L")
    col_m = _obtener_columna(df, "M")
    col_s = _obtener_columna(df, "S")

    for columna in (col_mes, col_l, col_m, col_s):
        df[columna] = pd.to_numeric(df[columna], errors="coerce")

    df = df.dropna(subset=[col_mes, col_l, col_m, col_s])
    df = df.sort_values(col_mes)

    if df.empty:
        raise ValueError("No hay datos LMS válidos en la tabla OMS.")

    meses = df[col_mes].to_numpy(dtype=float)

    if edad_meses < meses.min() or edad_meses > meses.max():
        raise ValueError(
            f"La edad de {edad_meses} meses está fuera del rango "
            f"de esta tabla ({meses.min():g} a {meses.max():g})."
        )

    L = float(np.interp(edad_meses, meses, df[col_l]))
    M = float(np.interp(edad_meses, meses, df[col_m]))
    S = float(np.interp(edad_meses, meses, df[col_s]))

    if M <= 0 or S <= 0:
        raise ValueError("Los parámetros OMS M y S no son válidos.")

    return L, M, S


def calcular_puntaje_z_bmi(imc, edad_meses, sexo, tablas):
    """Calcula el puntaje Z mediante el método LMS de la OMS."""
    return calcular_puntaje_z_oms(imc, edad_meses, sexo, tablas)


def calcular_puntaje_z_oms(imc, edad_meses, sexo, tablas):
    if imc <= 0:
        raise ValueError("El IMC debe ser mayor que cero.")

    if edad_meses < 24 or edad_meses > 228:
        raise ValueError("La edad debe estar entre 24 y 228 meses.")

    sexo = str(sexo).strip().lower()

    if sexo in ("masculino", "hombre", "niño", "nino"):
        prefijo = "Masculino"
    elif sexo in ("femenino", "mujer", "niña", "nina"):
        prefijo = "Femenino"
    else:
        raise ValueError("Selecciona un sexo válido.")

    if edad_meses <= 60:
        clave = f"{prefijo}_2_5"
    else:
        clave = f"{prefijo}_5_19"

    if clave not in tablas:
        raise ValueError(f"No se encontró la tabla OMS: {clave}")

    L, M, S = obtener_lms(tablas[clave], edad_meses)

    if abs(L) < 1e-10:
        z = np.log(imc / M) / S
    else:
        z = ((imc / M) ** L - 1) / (L * S)

    if not np.isfinite(z):
        raise ValueError("No se pudo calcular un puntaje Z válido.")

    return float(z)


def clasificar_bmi_oms(z, edad_meses):
    """Clasifica el IMC infantil según los puntos de corte OMS."""

    if edad_meses < 24 or edad_meses > 228:
        raise ValueError("La clasificación infantil requiere 24 a 228 meses.")

    # Niños menores de 5 años
    if edad_meses <= 60:
        if z < -3:
            return "Delgadez severa", "🔵"
        elif z < -2:
            return "Delgadez", "🟡"
        elif z <= 1:
            return "Peso adecuado", "🟢"
        elif z <= 2:
            return "Riesgo de sobrepeso", "🟡"
        elif z <= 3:
            return "Sobrepeso", "🟠"
        else:
            return "Obesidad", "🔴"

    # Niños y adolescentes de 5 a 19 años
    else:
        if z < -3:
            return "Delgadez severa", "🔵"
        elif z < -2:
            return "Delgadez", "🟡"
        elif z <= 1:
            return "Peso adecuado", "🟢"
        elif z <= 2:
            return "Sobrepeso", "🟠"
        else:
            return "Obesidad", "🔴"
