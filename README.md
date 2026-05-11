# Dashboard de negocio REA 25-26

Dashboard Streamlit para analizar visualmente la campaña REA 25-26.

## Objetivo

Transformar la base de campaña en un reporte visual de gestión que permita analizar:

- cúmulos de exposición por provincia/departamento;
- resultado técnico por cosecha;
- performance por cultivo;
- matriz zona-cultivo;
- alertas de negocio por concentración, siniestralidad y resultado negativo.

## Estructura

```text
rea_25_26_dashboard_negocio/
├── app.py
├── requirements.txt
├── README.md
├── run_dashboard_windows.bat
└── data/
    └── rea_25_26_dashboard_ready.csv
```

## Cómo correrlo

Desde una terminal:

```bash
cd rea_25_26_dashboard_negocio
pip install -r requirements.txt
streamlit run app.py
```

En Windows también podés ejecutar:

```bash
run_dashboard_windows.bat
```

## Indicadores principales

El dashboard recalcula dinámicamente según filtros:

- suma asegurada;
- hectáreas;
- prima;
- siniestros totales;
- resultado técnico;
- tasa de prima;
- Loss Cost campaña;
- Loss Ratio;
- participación de cúmulos sobre el total.

## Notas

Esta versión está enfocada en el objetivo inicial de negocio: lectura visual de la campaña. El cruce con tarifador, Loss Cost histórico e índices de confianza puede integrarse como segunda etapa.
