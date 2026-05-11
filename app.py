from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "rea_25_26_dashboard_ready.csv"

st.set_page_config(
    page_title="REA 25-26 | Dashboard de Negocio",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Estilo visual
# -----------------------------
st.markdown(
    """
    <style>
    .main .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    .metric-card {
        border: 1px solid #E7E7E7;
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%);
        box-shadow: 0 2px 10px rgba(0,0,0,.035);
        min-height: 112px;
    }
    .metric-label {font-size: 0.82rem; color: #606060; margin-bottom: 0.35rem;}
    .metric-value {font-size: 1.7rem; font-weight: 760; color: #1E1E1E; line-height: 1.1;}
    .metric-help {font-size: 0.78rem; color: #777; margin-top: 0.35rem;}
    .insight-box {
        border-left: 5px solid #B88746;
        background: #FFF8EF;
        padding: 14px 16px;
        border-radius: 12px;
        margin: 8px 0 12px 0;
        color: #343434;
    }
    .section-title {font-size: 1.15rem; font-weight: 700; margin: 0.6rem 0 0.35rem 0;}
    div[data-testid="stDataFrame"] {border-radius: 12px; overflow: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)

    text_cols = [
        "cosecha",
        "cobertura",
        "cultivo",
        "provincia",
        "departamento",
        "semaforo_loss_ratio",
        "cluster_negocio",
    ]
    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].fillna("SIN DATO").astype(str).str.strip().str.upper()

    num_cols = [
        "has",
        "suma_asegurada_usd",
        "suma_asegurada_helada_usd",
        "prima_usd",
        "st_pagado_usd",
        "rsp_usd",
        "hyg_usd",
        "siniestros_total_usd",
        "resultado_tecnico_usd",
        "tasa_prima_pct",
        "loss_cost_campania_pct",
        "loss_ratio_pct",
        "prima_por_ha_usd",
        "suma_asegurada_por_ha_usd",
        "siniestros_por_ha_usd",
        "share_suma_asegurada_pct",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    # Recalculo defensivo para que los indicadores siempre respondan a filtros.
    df["siniestros_total_usd"] = df[["st_pagado_usd", "rsp_usd", "hyg_usd"]].sum(axis=1)
    df["resultado_tecnico_usd"] = df["prima_usd"] - df["siniestros_total_usd"]
    df["siniestro_flag"] = df["siniestros_total_usd"] > 0
    return df


def fmt_usd(value: float) -> str:
    value = 0 if pd.isna(value) else float(value)
    abs_v = abs(value)
    sign = "-" if value < 0 else ""
    if abs_v >= 1_000_000:
        return f"{sign}USD {abs_v/1_000_000:,.1f} M"
    if abs_v >= 1_000:
        return f"{sign}USD {abs_v/1_000:,.0f} K"
    return f"{sign}USD {abs_v:,.0f}"


def fmt_num(value: float, decimals: int = 0) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{decimals}f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value) * 100:.{decimals}f}%"


def safe_ratio(num: float, den: float) -> float:
    den = float(den or 0)
    if den == 0:
        return 0.0
    return float(num) / den


def kpis(df: pd.DataFrame) -> dict[str, float]:
    suma = df["suma_asegurada_usd"].sum()
    prima = df["prima_usd"].sum()
    siniestros = df["siniestros_total_usd"].sum()
    has = df["has"].sum()
    return {
        "registros": len(df),
        "provincias": df["provincia"].nunique(),
        "departamentos": df["departamento"].nunique(),
        "cultivos": df["cultivo"].nunique(),
        "has": has,
        "suma_asegurada_usd": suma,
        "prima_usd": prima,
        "siniestros_total_usd": siniestros,
        "resultado_tecnico_usd": prima - siniestros,
        "tasa_prima": safe_ratio(prima, suma),
        "loss_cost": safe_ratio(siniestros, suma),
        "loss_ratio": safe_ratio(siniestros, prima),
        "prima_por_ha": safe_ratio(prima, has),
        "siniestros_por_ha": safe_ratio(siniestros, has),
    }


def aggregate(df: pd.DataFrame, by: Iterable[str]) -> pd.DataFrame:
    by = list(by)
    if not by:
        raise ValueError("Debe indicarse al menos una dimensión de agrupación")

    out = (
        df.groupby(by, dropna=False, as_index=False)
        .agg(
            registros=("registro_id", "count"),
            hectareas=("has", "sum"),
            suma_asegurada_usd=("suma_asegurada_usd", "sum"),
            suma_asegurada_helada_usd=("suma_asegurada_helada_usd", "sum"),
            prima_usd=("prima_usd", "sum"),
            st_pagado_usd=("st_pagado_usd", "sum"),
            rsp_usd=("rsp_usd", "sum"),
            hyg_usd=("hyg_usd", "sum"),
            siniestros_total_usd=("siniestros_total_usd", "sum"),
            casos_con_siniestro=("siniestro_flag", "sum"),
        )
        .sort_values("suma_asegurada_usd", ascending=False)
    )
    out["resultado_tecnico_usd"] = out["prima_usd"] - out["siniestros_total_usd"]
    out["loss_ratio"] = np.where(out["prima_usd"] > 0, out["siniestros_total_usd"] / out["prima_usd"], 0.0)
    out["loss_cost"] = np.where(out["suma_asegurada_usd"] > 0, out["siniestros_total_usd"] / out["suma_asegurada_usd"], 0.0)
    out["tasa_prima"] = np.where(out["suma_asegurada_usd"] > 0, out["prima_usd"] / out["suma_asegurada_usd"], 0.0)
    out["prima_por_ha"] = np.where(out["hectareas"] > 0, out["prima_usd"] / out["hectareas"], 0.0)
    out["share_suma"] = out["suma_asegurada_usd"] / max(out["suma_asegurada_usd"].sum(), 1)
    out["share_prima"] = out["prima_usd"] / max(out["prima_usd"].sum(), 1)
    out["share_siniestros"] = out["siniestros_total_usd"] / max(out["siniestros_total_usd"].sum(), 1)
    out["cum_share_suma"] = out["share_suma"].cumsum()
    return out


def metric_card(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def add_bar_labels(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        margin=dict(l=10, r=10, t=45, b=10),
        height=430,
        legend_title_text="",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,.08)")
    return fig


def business_commentary(k: dict[str, float]) -> str:
    lr = k["loss_ratio"]
    resultado = k["resultado_tecnico_usd"]
    if lr == 0:
        status = "la cartera filtrada no registra siniestros cargados."
    elif lr < 0.50:
        status = "el resultado técnico luce favorable, con siniestralidad contenida frente a la prima."
    elif lr < 0.80:
        status = "la siniestralidad es relevante pero todavía se mantiene en un rango manejable."
    elif lr < 1.00:
        status = "la cartera se acerca a una zona de equilibrio técnico y conviene revisar focos puntuales."
    else:
        status = "la cartera presenta resultado técnico negativo y requiere análisis de causas por zona/cultivo."

    return (
        f"Con los filtros actuales, {status} "
        f"El resultado técnico es {fmt_usd(resultado)} y el Loss Ratio agregado es {fmt_pct(lr)}."
    )


def style_table(df: pd.DataFrame) -> pd.DataFrame:
    cols_order = [
        c
        for c in [
            "provincia",
            "departamento",
            "cultivo",
            "cosecha",
            "cobertura",
            "registros",
            "hectareas",
            "suma_asegurada_usd",
            "prima_usd",
            "siniestros_total_usd",
            "resultado_tecnico_usd",
            "loss_ratio",
            "loss_cost",
            "tasa_prima",
            "share_suma",
            "casos_con_siniestro",
        ]
        if c in df.columns
    ]
    rest = [c for c in df.columns if c not in cols_order]
    return df[cols_order + rest]


def chart_metric_label(metric: str) -> str:
    return {
        "suma_asegurada_usd": "Suma asegurada",
        "prima_usd": "Prima",
        "siniestros_total_usd": "Siniestros",
        "resultado_tecnico_usd": "Resultado técnico",
        "loss_ratio": "Loss Ratio",
        "loss_cost": "Loss Cost",
        "tasa_prima": "Tasa de prima",
        "hectareas": "Hectáreas",
    }.get(metric, metric)


# -----------------------------
# Data + filtros
# -----------------------------
df_raw = load_data()

with st.sidebar:
    st.title("🌾 REA 25-26")
    st.caption("Dashboard visual de campaña")
    st.divider()

    cosecha_sel = st.multiselect(
        "Cosecha",
        options=sorted(df_raw["cosecha"].unique()),
        default=sorted(df_raw["cosecha"].unique()),
    )
    provincia_sel = st.multiselect(
        "Provincia",
        options=sorted(df_raw["provincia"].unique()),
        default=sorted(df_raw["provincia"].unique()),
    )
    cultivo_sel = st.multiselect(
        "Cultivo",
        options=sorted(df_raw["cultivo"].unique()),
        default=sorted(df_raw["cultivo"].unique()),
    )
    cobertura_sel = st.multiselect(
        "Cobertura",
        options=sorted(df_raw["cobertura"].unique()),
        default=sorted(df_raw["cobertura"].unique()),
    )

    st.divider()
    min_suma = float(df_raw["suma_asegurada_usd"].min())
    max_suma = float(df_raw["suma_asegurada_usd"].max())
    rango_suma = st.slider(
        "Rango de suma asegurada por registro",
        min_value=min_suma,
        max_value=max_suma,
        value=(min_suma, max_suma),
        step=max((max_suma - min_suma) / 100, 1.0),
        format="USD %.0f",
    )

    solo_siniestros = st.checkbox("Ver solo registros con siniestros", value=False)
    top_n = st.slider("Top N para rankings", 5, 30, 12, 1)


df = df_raw[
    df_raw["cosecha"].isin(cosecha_sel)
    & df_raw["provincia"].isin(provincia_sel)
    & df_raw["cultivo"].isin(cultivo_sel)
    & df_raw["cobertura"].isin(cobertura_sel)
    & df_raw["suma_asegurada_usd"].between(rango_suma[0], rango_suma[1])
].copy()
if solo_siniestros:
    df = df[df["siniestro_flag"]]

if df.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

k = kpis(df)

# -----------------------------
# Header
# -----------------------------
st.title("Dashboard de negocio | Campaña REA 25-26")
st.caption(
    "Informes visuales para analizar cúmulos por zonas, resultado por cosecha, cultivos y focos críticos de siniestralidad."
)

st.markdown(f"<div class='insight-box'>{business_commentary(k)}</div>", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    metric_card("Suma asegurada", fmt_usd(k["suma_asegurada_usd"]), f"{fmt_num(k['has'])} ha")
with c2:
    metric_card("Prima", fmt_usd(k["prima_usd"]), f"Tasa {fmt_pct(k['tasa_prima'])}")
with c3:
    metric_card("Siniestros", fmt_usd(k["siniestros_total_usd"]), f"Loss Cost {fmt_pct(k['loss_cost'])}")
with c4:
    metric_card("Resultado técnico", fmt_usd(k["resultado_tecnico_usd"]), "Prima - siniestros")
with c5:
    metric_card("Loss Ratio", fmt_pct(k["loss_ratio"]), f"{int(k['registros'])} registros")

# -----------------------------
# Tabs
# -----------------------------
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Resumen ejecutivo",
        "Cúmulos por zona",
        "Resultado por cosecha",
        "Cultivos",
        "Matriz zona-cultivo",
        "Alertas y detalle",
    ]
)

with tab0:
    st.markdown("<div class='section-title'>Composición general de la cartera</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1.15, 0.85])

    with col_a:
        prov = aggregate(df, ["provincia"]).head(top_n)
        fig = px.bar(
            prov.sort_values("suma_asegurada_usd"),
            x="suma_asegurada_usd",
            y="provincia",
            orientation="h",
            text="suma_asegurada_usd",
            title="Suma asegurada por provincia",
            labels={"suma_asegurada_usd": "Suma asegurada", "provincia": "Provincia"},
        )
        fig.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)

    with col_b:
        pie = aggregate(df, ["cultivo"])
        fig = px.pie(
            pie,
            names="cultivo",
            values="suma_asegurada_usd",
            title="Participación por cultivo",
            hole=0.48,
        )
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        sem = aggregate(df, ["cluster_negocio"])
        fig = px.bar(
            sem.sort_values("prima_usd"),
            x="prima_usd",
            y="cluster_negocio",
            orientation="h",
            title="Prima por cluster de negocio",
            labels={"prima_usd": "Prima", "cluster_negocio": "Cluster"},
        )
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)
    with col_d:
        cov = aggregate(df, ["cobertura"])
        fig = px.bar(
            cov,
            x="cobertura",
            y=["prima_usd", "siniestros_total_usd"],
            barmode="group",
            title="Prima vs siniestros por cobertura",
            labels={"value": "USD", "cobertura": "Cobertura", "variable": "Indicador"},
        )
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)

with tab1:
    st.markdown("<div class='section-title'>Cúmulos de exposición por zona</div>", unsafe_allow_html=True)
    dim_zona = st.radio(
        "Nivel de análisis",
        options=["provincia", "departamento", "provincia + departamento"],
        horizontal=True,
    )
    if dim_zona == "provincia":
        zona = aggregate(df, ["provincia"])
        zona["zona"] = zona["provincia"]
    elif dim_zona == "departamento":
        zona = aggregate(df, ["departamento"])
        zona["zona"] = zona["departamento"]
    else:
        zona = aggregate(df, ["provincia", "departamento"])
        zona["zona"] = zona["provincia"] + " | " + zona["departamento"]

    zona_top = zona.sort_values("suma_asegurada_usd", ascending=False).head(top_n).copy()

    col_a, col_b = st.columns([1.1, 0.9])
    with col_a:
        fig = px.bar(
            zona_top.sort_values("suma_asegurada_usd"),
            x="suma_asegurada_usd",
            y="zona",
            orientation="h",
            title=f"Top {top_n} zonas por suma asegurada",
            color="loss_ratio",
            color_continuous_scale="RdYlGn_r",
            labels={"suma_asegurada_usd": "Suma asegurada", "zona": "Zona", "loss_ratio": "Loss Ratio"},
        )
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)

    with col_b:
        pareto = zona.sort_values("suma_asegurada_usd", ascending=False).head(top_n).copy()
        fig = go.Figure()
        fig.add_bar(x=pareto["zona"], y=pareto["suma_asegurada_usd"], name="Suma asegurada")
        fig.add_scatter(
            x=pareto["zona"],
            y=pareto["cum_share_suma"],
            name="Share acumulado",
            yaxis="y2",
            mode="lines+markers",
        )
        fig.update_layout(
            title="Pareto de concentración",
            yaxis=dict(title="USD"),
            yaxis2=dict(title="Share acumulado", overlaying="y", side="right", tickformat=".0%", range=[0, 1.05]),
            xaxis_tickangle=-35,
            height=430,
            margin=dict(l=10, r=10, t=45, b=90),
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend_title_text="",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        style_table(zona_top),
        use_container_width=True,
        hide_index=True,
        column_config={
            "suma_asegurada_usd": st.column_config.NumberColumn("Suma asegurada", format="USD %.0f"),
            "prima_usd": st.column_config.NumberColumn("Prima", format="USD %.0f"),
            "siniestros_total_usd": st.column_config.NumberColumn("Siniestros", format="USD %.0f"),
            "resultado_tecnico_usd": st.column_config.NumberColumn("Resultado", format="USD %.0f"),
            "loss_ratio": st.column_config.NumberColumn("Loss Ratio", format="%.1%"),
            "loss_cost": st.column_config.NumberColumn("Loss Cost", format="%.2%"),
            "share_suma": st.column_config.NumberColumn("Share suma", format="%.1%"),
        },
    )

with tab2:
    st.markdown("<div class='section-title'>Resultado técnico por cosecha</div>", unsafe_allow_html=True)
    cosecha = aggregate(df, ["cosecha"]).sort_values("cosecha")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        fig = px.bar(
            cosecha,
            x="cosecha",
            y=["prima_usd", "siniestros_total_usd", "resultado_tecnico_usd"],
            barmode="group",
            title="Prima, siniestros y resultado por cosecha",
            labels={"value": "USD", "cosecha": "Cosecha", "variable": "Indicador"},
        )
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)
    with col_b:
        fig = px.line(
            cosecha,
            x="cosecha",
            y=["loss_ratio", "loss_cost", "tasa_prima"],
            markers=True,
            title="Indicadores técnicos por cosecha",
            labels={"value": "Ratio", "cosecha": "Cosecha", "variable": "Indicador"},
        )
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)

    st.dataframe(
        style_table(cosecha),
        use_container_width=True,
        hide_index=True,
        column_config={
            "hectareas": st.column_config.NumberColumn("Hectáreas", format="%.0f"),
            "suma_asegurada_usd": st.column_config.NumberColumn("Suma asegurada", format="USD %.0f"),
            "prima_usd": st.column_config.NumberColumn("Prima", format="USD %.0f"),
            "siniestros_total_usd": st.column_config.NumberColumn("Siniestros", format="USD %.0f"),
            "resultado_tecnico_usd": st.column_config.NumberColumn("Resultado", format="USD %.0f"),
            "loss_ratio": st.column_config.NumberColumn("Loss Ratio", format="%.1%"),
            "loss_cost": st.column_config.NumberColumn("Loss Cost", format="%.2%"),
            "tasa_prima": st.column_config.NumberColumn("Tasa prima", format="%.2%"),
        },
    )

with tab3:
    st.markdown("<div class='section-title'>Lectura por cultivo</div>", unsafe_allow_html=True)
    cult = aggregate(df, ["cultivo"]).sort_values("suma_asegurada_usd", ascending=False)

    col_a, col_b = st.columns([1.1, 0.9])
    with col_a:
        metric_for_chart = st.selectbox(
            "Métrica para ranking de cultivos",
            options=["suma_asegurada_usd", "prima_usd", "siniestros_total_usd", "resultado_tecnico_usd", "hectareas"],
            format_func=chart_metric_label,
        )
        fig = px.bar(
            cult.head(top_n).sort_values(metric_for_chart),
            x=metric_for_chart,
            y="cultivo",
            orientation="h",
            title=f"Top cultivos por {chart_metric_label(metric_for_chart)}",
            color="loss_ratio",
            color_continuous_scale="RdYlGn_r",
            labels={metric_for_chart: chart_metric_label(metric_for_chart), "cultivo": "Cultivo", "loss_ratio": "Loss Ratio"},
        )
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)

    with col_b:
        fig = px.scatter(
            cult,
            x="tasa_prima",
            y="loss_cost",
            size="suma_asegurada_usd",
            color="loss_ratio",
            hover_name="cultivo",
            color_continuous_scale="RdYlGn_r",
            title="Tasa vs Loss Cost por cultivo",
            labels={"tasa_prima": "Tasa prima", "loss_cost": "Loss Cost", "loss_ratio": "Loss Ratio"},
        )
        fig.update_xaxes(tickformat=".1%")
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)

    st.dataframe(
        style_table(cult),
        use_container_width=True,
        hide_index=True,
        column_config={
            "hectareas": st.column_config.NumberColumn("Hectáreas", format="%.0f"),
            "suma_asegurada_usd": st.column_config.NumberColumn("Suma asegurada", format="USD %.0f"),
            "prima_usd": st.column_config.NumberColumn("Prima", format="USD %.0f"),
            "siniestros_total_usd": st.column_config.NumberColumn("Siniestros", format="USD %.0f"),
            "resultado_tecnico_usd": st.column_config.NumberColumn("Resultado", format="USD %.0f"),
            "loss_ratio": st.column_config.NumberColumn("Loss Ratio", format="%.1%"),
            "loss_cost": st.column_config.NumberColumn("Loss Cost", format="%.2%"),
            "tasa_prima": st.column_config.NumberColumn("Tasa prima", format="%.2%"),
        },
    )

with tab4:
    st.markdown("<div class='section-title'>Matriz zona-cultivo</div>", unsafe_allow_html=True)
    col_f1, col_f2 = st.columns([0.5, 0.5])
    with col_f1:
        zona_dim = st.selectbox("Dimensión zona", ["provincia", "departamento"], index=0)
    with col_f2:
        heat_metric = st.selectbox(
            "Métrica del color",
            ["suma_asegurada_usd", "prima_usd", "siniestros_total_usd", "resultado_tecnico_usd", "loss_ratio", "loss_cost", "tasa_prima"],
            index=4,
            format_func=chart_metric_label,
        )

    mat = aggregate(df, [zona_dim, "cultivo"])
    if heat_metric in ["loss_ratio", "loss_cost", "tasa_prima"]:
        values = mat.pivot(index=zona_dim, columns="cultivo", values=heat_metric).fillna(0)
    else:
        values = mat.pivot(index=zona_dim, columns="cultivo", values=heat_metric).fillna(0)

    # Ordena por exposición total de la zona para que la matriz tenga lectura de negocio.
    order_zones = aggregate(df, [zona_dim]).sort_values("suma_asegurada_usd", ascending=False)[zona_dim].tolist()
    values = values.reindex([z for z in order_zones if z in values.index])
    if len(values) > 25:
        values = values.head(25)

    fig = px.imshow(
        values,
        aspect="auto",
        text_auto=False,
        color_continuous_scale="RdYlGn_r" if heat_metric in ["loss_ratio", "loss_cost"] else "Blues",
        title=f"Heatmap {chart_metric_label(heat_metric)} por {zona_dim} y cultivo",
        labels=dict(x="Cultivo", y=zona_dim.title(), color=chart_metric_label(heat_metric)),
    )
    if heat_metric in ["loss_ratio", "loss_cost", "tasa_prima"]:
        fig.update_coloraxes(colorbar_tickformat=".1%")
    fig.update_layout(height=max(460, 24 * len(values)), margin=dict(l=10, r=10, t=45, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("Tip: usar Loss Ratio para detectar zonas/cultivos con peor resultado; usar suma asegurada para detectar cúmulos de exposición.")

with tab5:
    st.markdown("<div class='section-title'>Alertas de negocio y detalle descargable</div>", unsafe_allow_html=True)

    base_alertas = aggregate(df, ["provincia", "departamento", "cultivo", "cosecha"])
    # Score simple: prioriza alta exposición, LR alto y resultado negativo.
    base_alertas["score_alerta"] = (
        base_alertas["share_suma"].rank(pct=True).fillna(0) * 0.35
        + base_alertas["loss_ratio"].clip(0, 3).rank(pct=True).fillna(0) * 0.35
        + (base_alertas["resultado_tecnico_usd"] < 0).astype(float) * 0.30
    )
    base_alertas["motivo_alerta"] = np.select(
        [
            (base_alertas["resultado_tecnico_usd"] < 0) & (base_alertas["loss_ratio"] >= 1),
            (base_alertas["loss_ratio"] >= 0.8),
            (base_alertas["share_suma"] >= 0.05),
            (base_alertas["siniestros_total_usd"] > 0),
        ],
        [
            "Resultado negativo",
            "Loss Ratio elevado",
            "Alta concentración",
            "Con siniestros",
        ],
        default="Seguimiento",
    )
    alertas = base_alertas.sort_values("score_alerta", ascending=False).head(max(top_n, 10))

    col_a, col_b = st.columns([1, 1])
    with col_a:
        fig = px.bar(
            alertas.sort_values("score_alerta"),
            x="score_alerta",
            y=alertas["provincia"] + " | " + alertas["departamento"] + " | " + alertas["cultivo"],
            orientation="h",
            color="motivo_alerta",
            title="Ranking de focos a revisar",
            labels={"score_alerta": "Score alerta", "y": "Zona / cultivo"},
        )
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)
    with col_b:
        fig = px.scatter(
            base_alertas,
            x="suma_asegurada_usd",
            y="loss_ratio",
            size="prima_usd",
            color="resultado_tecnico_usd",
            hover_name="departamento",
            hover_data=["provincia", "cultivo", "cosecha", "prima_usd", "siniestros_total_usd"],
            color_continuous_scale="RdYlGn",
            title="Exposición vs Loss Ratio",
            labels={"suma_asegurada_usd": "Suma asegurada", "loss_ratio": "Loss Ratio"},
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(add_bar_labels(fig), use_container_width=True)

    st.dataframe(
        style_table(alertas),
        use_container_width=True,
        hide_index=True,
        column_config={
            "suma_asegurada_usd": st.column_config.NumberColumn("Suma asegurada", format="USD %.0f"),
            "prima_usd": st.column_config.NumberColumn("Prima", format="USD %.0f"),
            "siniestros_total_usd": st.column_config.NumberColumn("Siniestros", format="USD %.0f"),
            "resultado_tecnico_usd": st.column_config.NumberColumn("Resultado", format="USD %.0f"),
            "loss_ratio": st.column_config.NumberColumn("Loss Ratio", format="%.1%"),
            "loss_cost": st.column_config.NumberColumn("Loss Cost", format="%.2%"),
            "share_suma": st.column_config.NumberColumn("Share suma", format="%.1%"),
            "score_alerta": st.column_config.ProgressColumn("Score alerta", format="%.2f", min_value=0, max_value=1),
        },
    )

    st.download_button(
        "Descargar alertas filtradas CSV",
        data=alertas.to_csv(index=False).encode("utf-8"),
        file_name="alertas_negocio_rea_25_26.csv",
        mime="text/csv",
    )

    st.markdown("<div class='section-title'>Base filtrada</div>", unsafe_allow_html=True)
    st.dataframe(
        df.sort_values("suma_asegurada_usd", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "suma_asegurada_usd": st.column_config.NumberColumn("Suma asegurada", format="USD %.0f"),
            "prima_usd": st.column_config.NumberColumn("Prima", format="USD %.0f"),
            "siniestros_total_usd": st.column_config.NumberColumn("Siniestros", format="USD %.0f"),
            "resultado_tecnico_usd": st.column_config.NumberColumn("Resultado", format="USD %.0f"),
            "loss_ratio_pct": st.column_config.NumberColumn("Loss Ratio", format="%.1%"),
            "loss_cost_campania_pct": st.column_config.NumberColumn("Loss Cost", format="%.2%"),
        },
    )
    st.download_button(
        "Descargar base filtrada CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="base_filtrada_rea_25_26.csv",
        mime="text/csv",
    )
