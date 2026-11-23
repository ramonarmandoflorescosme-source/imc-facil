import math
from pathlib import Path
import numpy as np
import pandas as pd

# Ruta segura relativa al archivo actual
DATA_DIR = Path(__file__).resolve().parent / "data"

ARCHIVOS_OMS = {
    ("masculino", "5_19"): "bmi-boys-z-who-2007-exp.xlsx",
    ("femenino", "5_19"): "bmi-girls-z-who-2007-exp.xlsx",
    ("masculino", "0_5_dias"): "bfa-boys-zscore-expanded-tables.xlsx",
    ("femenino", "0_5_dias"): "bfa-girls-zscore-expanded-tables.xlsx",
}


def cargar_tablas_oms(data_dir: Path = DATA_DIR) -> dict[tuple[str, str], pd.DataFrame]:
    """Carga todas las tablas LMS configuradas en ARCHIVOS_OMS."""
    tablas: dict[tuple[str, str], pd.DataFrame] = {}
    for clave, nombre_archivo in ARCHIVOS_OMS.items():
        ruta = data_dir / nombre_archivo
        if not ruta.exists():
            raise FileNotFoundError(f"No se encontró el archivo OMS: {ruta}")
        tablas[clave] = pd.read_excel(ruta)
    return tablas


def normalizar_sexo(sexo: str) -> str:
    s = str(sexo).lower().strip()
    if s in ["masculino", "niño", "nino", "m"]:
        return "masculino"
    if s in ["femenino", "niña", "nina", "f"]:
        return "femenino"
    raise ValueError(f"Sexo no válido: {sexo}")


def formula_lms(imc: float, L: float, M: float, S: float) -> float:
    """Aplica la ecuación estándar LMS de la OMS."""
    if imc <= 0 or M <= 0 or S <= 0:
        raise ValueError("El IMC y los parámetros M y S deben ser mayores que cero.")
    if L == 0:
        return math.log(imc / M) / S
    return ((imc / M) ** L - 1) / (L * S)


def interpolar_lms(
    tabla: pd.DataFrame, col_tiempo: str, valor_tiempo: float
) -> tuple[float, float, float]:
    tabla_ordenada = tabla.sort_values(col_tiempo)
    L = float(np.interp(valor_tiempo, tabla_ordenada[col_tiempo], tabla_ordenada["L"]))
    M = float(np.interp(valor_tiempo, tabla_ordenada[col_tiempo], tabla_ordenada["M"]))
    S = float(np.interp(valor_tiempo, tabla_ordenada[col_tiempo], tabla_ordenada["S"]))
    return L, M, S


def calcular_puntaje_z_oms(
    imc: float, edad_meses: int, sexo: str, tablas: dict
) -> float:
    sexo_norm = normalizar_sexo(sexo)

    # Menores de 61 meses (hasta 60 meses / 5 años) usan la tabla expandida en días
    if edad_meses < 61:
        clave = (sexo_norm, "0_5_dias")
        if clave not in tablas:
            raise KeyError(f"Falta cargar la tabla OMS para {clave} en 'tablas'.")
        edad_dias = edad_meses * 30.4375
        tabla = tablas[clave]
        L, M, S = interpolar_lms(tabla, "Day", edad_dias)
        return formula_lms(imc, L, M, S)

    # De 61 a 228 meses (5 a 19 años)
    clave = (sexo_norm, "5_19")
    if clave not in tablas:
        raise KeyError(f"Falta cargar la tabla OMS para {clave} en 'tablas'.")

    tabla = tablas[clave]
    if not (tabla["Month"].min() <= edad_meses <= tabla["Month"].max()):
        raise ValueError("Edad fuera del rango de las tablas OMS (0 a 228 meses).")

    L, M, S = interpolar_lms(tabla, "Month", edad_meses)
    z = formula_lms(imc, L, M, S)

    # Ajuste OMS para valores extremos (|Z| > 3) en mayores de 5 años
    tabla_ord = tabla.sort_values("Month")
    if z > 3:
        sd2 = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD2"]))
        sd3 = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD3"]))
        z = 3 + (imc - sd3) / (sd3 - sd2)
    elif z < -3:
        sd2_neg = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD2neg"]))
        sd3_neg = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD3neg"]))
        z = -3 + (imc - sd3_neg) / (sd2_neg - sd3_neg)

    return z


def clasificar_bmi_oms(z: float, edad_meses: int) -> tuple[str, str]:
    """Devuelve (Categoría, Emoji indicador) según el grupo etario."""
    if z < -3:
        return "Delgadez severa", "🔴"
    if z < -2:
        return "Delgadez", "🟠"

    if edad_meses < 61:
        if z > 3:
            return "Obesidad", "🔴"
        if z > 2:
            return "Sobrepeso", "🟠"
        if z > 1:
            return "Riesgo de sobrepeso", "🟡"
        return "Peso adecuado", "🟢"
    else:
        if z > 2:
            return "Obesidad", "🔴"
        if z > 1:
            return "Sobrepeso", "🟠"
        return "Peso adecuado", "🟢"
