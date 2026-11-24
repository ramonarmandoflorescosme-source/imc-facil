
from pathlib import Path
import numpy as np
import pandas as pd

# Carpeta principal del proyecto
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Archivos de referencia OMS
ARCHIVOS_OMS = {
    "Masculino_2_5": "bmi_boys_2-to-5-years_zscores.xlsx",
    "Femenino_2_5": "bmi_girls_2-to-5-years_zscores.xlsx",
    "Masculino_5_19": "bmi-boys-z-who-2007-exp.xlsx",
    "Femenino_5_19": "bmi-girls-z-who-2007-exp.xlsx",
}


def resolver_archivo_oms(nombre_archivo):
    """
    Busca un Excel por nombre dentro del proyecto,
    incluyendo subcarpetas y respetando mayúsculas.
    """

    carpetas = [
        BASE_DIR / "data",
        BASE_DIR,
    ]

    for carpeta in carpetas:
        if not carpeta.exists():
            continue

        for archivo in carpeta.rglob("*"):
            if (
                archivo.is_file()
                and archivo.name.lower() == nombre_archivo.lower()
            ):
                return archivo

    return None


def _normalizar_columnas(df):
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "").replace("_", "")
        for col in df.columns
    ]
    return df


def obtener_lms(tabla, edad_meses):
    """Obtiene los valores L, M y S de la tabla OMS."""

    if tabla is None or tabla.empty:
        raise ValueError("La tabla OMS está vacía.")

    df = _normalizar_columnas(tabla)

    necesarias = ["month", "l", "m", "s"]

    for columna in necesarias:
        if columna not in df.columns:
            raise ValueError(
                f"Falta la columna {columna} en la tabla OMS."
            )

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

    df = df.dropna(subset=necesarias)
    df = df.sort_values("month")

    if df.empty:
        raise ValueError("No hay datos LMS válidos.")

    meses = df["month"].to_numpy(dtype=float)

    if edad_meses < meses.min() or edad_meses > meses.max():
        raise ValueError(
            f"Edad fuera del rango de la tabla: "
            f"{meses.min():g} a {meses.max():g} meses."
        )

    L = float(np.interp(edad_meses, meses, df["l"]))
    M = float(np.interp(edad_meses, meses, df["m"]))
    S = float(np.interp(edad_meses, meses, df["s"]))

    if M <= 0 or S <= 0:
        raise ValueError("Los valores OMS M y S no son válidos.")

    return L, M, S


def calcular_puntaje_z_oms(imc, edad_meses, sexo, tablas):

    if imc <= 0:
        raise ValueError("El IMC debe ser mayor que cero.")

    if not 24 <= edad_meses <= 228:
        raise ValueError("La edad debe estar entre 24 y 228 meses.")

    sexo = str(sexo).strip().lower()

    if sexo in ("masculino", "hombre", "niño", "nino"):
        prefijo = "Masculino"
    elif sexo in ("femenino", "mujer", "niña", "nina"):
        prefijo = "Femenino"
    else:
        raise ValueError("Sexo no válido.")

    if edad_meses <= 60:
        clave = f"{prefijo}_2_5"
    else:
        clave = f"{prefijo}_5_19"

    if clave not in tablas:
        raise ValueError(f"No se cargó la tabla OMS {clave}.")

    L, M, S = obtener_lms(tablas[clave], edad_meses)

    if abs(L) < 1e-10:
        z = np.log(imc / M) / S
    else:
        z = ((imc / M) ** L - 1) / (L * S)

    if not np.isfinite(z):
        raise ValueError("El puntaje Z calculado no es válido.")

    return float(z)


def calcular_puntaje_z_bmi(imc, edad_meses, sexo, tablas):
    return calcular_puntaje_z_oms(
        imc, edad_meses, sexo, tablas
    )


def clasificar_bmi_oms(z, edad_meses):

    if not 24 <= edad_meses <= 228:
        raise ValueError("Edad fuera del rango infantil OMS.")

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
