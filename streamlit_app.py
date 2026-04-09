# ══════════════════════════════════════════════
# MCPs PERÚ — DASHBOARD FINAL PRO
# ══════════════════════════════════════════════

import os
import zipfile
import tempfile
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px

from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout="wide")

# ══════════════════════════════════════════════
# CARGA
# ══════════════════════════════════════════════
BASE = os.path.dirname(__file__)
PADRON_PATH = os.path.join(BASE, "ELECTORES_POR_MCP.xlsx")

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
# SIDEBAR FILTROS BASE
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

total_mcp = len(df_f)
total_e = int(df_f["CANTIDAD DE ELECTORES"].sum())
total_dist = df_f["DISTRITO"].nunique()

kpis = [
    ("MCPs", f"{total_mcp:,}"),
    ("Electores", f"{total_e:,}"),
    ("Distritos", f"{total_dist:,}")
]

cols = st.columns(len(kpis))
for col, (label, value) in zip(cols, kpis):
    col.metric(label, value)

# ══════════════════════════════════════════════
# MAPA + BARRAS
# ══════════════════════════════════════════════
col1, col2 = st.columns([2,1])

with col1:
    st.markdown("## 🗺️ Mapa")

    MAP_PATH = os.path.join(BASE, "mapa_distrito.zip")

    if os.path.exists(MAP_PATH):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(MAP_PATH) as z:
                z.extractall(tmp)

            html = [f for f in os.listdir(tmp) if f.endswith(".html")][0]
            with open(os.path.join(tmp, html), "r", encoding="utf-8") as f:
                components.html(f.read(), height=500)

with col2:
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
        orientation="h"
    )

    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# 🔥 FILTRO JERÁRQUICO INTERACTIVO (LO QUE PEDISTE)
# ══════════════════════════════════════════════
st.markdown("## 🔎 Exploración jerárquica")

colA, colB, colC, colD = st.columns(4)

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

df_lvl3 = df_lvl2[df_lvl2["DISTRITO"] == sel_dist]

with colD:
    sel_mcp = st.selectbox(
        "MCP",
        sorted(df_lvl3["MCP"].unique())
    )

df_final = df_lvl3[df_lvl3["MCP"] == sel_mcp]

st.dataframe(df_final)

st.metric(
    "Electores en MCP seleccionado",
    int(df_final["CANTIDAD DE ELECTORES"].sum())
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
)

st.dataframe(table_df, height=400)

# ══════════════════════════════════════════════
# 🌳 TABLA ÁRBOL REAL (CORREGIDA)
# ══════════════════════════════════════════════
st.markdown("## 🌳 Tabla expandible")

tree_df = table_df.copy()

tree_df["path"] = tree_df.apply(
    lambda x: [x["DEPARTAMENTO"], x["PROVINCIA"], x["DISTRITO"], str(x["MCP"])],
    axis=1
)

gridOptions = {
    "treeData": True,
    "animateRows": True,
    "groupDefaultExpanded": 1,
    "getDataPath": {"function": "function(data){return data.path;}"},
    "autoGroupColumnDef": {
        "headerName": "Ubicación",
        "cellRendererParams": {"suppressCount": True}
    }
}

AgGrid(
    tree_df,
    gridOptions=gridOptions,
    height=500,
    fit_columns_on_grid_load=True,
    enable_enterprise_modules=True
)
