
from __future__ import annotations

import io
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "rea_25_26_dashboard_ready.csv"
HIST_LOCAL_PATH = BASE_DIR / "data" / "historico" / "pricing_vs_excel.csv"
HIST_RAW_URL = "https://raw.githubusercontent.com/salva67/tarifador-ML/main/data/raw/pricing_vs_excel.csv"


st.set_page_config(
    page_title="Dashboard REA 25-26",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Helpers
# -----------------------------
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


def safe_div(num, den):
    return np.where(den != 0, num / den, np.nan)


def fmt_money(value, decimals=0):
    if pd.isna(value):
        return "-"
    return f"USD {value:,.{decimals}f}"


def fmt_pct(value, decimals=1):
    if pd.isna(value):
        return "-"
    return f"{value:.{decimals}%}"


def add_css():
    st.markdown(
        """
        <style>
        .main .block-container {padding-top: 1.5rem;}
        .metric-card {
            padding: 16px 18px;
            border-radius: 18px;
            background: #FFFFFF;
            box-shadow: 0 1px 12px rgba(15, 23, 42, 0.08);
            border: 1px solid #E5E7EB;
            min-height: 110px;
        }
        .metric-title {
            color: #64748B;
            font-size: 0.82rem;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }
        .metric-value {
            color: #0F172A;
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.2;
        }
        .metric-sub {
            color: #64748B;
            font-size: 0.78rem;
            margin-top: 0.4rem;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 6px;
        }
        .badge-red {background:#FEE2E2;color:#991B1B;}
        .badge-yellow {background:#FEF3C7;color:#92400E;}
        .badge-green {background:#DCFCE7;color:#166534;}
        .badge-blue {background:#DBEAFE;color:#1E40AF;}
        .section-note {
            padding: 12px 14px;
            border-left: 4px solid #2563EB;
            background: #EFF6FF;
            border-radius: 12px;
            color:#1E3A8A;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(title, value, subtitle=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_campaign() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    for col in ["cosecha", "cobertura", "cultivo", "provincia", "departamento"]:
        df[col] = df[col].map(normalize_label)

    for col in ["cultivo", "provincia", "departamento"]:
        df[f"{col}_key"] = df[col].map(normalize_key)

    numeric_cols = [
        "hectareas",
        "suma_asegurada_usd",
        "suma_asegurada_helada_usd",
        "prima_usd",
        "st_pagado_usd",
        "rsp_usd",
        "hyg_usd",
        "siniestros_totales_usd",
        "resultado_tecnico_usd",
        "loss_ratio_campania",
        "loss_cost_campania",
        "tasa_prima",
        "tasa_rea",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


@st.cache_data(show_spinner=False)
def load_historical_from_csv(content: bytes | None, try_github: bool) -> pd.DataFrame | None:
    try:
        if content is not None:
            hist = pd.read_csv(io.BytesIO(content))
        elif HIST_LOCAL_PATH.exists():
            hist = pd.read_csv(HIST_LOCAL_PATH)
        elif try_github:
            hist = pd.read_csv(HIST_RAW_URL)
        else:
            return None
    except Exception:
        return None

    # Normaliza nombres mínimos esperados del tarifador.
    rename = {c: c.strip() for c in hist.columns}
    hist = hist.rename(columns=rename)

    # Si viene con nombres en mayúsculas del repo.
    colmap = {c.upper(): c for c in hist.columns}
    for source, target in [("CULTIVO", "cultivo"), ("PROVINCIA", "provincia"), ("DEPTO", "departamento")]:
        if source in colmap and target not in hist.columns:
            hist = hist.rename(columns={colmap[source]: target})

    needed = ["cultivo", "provincia", "departamento"]
    if not all(c in hist.columns for c in needed):
        return None

    hist["cultivo_key"] = hist["cultivo"].map(normalize_key)
    hist["provincia_key"] = hist["provincia"].map(normalize_key)
    hist["departamento_key"] = hist["departamento"].map(normalize_key)

    # Históricos esperados desde tarifador-ML.
    for c in [
        "loss_cost_hist",
        "premium_rate_hist",
        "exposure_hist_usd",
        "premium_hist_usd",
        "claims_hist_usd",
        "technical_rate_final",
        "technical_rate_with_cat",
        "sufficiency_index",
        "T_FINAL_EXCEL",
        "LC_MEDIA_EXCEL",
    ]:
        if c in hist.columns:
            hist[c] = pd.to_numeric(hist[c], errors="coerce")

    if "loss_ratio_historico" not in hist.columns:
        if {"claims_hist_usd", "premium_hist_usd"}.issubset(hist.columns):
            hist["loss_ratio_historico"] = hist["claims_hist_usd"] / hist["premium_hist_usd"].replace(0, np.nan)
        else:
            hist["loss_ratio_historico"] = np.nan

    # Loss cost histórico: prioriza loss_cost_hist; si no, LC_MEDIA_EXCEL.
    if "loss_cost_historico" not in hist.columns:
        if "loss_cost_hist" in hist.columns:
            hist["loss_cost_historico"] = hist["loss_cost_hist"]
        elif "LC_MEDIA_EXCEL" in hist.columns:
            hist["loss_cost_historico"] = hist["LC_MEDIA_EXCEL"]
        else:
            hist["loss_cost_historico"] = np.nan

    keep = [
        "cultivo_key",
        "provincia_key",
        "departamento_key",
        "loss_ratio_historico",
        "loss_cost_historico",
        "premium_rate_hist",
        "technical_rate_final",
        "technical_rate_with_cat",
        "sufficiency_index",
        "exposure_hist_usd",
        "premium_hist_usd",
        "claims_hist_usd",
    ]
    keep = [c for c in keep if c in hist.columns]
    return hist[keep].drop_duplicates(["cultivo_key", "provincia_key", "departamento_key"])


def add_historical(df: pd.DataFrame, hist: pd.DataFrame | None) -> pd.DataFrame:
    out = df.copy()
    if hist is None or hist.empty:
        out["loss_ratio_historico"] = np.nan
        out["loss_cost_historico"] = np.nan
        out["gap_loss_ratio"] = np.nan
        out["gap_loss_cost"] = np.nan
        out["indice_loss_cost"] = np.nan
        out["tiene_historico"] = False
        return out

    out = out.merge(
        hist,
        on=["cultivo_key", "provincia_key", "departamento_key"],
        how="left",
        suffixes=("", "_hist"),
    )
    out["gap_loss_ratio"] = out["loss_ratio_campania"] - out["loss_ratio_historico"]
    out["gap_loss_cost"] = out["loss_cost_campania"] - out["loss_cost_historico"]
    out["indice_loss_cost"] = out["loss_cost_campania"] / out["loss_cost_historico"].replace(0, np.nan)
    out["tiene_historico"] = out["loss_cost_historico"].notna() | out["loss_ratio_historico"].notna()
    return out


def aggregate(df: pd.DataFrame, dims: list[str]) -> pd.DataFrame:
    g = (
        df.groupby(dims, dropna=False, as_index=False)
        .agg(
            registros=("cultivo", "size"),
            hectareas=("hectareas", "sum"),
            suma_asegurada_usd=("suma_asegurada_usd", "sum"),
            prima_usd=("prima_usd", "sum"),
            st_pagado_usd=("st_pagado_usd", "sum"),
            rsp_usd=("rsp_usd", "sum"),
            hyg_usd=("hyg_usd", "sum"),
            siniestros_totales_usd=("siniestros_totales_usd", "sum"),
        )
    )
    g["resultado_tecnico_usd"] = g["prima_usd"] - g["siniestros_totales_usd"]
    g["loss_ratio_campania"] = g["siniestros_totales_usd"] / g["prima_usd"].replace(0, np.nan)
    g["loss_cost_campania"] = g["siniestros_totales_usd"] / g["suma_asegurada_usd"].replace(0, np.nan)
    g["tasa_prima"] = g["prima_usd"] / g["suma_asegurada_usd"].replace(0, np.nan)
    g["participacion_suma"] = g["suma_asegurada_usd"] / g["suma_asegurada_usd"].sum()
    g["participacion_prima"] = g["prima_usd"] / g["prima_usd"].sum()
    return g


def build_alerts(df: pd.DataFrame, concentration_threshold: float, lr_tolerance: float, lc_tolerance: float) -> pd.DataFrame:
    work = df.copy()
    total_expo = work["suma_asegurada_usd"].sum()
    work["participacion_suma"] = work["suma_asegurada_usd"] / total_expo if total_expo else 0

    alert_rows = []
    for _, r in work.iterrows():
        labels = []
        severity = 0

        if r["participacion_suma"] >= concentration_threshold:
            labels.append("Alta concentración")
            severity = max(severity, 2)

        if r["resultado_tecnico_usd"] < 0:
            labels.append("Resultado negativo")
            severity = max(severity, 3)

        if pd.notna(r.get("loss_ratio_historico")) and r.get("loss_ratio_historico", np.nan) > 0:
            if r["loss_ratio_campania"] > r["loss_ratio_historico"] * (1 + lr_tolerance):
                labels.append("Loss Ratio > histórico")
                severity = max(severity, 3)

        if pd.notna(r.get("loss_cost_historico")) and r.get("loss_cost_historico", np.nan) > 0:
            if r["loss_cost_campania"] > r["loss_cost_historico"] * (1 + lc_tolerance):
                labels.append("Loss Cost > histórico")
                severity = max(severity, 3)

        if labels:
            alert_rows.append({
                "severidad": severity,
                "alertas": " | ".join(labels),
                "cosecha": r["cosecha"],
                "cultivo": r["cultivo"],
                "provincia": r["provincia"],
                "departamento": r["departamento"],
                "suma_asegurada_usd": r["suma_asegurada_usd"],
                "prima_usd": r["prima_usd"],
                "siniestros_totales_usd": r["siniestros_totales_usd"],
                "resultado_tecnico_usd": r["resultado_tecnico_usd"],
                "loss_ratio_campania": r["loss_ratio_campania"],
                "loss_ratio_historico": r.get("loss_ratio_historico", np.nan),
                "loss_cost_campania": r["loss_cost_campania"],
                "loss_cost_historico": r.get("loss_cost_historico", np.nan),
                "indice_loss_cost": r.get("indice_loss_cost", np.nan),
                "participacion_suma": r["participacion_suma"],
            })

    if not alert_rows:
        return pd.DataFrame()
    return pd.DataFrame(alert_rows).sort_values(["severidad", "suma_asegurada_usd"], ascending=[False, False])


def style_alerts(df: pd.DataFrame):
    def row_style(row):
        sev = row.get("severidad", 0)
        if sev >= 3:
            return ["background-color: #FEE2E2; color:#7F1D1D"] * len(row)
        if sev == 2:
            return ["background-color: #FEF3C7; color:#78350F"] * len(row)
        return ["background-color: #DCFCE7; color:#14532D"] * len(row)

    fmt = {
        "suma_asegurada_usd": "USD {:,.0f}",
        "prima_usd": "USD {:,.0f}",
        "siniestros_totales_usd": "USD {:,.0f}",
        "resultado_tecnico_usd": "USD {:,.0f}",
        "loss_ratio_campania": "{:.1%}",
        "loss_ratio_historico": "{:.1%}",
        "loss_cost_campania": "{:.2%}",
        "loss_cost_historico": "{:.2%}",
        "indice_loss_cost": "{:.2f}",
        "participacion_suma": "{:.1%}",
    }
    return df.style.apply(row_style, axis=1).format(fmt, na_rep="-")


# -----------------------------
# Load
# -----------------------------
add_css()
df_base = load_campaign()

st.title("🌾 Dashboard REA 25-26")
st.caption("Reporte visual de campaña: cúmulos, resultado técnico, cultivos, cosecha y alertas de negocio.")

with st.sidebar:
    st.header("Filtros")
    cosechas = st.multiselect("Cosecha", sorted(df_base["cosecha"].dropna().unique()), default=sorted(df_base["cosecha"].dropna().unique()))
    provincias = st.multiselect("Provincia", sorted(df_base["provincia"].dropna().unique()), default=sorted(df_base["provincia"].dropna().unique()))
    cultivos = st.multiselect("Cultivo", sorted(df_base["cultivo"].dropna().unique()), default=sorted(df_base["cultivo"].dropna().unique()))

    st.divider()
    st.subheader("Histórico / índice confianza")
    try_github = st.checkbox("Intentar leer histórico desde GitHub", value=True)
    uploaded_hist = st.file_uploader(
        "O subir CSV histórico",
        type=["csv"],
        help="Puede ser pricing_vs_excel.csv del repo tarifador-ML o un archivo con loss_cost_historico/loss_ratio_historico.",
    )

    st.divider()
    st.subheader("Umbrales de alertas")
    concentration_threshold = st.slider("Alta concentración por fila", 0.01, 0.20, 0.05, 0.01)
    lr_tolerance = st.slider("Tolerancia Loss Ratio vs histórico", 0.00, 1.00, 0.10, 0.05)
    lc_tolerance = st.slider("Tolerancia Loss Cost vs histórico", 0.00, 1.00, 0.10, 0.05)

hist_content = uploaded_hist.getvalue() if uploaded_hist is not None else None
hist = load_historical_from_csv(hist_content, try_github=try_github)
df = add_historical(df_base, hist)

df_f = df[
    df["cosecha"].isin(cosechas)
    & df["provincia"].isin(provincias)
    & df["cultivo"].isin(cultivos)
].copy()

if df_f.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# -----------------------------
# Executive KPIs
# -----------------------------
prima = df_f["prima_usd"].sum()
siniestros = df_f["siniestros_totales_usd"].sum()
suma = df_f["suma_asegurada_usd"].sum()
resultado = prima - siniestros
loss_ratio = siniestros / prima if prima else np.nan
loss_cost = siniestros / suma if suma else np.nan
hectareas = df_f["hectareas"].sum()

st.markdown(
    """
    <div class="section-note">
    <b>Base actualizada:</b> la siniestralidad se calcula como <b>K + L + M</b>:
    ST Pagado + RSP + HYG. Esto recalcula Loss Ratio, Loss Cost, resultado técnico y alertas.
    </div>
    """,
    unsafe_allow_html=True,
)

kpi_cols = st.columns(6)
with kpi_cols[0]:
    metric_card("Suma asegurada", fmt_money(suma), f"{len(df_f):,} registros")
with kpi_cols[1]:
    metric_card("Prima", fmt_money(prima), f"Tasa prima {fmt_pct(prima / suma if suma else np.nan, 2)}")
with kpi_cols[2]:
    metric_card("Siniestros K+L+M", fmt_money(siniestros), f"ST + RSP + HYG")
with kpi_cols[3]:
    metric_card("Resultado técnico", fmt_money(resultado), "Prima - siniestros")
with kpi_cols[4]:
    metric_card("Loss Ratio", fmt_pct(loss_ratio), "Siniestros / Prima")
with kpi_cols[5]:
    metric_card("Loss Cost", fmt_pct(loss_cost, 2), "Siniestros / Suma asegurada")

st.markdown(
    f"""
    <span class="badge badge-blue">Hectáreas: {hectareas:,.0f}</span>
    <span class="badge badge-green">Cultivos: {df_f["cultivo"].nunique()}</span>
    <span class="badge badge-green">Departamentos: {df_f["departamento"].nunique()}</span>
    <span class="badge badge-yellow">Histórico cruzado: {df_f["tiene_historico"].mean():.0%}</span>
    """,
    unsafe_allow_html=True,
)

tabs = st.tabs([
    "Resumen",
    "Cúmulos por zona",
    "Resultado por cosecha",
    "Cultivos",
    "Matriz zona-cultivo",
    "Alertas",
    "Datos",
])

# -----------------------------
# Resumen
# -----------------------------
with tabs[0]:
    c1, c2 = st.columns([1.2, 1])
    prov_agg = aggregate(df_f, ["provincia"]).sort_values("suma_asegurada_usd", ascending=False)
    cult_agg = aggregate(df_f, ["cultivo"]).sort_values("suma_asegurada_usd", ascending=False)

    with c1:
        fig = px.bar(
            prov_agg,
            x="provincia",
            y="suma_asegurada_usd",
            text_auto=".2s",
            title="Cúmulo de suma asegurada por provincia",
            labels={"suma_asegurada_usd": "Suma asegurada USD", "provincia": "Provincia"},
        )
        fig.update_layout(height=420, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.pie(
            cult_agg,
            names="cultivo",
            values="prima_usd",
            title="Distribución de prima por cultivo",
            hole=0.45,
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Lectura rápida")
    worst_lr = aggregate(df_f, ["provincia", "departamento"]).sort_values("loss_ratio_campania", ascending=False).head(5)
    st.dataframe(
        worst_lr[["provincia", "departamento", "prima_usd", "siniestros_totales_usd", "loss_ratio_campania", "loss_cost_campania"]].style.format({
            "prima_usd": "USD {:,.0f}",
            "siniestros_totales_usd": "USD {:,.0f}",
            "loss_ratio_campania": "{:.1%}",
            "loss_cost_campania": "{:.2%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Cúmulos
# -----------------------------
with tabs[1]:
    st.subheader("Cúmulos por provincia y departamento")
    nivel = st.radio("Nivel de análisis", ["Provincia", "Departamento"], horizontal=True)
    if nivel == "Provincia":
        zone = aggregate(df_f, ["provincia"]).sort_values("suma_asegurada_usd", ascending=False)
        x_col = "provincia"
    else:
        zone = aggregate(df_f, ["provincia", "departamento"]).sort_values("suma_asegurada_usd", ascending=False).head(30)
        zone["zona"] = zone["provincia"] + " - " + zone["departamento"]
        x_col = "zona"

    fig = px.bar(
        zone,
        x=x_col,
        y="suma_asegurada_usd",
        color="loss_ratio_campania",
        text_auto=".2s",
        title=f"Top cúmulos por {nivel.lower()}",
        labels={"suma_asegurada_usd": "Suma asegurada USD", "loss_ratio_campania": "Loss Ratio"},
        color_continuous_scale="RdYlGn_r",
    )
    fig.update_layout(height=520, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        zone.style.format({
            "hectareas": "{:,.0f}",
            "suma_asegurada_usd": "USD {:,.0f}",
            "prima_usd": "USD {:,.0f}",
            "siniestros_totales_usd": "USD {:,.0f}",
            "resultado_tecnico_usd": "USD {:,.0f}",
            "loss_ratio_campania": "{:.1%}",
            "loss_cost_campania": "{:.2%}",
            "participacion_suma": "{:.1%}",
            "participacion_prima": "{:.1%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Cosecha
# -----------------------------
with tabs[2]:
    st.subheader("Resultado por cosecha")
    cosecha_agg = aggregate(df_f, ["cosecha"]).sort_values("prima_usd", ascending=False)
    c1, c2 = st.columns(2)
    with c1:
        long = cosecha_agg.melt(
            id_vars="cosecha",
            value_vars=["prima_usd", "siniestros_totales_usd"],
            var_name="métrica",
            value_name="usd",
        )
        fig = px.bar(
            long,
            x="cosecha",
            y="usd",
            color="métrica",
            barmode="group",
            title="Prima vs siniestros por cosecha",
            text_auto=".2s",
        )
        fig.update_layout(height=430)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(
            cosecha_agg,
            x="cosecha",
            y="loss_ratio_campania",
            color="loss_ratio_campania",
            title="Loss Ratio por cosecha",
            text_auto=".1%",
            color_continuous_scale="RdYlGn_r",
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(height=430)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        cosecha_agg.style.format({
            "hectareas": "{:,.0f}",
            "suma_asegurada_usd": "USD {:,.0f}",
            "prima_usd": "USD {:,.0f}",
            "siniestros_totales_usd": "USD {:,.0f}",
            "resultado_tecnico_usd": "USD {:,.0f}",
            "loss_ratio_campania": "{:.1%}",
            "loss_cost_campania": "{:.2%}",
            "tasa_prima": "{:.2%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Cultivos
# -----------------------------
with tabs[3]:
    st.subheader("Performance por cultivo")
    cult = aggregate(df_f, ["cultivo"]).sort_values("suma_asegurada_usd", ascending=False)
    fig = px.scatter(
        cult,
        x="suma_asegurada_usd",
        y="loss_ratio_campania",
        size="prima_usd",
        color="resultado_tecnico_usd",
        hover_name="cultivo",
        title="Mapa de cultivos: exposición, prima, Loss Ratio y resultado",
        labels={
            "suma_asegurada_usd": "Suma asegurada USD",
            "loss_ratio_campania": "Loss Ratio",
            "prima_usd": "Prima USD",
            "resultado_tecnico_usd": "Resultado técnico USD",
        },
        color_continuous_scale="RdYlGn",
    )
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        cult.sort_values("loss_ratio_campania", ascending=False).style.format({
            "hectareas": "{:,.0f}",
            "suma_asegurada_usd": "USD {:,.0f}",
            "prima_usd": "USD {:,.0f}",
            "siniestros_totales_usd": "USD {:,.0f}",
            "resultado_tecnico_usd": "USD {:,.0f}",
            "loss_ratio_campania": "{:.1%}",
            "loss_cost_campania": "{:.2%}",
            "participacion_suma": "{:.1%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Matriz zona-cultivo
# -----------------------------
with tabs[4]:
    st.subheader("Matriz zona-cultivo")
    metric = st.selectbox(
        "Métrica para colorear",
        ["loss_ratio_campania", "loss_cost_campania", "suma_asegurada_usd", "resultado_tecnico_usd", "prima_usd"],
        index=0,
    )
    zona_metric = aggregate(df_f, ["provincia", "cultivo"])
    pivot = zona_metric.pivot_table(index="provincia", columns="cultivo", values=metric, aggfunc="sum")
    if metric in ["loss_ratio_campania", "loss_cost_campania"]:
        # Para ratios, recomputar correctamente a partir de agregados.
        if metric == "loss_ratio_campania":
            pivot = zona_metric.pivot(index="provincia", columns="cultivo", values="loss_ratio_campania")
        else:
            pivot = zona_metric.pivot(index="provincia", columns="cultivo", values="loss_cost_campania")

    fig = px.imshow(
        pivot,
        text_auto=".1%" if metric in ["loss_ratio_campania", "loss_cost_campania"] else ".2s",
        aspect="auto",
        color_continuous_scale="RdYlGn_r" if metric in ["loss_ratio_campania", "loss_cost_campania"] else "Blues",
        title=f"Heatmap provincia x cultivo - {metric}",
    )
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Alertas
# -----------------------------
with tabs[5]:
    st.subheader("Alertas de negocio")
    alerts = build_alerts(df_f, concentration_threshold, lr_tolerance, lc_tolerance)

    if alerts.empty:
        st.success("No se detectaron alertas bajo los umbrales actuales.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Alertas", len(alerts))
        with c2:
            st.metric("Resultado negativo", int(alerts["alertas"].str.contains("Resultado negativo").sum()))
        with c3:
            st.metric("Alta concentración", int(alerts["alertas"].str.contains("Alta concentración").sum()))

        st.dataframe(
            style_alerts(alerts),
            use_container_width=True,
            hide_index=True,
        )

        csv_alerts = alerts.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar alertas CSV", csv_alerts, "alertas_rea_25_26.csv", "text/csv")

    st.info(
        "Las alertas comparativas contra histórico se activan si se logra cruzar contra pricing_vs_excel.csv "
        "u otro CSV histórico por cultivo + provincia + departamento."
    )

# -----------------------------
# Datos
# -----------------------------
with tabs[6]:
    st.subheader("Base filtrada")
    st.dataframe(
        df_f.style.format({
            "hectareas": "{:,.0f}",
            "suma_asegurada_usd": "USD {:,.0f}",
            "prima_usd": "USD {:,.0f}",
            "st_pagado_usd": "USD {:,.0f}",
            "rsp_usd": "USD {:,.0f}",
            "hyg_usd": "USD {:,.0f}",
            "siniestros_totales_usd": "USD {:,.0f}",
            "resultado_tecnico_usd": "USD {:,.0f}",
            "loss_ratio_campania": "{:.1%}",
            "loss_cost_campania": "{:.2%}",
            "loss_ratio_historico": "{:.1%}",
            "loss_cost_historico": "{:.2%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Descargar base filtrada CSV",
        df_f.to_csv(index=False).encode("utf-8"),
        "rea_25_26_base_filtrada.csv",
        "text/csv",
    )
