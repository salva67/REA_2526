# Dashboard REA 25-26 actualizado

Dashboard Streamlit para analizar la campaña REA 25-26 con foco en:

- cúmulos por zona, provincia y departamento,
- resultado por cosecha,
- performance por cultivo,
- matriz zona-cultivo,
- alertas de negocio por concentración, resultado negativo y comparación contra histórico.

## Cambio incorporado

La siniestralidad se recalcula como la suma de las columnas **K + L + M** de la solapa `25-26`:

- K: `ST PAGADO 100%- USD`
- L: `RSP 100%- USD`
- M: `HYG 100%- USD`

Validación sobre el archivo reenviado:

- Registros válidos: 210
- Suma asegurada: USD 64,906,579
- Prima: USD 2,132,683
- ST pagado: USD 694,339
- RSP: USD 42,074
- HYG: USD 66,896
- **Siniestros totales K+L+M: USD 803,309**
- Resultado técnico: USD 1,329,373
- Loss Ratio: 37.7%
- Loss Cost: 1.24%

## Cómo correr

```bash
pip install -r requirements.txt
streamlit run app.py
```

En Windows:

```bash
run_dashboard_windows.bat
```

## Cruce con histórico

El dashboard puede intentar leer automáticamente:

```text
https://raw.githubusercontent.com/salva67/tarifador-ML/main/data/raw/pricing_vs_excel.csv
```

También se puede subir un CSV histórico desde el sidebar.

Columnas sugeridas para histórico:

- `CULTIVO`
- `PROVINCIA`
- `DEPTO`
- `loss_cost_hist`
- `premium_hist_usd`
- `claims_hist_usd`

Con eso el dashboard calcula:

- Loss Ratio campaña vs histórico
- Loss Cost campaña vs histórico
- Índice Loss Cost campaña / histórico
- Alertas por desvío

## Cómo actualizar con otro Excel

Reemplazá el archivo en `data/raw/` y corré:

```bash
python preparar_base_desde_excel.py --input "data/raw/NOMBRE_DEL_ARCHIVO.xlsx"
streamlit run app.py
```
