
"""
Regenera data/rea_25_26_dashboard_ready.csv desde un Excel actualizado.

Uso:
    python preparar_base_desde_excel.py --input "data/raw/Copia de REA 25-26 v2 (1).xlsx"

La lógica de siniestralidad toma columnas K, L y M:
    ST PAGADO 100%- USD + RSP 100%- USD + HYG 100%- USD
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd


def normalize_label(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_key(value) -> str:
    s = normalize_label(value)
    return re.sub(r"[^A-Z0-9]+", "", s)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Ruta del Excel actualizado")
    parser.add_argument("--sheet", default="25-26", help="Nombre de la solapa")
    parser.add_argument("--output", default="data/rea_25_26_dashboard_ready.csv")
    args = parser.parse_args()

    # En el archivo original, la fila 5 contiene los encabezados.
    df = pd.read_excel(args.input, sheet_name=args.sheet, header=4)

    # Usamos posiciones para respetar la indicación: K, L, M.
    out = pd.DataFrame()
    out["anio_contrato"] = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    out["cosecha"] = df.iloc[:, 1].map(normalize_label)
    out["cobertura"] = df.iloc[:, 2].map(normalize_label)
    out["cultivo"] = df.iloc[:, 3].map(normalize_label)
    out["provincia"] = df.iloc[:, 4].map(normalize_label)
    out["departamento"] = df.iloc[:, 5].map(normalize_label)
    out["hectareas"] = pd.to_numeric(df.iloc[:, 6], errors="coerce").fillna(0)
    out["suma_asegurada_usd"] = pd.to_numeric(df.iloc[:, 7], errors="coerce").fillna(0)
    out["suma_asegurada_helada_usd"] = pd.to_numeric(df.iloc[:, 8], errors="coerce").fillna(0)
    out["prima_usd"] = pd.to_numeric(df.iloc[:, 9], errors="coerce").fillna(0)

    out["st_pagado_usd"] = pd.to_numeric(df.iloc[:, 10], errors="coerce").fillna(0)
    out["rsp_usd"] = pd.to_numeric(df.iloc[:, 11], errors="coerce").fillna(0)
    out["hyg_usd"] = pd.to_numeric(df.iloc[:, 12], errors="coerce").fillna(0)
    out["siniestros_totales_usd"] = out["st_pagado_usd"] + out["rsp_usd"] + out["hyg_usd"]

    out["resultado_tecnico_usd"] = out["prima_usd"] - out["siniestros_totales_usd"]
    out["loss_ratio_campania"] = out["siniestros_totales_usd"] / out["prima_usd"].replace(0, pd.NA)
    out["loss_cost_campania"] = out["siniestros_totales_usd"] / out["suma_asegurada_usd"].replace(0, pd.NA)
    out["tasa_prima"] = out["prima_usd"] / out["suma_asegurada_usd"].replace(0, pd.NA)

    # Columna U: tasas REA, si existe.
    out["tasa_rea"] = pd.to_numeric(df.iloc[:, 20], errors="coerce").fillna(0) if df.shape[1] > 20 else 0

    out = out[
        (out["cultivo"] != "")
        & (out["provincia"] != "")
        & (out["departamento"] != "")
    ].copy()

    out["anio_contrato"] = out["anio_contrato"].astype("Int64")
    out["cultivo_key"] = out["cultivo"].map(normalize_key)
    out["provincia_key"] = out["provincia"].map(normalize_key)
    out["departamento_key"] = out["departamento"].map(normalize_key)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)

    print("OK - base generada:", output)
    print("Registros:", len(out))
    print("Prima USD:", round(out["prima_usd"].sum(), 2))
    print("Siniestros K+L+M USD:", round(out["siniestros_totales_usd"].sum(), 2))
    print("Loss Ratio:", round(out["siniestros_totales_usd"].sum() / out["prima_usd"].sum(), 4))


if __name__ == "__main__":
    main()
