# ══════════════════════════════════════════════
# MCPs PERÚ — DASHBOARD FINAL LIMPIO
# ══════════════════════════════════════════════

import os
import zipfile
import tempfile
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

# ══════════════════════════════════════════════
# CARGA
# ══════════════════════════════════════════════
BASE = os.path.dirname(__file__)
PADRON_PATH = os.path.join(BASE, "ELECTORES_POR_MCP.xlsx")
MAP_PATH = os.path.join(BASE, "mapa_final.zip")

@st.cache_data
def load_data():
    df = pd.read_excel(PADRON_PATH)
    df.columns = df.columns.str.upper().str.strip()
    df["CANTIDAD DE ELECTORES"] = pd.to_numeric(
        df["CANTIDAD DE ELECTORES"], errors="coerce"
    ).fillna(0)
    return df

df = load_data()

# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.title("Filtros")

    dept = st.selectbox("Departamento", ["Todos"] + sorted(df["DEPARTAMENTO"].unique()))
    df_f = df if dept == "Todos" else df[df["DEPARTAMENTO"] == dept]

    prov = st.selectbox("Provincia", ["Todas"] + sorted(df_f["PROVINCIA"].unique()))
    df_f = df_f if prov == "Todas" else df_f[df_f["PROVINCIA"] == prov]

    dist = st.selectbox("Distrito", ["Todos"] + sorted(df_f["DISTRITO"].unique()))
    df_f = df_f if dist == "Todos" else df_f[df_f["DISTRITO"] == dist]

# ══════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════
st.markdown("## 📊 Indicadores")

col1, col2, col3 = st.columns(3)

col1.metric("MCPs", len(df_f))
col2.metric("Electores", int(df_f["CANTIDAD DE ELECTORES"].sum()))
col3.metric("Distritos", df_f["DISTRITO"].nunique())

# ══════════════════════════════════════════════
# MAPA + BARRAS
# ══════════════════════════════════════════════
col_map, col_bar = st.columns([2,1])

# ── MAPA ─────────────────────────────
with col_map:
    st.markdown("## 🗺️ Mapa distrital")

    if os.path.exists(MAP_PATH):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(MAP_PATH) as z:
                z.extractall(tmp)

            html_file = [f for f in os.listdir(tmp) if f.endswith(".html")][0]

            with open(os.path.join(tmp, html_file), "r", encoding="utf-8") as f:
                components.html(f.read(), height=520)

    else:
        st.warning("No se encontró el mapa zip.")

# ── BARRAS ───────────────────────────
with col_bar:
    st.markdown("## 📊 Electores por distrito")

    dist_plot = (
        df_f.groupby(["PROVINCIA","DISTRITO"])["CANTIDAD DE ELECTORES"]
        .sum()
        .reset_index()
        .sort_values("CANTIDAD DE ELECTORES", ascending=False)
        .head(15)
    )

    dist_plot["LABEL"] = dist_plot["DISTRITO"] + " (" + dist_plot["PROVINCIA"] + ")"

    fig = px.bar(
        dist_plot.sort_values("CANTIDAD DE ELECTORES"),
        x="CANTIDAD DE ELECTORES",
        y="LABEL",
        orientation="h",
        text="CANTIDAD DE ELECTORES"
    )

    fig.update_traces(texttemplate="%{text:,}", textposition="outside")

    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# EXPLORACIÓN JERÁRQUICA
# ══════════════════════════════════════════════
st.markdown("## 🔎 Buscador por distrito")

colA, colB, colC = st.columns(3)

with colA:
    sel_dept = st.selectbox(
        "Departamento",
        sorted(df_f["DEPARTAMENTO"].unique())
    )

df_lvl1 = df_f[df_f["DEPARTAMENTO"] == sel_dept]

with colB:
    sel_prov = st.selectbox(
        "Provincia",
        sorted(df_lvl1["PROVINCIA"].unique())
    )

df_lvl2 = df_lvl1[df_lvl1["PROVINCIA"] == sel_prov]

with colC:
    sel_dist = st.selectbox(
        "Distrito",
        sorted(df_lvl2["DISTRITO"].unique())
    )

df_final = df_lvl2[df_lvl2["DISTRITO"] == sel_dist]

# resultado
resultado = (
    df_final.groupby(
        ["DEPARTAMENTO","PROVINCIA","DISTRITO","MCP"]
    )["CANTIDAD DE ELECTORES"]
    .sum()
    .reset_index()
)

st.dataframe(resultado, use_container_width=True)

st.metric(
    "Electores en distrito seleccionado",
    int(resultado["CANTIDAD DE ELECTORES"].sum())
)

# ══════════════════════════════════════════════
# TABLA GENERAL
# ══════════════════════════════════════════════
st.markdown("## 📋 Tabla general")

table_df = (
    df_f.groupby(
        ["DEPARTAMENTO","PROVINCIA","DISTRITO","MCP"]
    )["CANTIDAD DE ELECTORES"]
    .sum()
    .reset_index()
    .sort_values("CANTIDAD DE ELECTORES", ascending=False)
)

st.dataframe(table_df, height=400, use_container_width=True)
