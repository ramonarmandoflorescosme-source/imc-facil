import math
from pathlib import Path
import numpy as np
import pandas as pd

# Ruta segura relativa al archivo actual
DATA_DIR = Path(__file__).parent / "data"

ARCHIVOS_OMS = {
    ("masculino", "2_5"): "bmi_boys_2-to-5-years_zscores.xlsx",
    ("femenino", "2_5"): "bmi_girls_2-to-5-years_zscores.xlsx",
    ("masculino", "5_19"): "bmi-boys-z-who-2007-exp.xlsx",
    ("femenino", "5_19"): "bmi-girls-z-who-2007-exp.xlsx",
    ("masculino", "0_5_dias"): "bfa-boys-zscore-expanded-tables.xlsx",
    ("femenino", "0_5_dias"): "bfa-girls-zscore-expanded-tables.xlsx",
}

def normalizar_sexo(sexo: str) -> str:
    s = sexo.lower().strip()
    if s in ["masculino", "niño", "nino", "m"]:
        return "masculino"
    if s in ["femenino", "niña", "nina", "f"]:
        return "femenino"
    raise ValueError(f"Sexo no válido: {sexo}")

def formula_lms(imc: float, L: float, M: float, S: float) -> float:
    """Aplica la ecuación estándar LMS de la OMS."""
    if L == 0:
        return math.log(imc / M) / S
    return ((imc / M) ** L - 1) / (L * S)

def interpolar_lms(tabla: pd.DataFrame, col_tiempo: str, valor_tiempo: float) -> tuple[float, float, float]:
    L = float(np.interp(valor_tiempo, tabla[col_tiempo], tabla["L"]))
    M = float(np.interp(valor_tiempo, tabla[col_tiempo], tabla["M"]))
    S = float(np.interp(valor_tiempo, tabla[col_tiempo], tabla["S"]))
    return L, M, S

def calcular_puntaje_z_oms(imc: float, edad_meses: int, sexo: str, tablas: dict) -> float:
    sexo_norm = normalizar_sexo(sexo)

    # Menores de 61 meses (2 a 5 años) usan la tabla expandida en días
    if edad_meses < 61:
        edad_dias = edad_meses * 30.4375
        tabla = tablas[(sexo_norm, "0_5_dias")]
        L, M, S = interpolar_lms(tabla, "Day", edad_dias)
        return formula_lms(imc, L, M, S)

    # De 61 a 228 meses (5 a 19 años)
    tabla = tablas[(sexo_norm, "5_19")]
    if not (tabla["Month"].min() <= edad_meses <= tabla["Month"].max()):
        raise ValueError("Edad fuera del rango de las tablas OMS (24 a 228 meses).")

    L, M, S = interpolar_lms(tabla, "Month", edad_meses)
    z = formula_lms(imc, L, M, S)

    # Ajuste OMS para valores extremos (|Z| > 3) en mayores de 5 años
    if z > 3:
        sd2 = float(np.interp(edad_meses, tabla["Month"], tabla["SD2"]))
        sd3 = float(np.interp(edad_meses, tabla["Month"], tabla["SD3"]))
        z = 3 + (imc - sd3) / (sd3 - sd2)
    elif z < -3:
        sd2_neg = float(np.interp(edad_meses, tabla["Month"], tabla["SD2neg"]))
        sd3_neg = float(np.interp(edad_meses, tabla["Month"], tabla["SD3neg"]))
        z = -3 + (imc - sd3_neg) / (sd2_neg - sd3_neg)

    return z

def clasificar_bmi_oms(z: float, edad_meses: int) -> tuple[str, str]:
    """Devuelve (Categoría, Emoji indicador) según el grupo etario."""
    if z < -3:
        return "Delgadez severa", "🔴"
    if z < -2:
        return "Delgadez", "🟠"

    if edad_meses < 61:
        if z > 3: return "Obesidad", "🔴"
        if z > 2: return "Sobrepeso", "🟠"
        if z > 1: return "Riesgo de sobrepeso", "🟡"
        return "Peso adecuado", "🟢"
    else:
        if z > 2: return "Obesidad", "🔴"
        if z > 1: return "Sobrepeso", "🟠"
        return "Peso adecuado", "🟢"
