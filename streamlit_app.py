# ══════════════════════════════════════════════
# DASHBOARD MCPs PERÚ — VERSIÓN LIMPIA
# ══════════════════════════════════════════════

import os
import zipfile
import tempfile

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px

# 🔥 NUEVO
from st_aggrid import AgGrid, GridOptionsBuilder

# ══════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="MCPs Perú — Dashboard Electoral",
    layout="wide"
)

# ══════════════════════════════════════════════
# ESTILOS KPI
# ══════════════════════════════════════════════
st.markdown("""
<style>
.kpi-card {
    background:#161b22;
    border:1px solid #30363d;
    border-radius:10px;
    padding:16px;
    text-align:center;
}
.kpi-value { font-size:26px; font-weight:800; color:white; }
.kpi-label { font-size:11px; color:#8b949e; }
</style>
""", unsafe_allow_html=True)

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
# SIDEBAR FILTROS
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
total_mcp = len(df_f)
total_e = int(df_f["CANTIDAD DE ELECTORES"].sum())
total_dist = df_f["DISTRITO"].nunique()

kpis = [
    ("Total MCPs", f"{total_mcp:,}"),
    ("Total Electores", f"{total_e:,}"),
    ("Distritos", f"{total_dist:,}")
]

cols = st.columns(len(kpis))

for col, (label, value) in zip(cols, kpis):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# MAPA (igual que el tuyo)
# ══════════════════════════════════════════════
st.markdown("## 🗺️ Mapa")

MAP_PATH = os.path.join(BASE, "mapa_distrito.zip")

if os.path.exists(MAP_PATH):
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(MAP_PATH) as z:
            z.extractall(tmp)

        html = [f for f in os.listdir(tmp) if f.endswith(".html")][0]
        with open(os.path.join(tmp, html), "r", encoding="utf-8") as f:
            components.html(f.read(), height=500)

# ══════════════════════════════════════════════
# GRÁFICO CLAVE
# ══════════════════════════════════════════════
st.markdown("## 📊 Electores por Distrito")

dist_plot = (
    df_f.groupby(["PROVINCIA","DISTRITO"])["CANTIDAD DE ELECTORES"]
    .sum()
    .reset_index()
    .sort_values("CANTIDAD DE ELECTORES", ascending=False)
    .head(20)
)

dist_plot["LABEL"] = dist_plot["DISTRITO"] + " (" + dist_plot["PROVINCIA"] + ")"

fig = px.bar(
    dist_plot.sort_values("CANTIDAD DE ELECTORES"),
    x="CANTIDAD DE ELECTORES",
    y="LABEL",
    orientation="h",
    text="CANTIDAD DE ELECTORES"
)

st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# TABLA JERÁRQUICA SIMPLE
# ══════════════════════════════════════════════
st.markdown("## 📋 Tabla jerárquica")

table_df = (
    df_f.groupby(
        ["DEPARTAMENTO","PROVINCIA","DISTRITO","MCP"]
    )["CANTIDAD DE ELECTORES"]
    .sum()
    .reset_index()
)

st.dataframe(table_df, use_container_width=True, height=400)

# ══════════════════════════════════════════════
# 🔥 TABLA ÁRBOL EXPANDIBLE (AGGRID)
# ══════════════════════════════════════════════
st.markdown("## 🌳 Tabla expandible (árbol)")

gb = GridOptionsBuilder.from_dataframe(table_df)

gb.configure_column("DEPARTAMENTO", rowGroup=True)
gb.configure_column("PROVINCIA", rowGroup=True)
gb.configure_column("DISTRITO", rowGroup=True)
gb.configure_column("MCP", rowGroup=True)

gb.configure_default_column(groupable=True)

gridOptions = gb.build()

AgGrid(
    table_df,
    gridOptions=gridOptions,
    enable_enterprise_modules=True,
    fit_columns_on_grid_load=True,
    height=500
)
