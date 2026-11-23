import math
from pathlib import Path
import numpy as np
import pandas as pd

# Ruta segura relativa a este archivo hacia la carpeta data/
DATA_DIR = Path(__file__).resolve().parent / "data"

ARCHIVOS_OMS = {
    ("masculino", "5_19"): "bmi-boys-z-who-2007-exp.xlsx",
    ("femenino", "5_19"): "bmi-girls-z-who-2007-exp.xlsx",
    ("masculino", "0_5_dias"): "bfa-boys-zscore-expanded-tables.xlsx",
    ("femenino", "0_5_dias"): "bfa-girls-zscore-expanded-tables.xlsx",
}


def normalizar_sexo(sexo: str) -> str:
    s = str(sexo).lower().strip()
    if s in {"masculino", "niño", "nino", "m"}:
        return "masculino"
    if s in {"femenino", "niña", "nina", "f"}:
        return "femenino"
    raise ValueError(f"Sexo no válido: {sexo}")


def cargar_tablas_oms(data_dir: Path = DATA_DIR) -> dict[tuple[str, str], pd.DataFrame]:
    """Carga las tablas LMS de la OMS desde la carpeta data/."""
    tablas: dict[tuple[str, str], pd.DataFrame] = {}
    faltantes: list[str] = []

    for clave, nombre_archivo in ARCHIVOS_OMS.items():
        ruta = data_dir / nombre_archivo
        if not ruta.exists():
            faltantes.append(f"{clave} -> {nombre_archivo}")
            continue
        tablas[clave] = pd.read_excel(ruta)

    if not tablas:
        raise FileNotFoundError(
            "No se encontró ninguna tabla OMS en 'data/'. Archivos esperados: "
            + ", ".join(ARCHIVOS_OMS.values())
        )

    if faltantes:
        # Guarda las claves faltantes para informar sin bloquear las demás
        tablas["_faltantes"] = faltantes  # type: ignore[assignment]

    return tablas


def convertir_peso_a_kg(peso: float, unidad: str) -> float:
    u = str(unidad).strip().lower()
    if u in {"kg", "kilogramos", "kilo", "kilos"}:
        return float(peso)
    if u in {"lb", "lbs", "libra", "libras"}:
        return float(peso) * 0.45359237
    raise ValueError(f"Unidad de peso no válida: {unidad}")


def convertir_estatura_a_metros(
    valor_principal: float, unidad_modo: str, pulgadas_extra: float = 0.0
) -> float:
    modo = str(unidad_modo).strip().lower()
    if "cm" in modo or "cent" in modo:
        return float(valor_principal) / 100.0
    if "pie" in modo or "ft" in modo:
        total_pulgadas = (float(valor_principal) * 12.0) + float(pulgadas_extra)
        return total_pulgadas * 0.0254
    raise ValueError(f"Unidad de estatura no válida: {unidad_modo}")


def calcular_imc(peso_kg: float, estatura_m: float) -> float:
    if peso_kg <= 0:
        raise ValueError("El peso debe ser mayor que cero.")
    if estatura_m <= 0:
        raise ValueError("La estatura debe ser mayor que cero.")
    return peso_kg / (estatura_m ** 2)


def formula_lms(imc: float, L: float, M: float, S: float) -> float:
    """Aplica la ecuación estándar LMS de la OMS."""
    if imc <= 0 or M <= 0 or S <= 0:
        raise ValueError("El IMC y los parámetros LMS (M y S) deben ser mayores que cero.")
    if L == 0:
        return math.log(imc / M) / S
    return ((imc / M) ** L - 1) / (L * S)


def interpolar_lms(
    tabla: pd.DataFrame, col_tiempo: str, valor_tiempo: float
) -> tuple[float, float, float]:
    if col_tiempo not in tabla.columns:
        raise ValueError(f"La tabla OMS no contiene la columna '{col_tiempo}'.")

    tabla_ord = tabla.dropna(subset=[col_tiempo, "L", "M", "S"]).sort_values(col_tiempo)
    x = tabla_ord[col_tiempo].to_numpy(dtype=float)

    L = float(np.interp(valor_tiempo, x, tabla_ord["L"].to_numpy(dtype=float)))
    M = float(np.interp(valor_tiempo, x, tabla_ord["M"].to_numpy(dtype=float)))
    S = float(np.interp(valor_tiempo, x, tabla_ord["S"].to_numpy(dtype=float)))
    return L, M, S


def calcular_puntaje_z_oms(
    imc: float, edad_meses: int, sexo: str, tablas: dict
) -> float:
    sexo_norm = normalizar_sexo(sexo)

    if edad_meses < 0 or edad_meses > 228:
        raise ValueError("La edad debe estar entre 0 y 228 meses (0 a 19 años).")

    # Menores de 61 meses (0 a 60 meses) usan tabla expandida en días
    if edad_meses < 61:
        clave = (sexo_norm, "0_5_dias")
        if clave not in tablas or not isinstance(tablas[clave], pd.DataFrame):
            archivo_esp = ARCHIVOS_OMS.get(clave, "tabla 0-5 años")
            raise KeyError(
                f"Falta cargar la tabla OMS para {sexo_norm} (0–5 años, archivo '{archivo_esp}')."
            )

        tabla = tablas[clave]
        edad_dias = edad_meses * 30.4375
        L, M, S = interpolar_lms(tabla, "Day", edad_dias)
        return formula_lms(imc, L, M, S)

    # De 61 a 228 meses (5 a 19 años)
    clave = (sexo_norm, "5_19")
    if clave not in tablas or not isinstance(tablas[clave], pd.DataFrame):
        archivo_esp = ARCHIVOS_OMS.get(clave, "tabla 5-19 años")
        raise KeyError(
            f"Falta cargar la tabla OMS para {sexo_norm} (5–19 años, archivo '{archivo_esp}')."
        )

    tabla = tablas[clave]
    if "Month" not in tabla.columns:
        raise ValueError("La tabla OMS de 5–19 años no contiene la columna 'Month'.")

    if not (tabla["Month"].min() <= edad_meses <= tabla["Month"].max()):
        raise ValueError("Edad fuera del rango de las tablas OMS.")

    L, M, S = interpolar_lms(tabla, "Month", edad_meses)
    z = formula_lms(imc, L, M, S)

    tabla_ord = tabla.sort_values("Month")
    if z > 3 and {"SD2", "SD3"}.issubset(tabla_ord.columns):
        sd2 = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD2"]))
        sd3 = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD3"]))
        denom = sd3 - sd2
        if denom != 0:
            z = 3 + (imc - sd3) / denom
    elif z < -3 and {"SD2neg", "SD3neg"}.issubset(tabla_ord.columns):
        sd2_neg = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD2neg"]))
        sd3_neg = float(np.interp(edad_meses, tabla_ord["Month"], tabla_ord["SD3neg"]))
        denom = sd2_neg - sd3_neg
        if denom != 0:
            z = -3 + (imc - sd3_neg) / denom

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

    if z > 2:
        return "Obesidad", "🔴"
    if z > 1:
        return "Sobrepeso", "🟠"
    return "Peso adecuado", "🟢"
