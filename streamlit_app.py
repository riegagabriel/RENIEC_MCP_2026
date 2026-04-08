"""
Dashboard Electoral Perú 2025
Padrón de Mesas de Centro de Votación (MCPs) por distrito
Requiere: streamlit, pandas, geopandas, plotly, requests, openpyxl
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import requests
import zipfile
import io
import os
import tempfile

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Electoral Perú",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILOS CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #e63946;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-label {
        color: #adb5bd;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        color: #f1faee;
        font-size: 28px;
        font-weight: 800;
        margin: 4px 0;
    }
    .metric-sub {
        color: #e63946;
        font-size: 12px;
    }
    .title-bar {
        background: linear-gradient(90deg, #e63946, #c1121f);
        border-radius: 8px;
        padding: 14px 24px;
        margin-bottom: 20px;
    }
    .section-header {
        border-left: 4px solid #e63946;
        padding-left: 10px;
        margin: 20px 0 10px 0;
        font-weight: 700;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

GITHUB_RAW = "https://raw.githubusercontent.com/riegagabriel/SHAPEFILES_PERU_2025/main/"

# Nombres posibles de los archivos ZIP en tu repo
# Ajusta estos nombres si difieren en tu repositorio
SHP_URLS = {
    "distrito": GITHUB_RAW + "DISTRITO.zip",
    "provincia": GITHUB_RAW + "PROVINCIA.zip",
    "departamento": GITHUB_RAW + "DEPARTAMENTO.zip",
}

@st.cache_data(show_spinner=False)
def load_shapefile(url: str) -> gpd.GeoDataFrame:
    """Descarga y lee un shapefile desde un ZIP remoto."""
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            z.extractall(tmpdir)
        shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
        if not shp_files:
            raise FileNotFoundError("No se encontró .shp en el ZIP")
        gdf = gpd.read_file(os.path.join(tmpdir, shp_files[0]))
    return gdf.to_crs(epsg=4326)


@st.cache_data(show_spinner=False)
def load_data():
    """Carga el CSV/Excel del padrón. Ajusta la ruta si usas archivo local."""
    # ── OPCIÓN A: subir el archivo desde la app ──
    # (se maneja con file_uploader más abajo)
    return None


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗳️ Dashboard Electoral")
    st.markdown("**Padrón MCP – Perú 2025**")
    st.divider()

    uploaded = st.file_uploader(
        "📂 Cargar padrón (CSV / Excel)",
        type=["csv", "xlsx", "xls"],
    )

    st.divider()
    st.markdown("### 🗺️ Shapefiles")
    nivel_mapa = st.selectbox(
        "Nivel geográfico del mapa",
        ["Distrito", "Provincia", "Departamento"],
    )

    st.divider()
    st.markdown("### 🎨 Visualización")
    color_scale = st.selectbox(
        "Escala de color",
        ["Reds", "YlOrRd", "Blues", "Viridis", "Plasma"],
    )
    top_n = st.slider("Top N en gráficos de barras", 10, 30, 15)

# ─────────────────────────────────────────────
# CARGA DEL PADRÓN
# ─────────────────────────────────────────────
if uploaded is None:
    st.markdown("""
    <div class="title-bar">
        <h2 style='color:white;margin:0'>🗳️ Dashboard Electoral — Padrón MCP Perú</h2>
        <p style='color:#ffd6d6;margin:4px 0 0 0;font-size:14px'>
            Carga el archivo del padrón en la barra lateral para comenzar
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.info("👈 Sube el archivo CSV o Excel del padrón desde el panel lateral.")
    st.stop()

# Leer archivo
if uploaded.name.endswith(".csv"):
    df = pd.read_csv(uploaded)
else:
    df = pd.read_excel(uploaded)

# Normalización de columnas (mayúsculas, sin espacios extra)
df.columns = df.columns.str.strip().str.upper()

# Validar columnas mínimas
required_cols = {"DEPARTAMENTO", "PROVINCIA", "DISTRITO", "MCP", "CANTIDAD DE ELECTORES"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Faltan columnas: {missing}")
    st.stop()

df["CANTIDAD DE ELECTORES"] = pd.to_numeric(df["CANTIDAD DE ELECTORES"], errors="coerce").fillna(0).astype(int)

# ─────────────────────────────────────────────
# FILTROS EN SIDEBAR (cascada)
# ─────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.markdown("### 🔍 Filtros")

    depts = ["Todos"] + sorted(df["DEPARTAMENTO"].unique().tolist())
    sel_dept = st.selectbox("Departamento", depts)

    df_f = df if sel_dept == "Todos" else df[df["DEPARTAMENTO"] == sel_dept]

    provs = ["Todas"] + sorted(df_f["PROVINCIA"].unique().tolist())
    sel_prov = st.selectbox("Provincia", provs)

    df_f = df_f if sel_prov == "Todas" else df_f[df_f["PROVINCIA"] == sel_prov]

    dists = ["Todos"] + sorted(df_f["DISTRITO"].unique().tolist())
    sel_dist = st.selectbox("Distrito", dists)

    df_f = df_f if sel_dist == "Todos" else df_f[df_f["DISTRITO"] == sel_dist]

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
scope_label = " › ".join(filter(lambda x: x not in ("Todos", "Todas"),
                                 [sel_dept, sel_prov, sel_dist])) or "Nacional"
st.markdown(f"""
<div class="title-bar">
    <h2 style='color:white;margin:0'>🗳️ Dashboard Electoral — Padrón MCP Perú</h2>
    <p style='color:#ffd6d6;margin:4px 0 0 0;font-size:14px'>Alcance: {scope_label}</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
total_electores = df_f["CANTIDAD DE ELECTORES"].sum()
total_mcps      = len(df_f)
total_distritos = df_f["DISTRITO"].nunique()
total_provs     = df_f["PROVINCIA"].nunique()
avg_x_mcp       = int(df_f["CANTIDAD DE ELECTORES"].mean()) if total_mcps > 0 else 0
max_row         = df_f.loc[df_f["CANTIDAD DE ELECTORES"].idxmax()] if total_mcps > 0 else None

cols_kpi = st.columns(5)
kpis = [
    ("Total Electores",  f"{total_electores:,}", "padrón filtrado"),
    ("MCPs",             f"{total_mcps:,}",      "centros de votación"),
    ("Distritos",        f"{total_distritos:,}", "con al menos 1 MCP"),
    ("Provincias",       f"{total_provs:,}",     "cubiertas"),
    ("Electores/MCP",    f"{avg_x_mcp:,}",       "promedio"),
]
for col, (label, val, sub) in zip(cols_kpi, kpis):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{val}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# AGGREGACIONES
# ─────────────────────────────────────────────
by_dept = (df_f.groupby("DEPARTAMENTO")
               .agg(ELECTORES=("CANTIDAD DE ELECTORES","sum"),
                    MCPS=("MCP","count"))
               .reset_index()
               .sort_values("ELECTORES", ascending=False))

by_prov = (df_f.groupby(["DEPARTAMENTO","PROVINCIA"])
               .agg(ELECTORES=("CANTIDAD DE ELECTORES","sum"),
                    MCPS=("MCP","count"))
               .reset_index()
               .sort_values("ELECTORES", ascending=False))

by_dist = (df_f.groupby(["DEPARTAMENTO","PROVINCIA","DISTRITO"])
               .agg(ELECTORES=("CANTIDAD DE ELECTORES","sum"),
                    MCPS=("MCP","count"))
               .reset_index()
               .sort_values("ELECTORES", ascending=False))

# ─────────────────────────────────────────────
# FILA 1: MAPA + BARRAS DEPARTAMENTOS
# ─────────────────────────────────────────────
col_map, col_bar = st.columns([3, 2], gap="medium")

with col_bar:
    st.markdown('<div class="section-header">Top Departamentos por Electores</div>', unsafe_allow_html=True)
    fig_bar = px.bar(
        by_dept.head(top_n),
        x="ELECTORES", y="DEPARTAMENTO",
        orientation="h",
        color="ELECTORES",
        color_continuous_scale=color_scale,
        text="ELECTORES",
        labels={"ELECTORES":"Electores","DEPARTAMENTO":""},
    )
    fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1faee",
        coloraxis_showscale=False,
        margin=dict(l=0,r=60,t=10,b=10),
        height=420,
        yaxis={"categoryorder":"total ascending"},
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_map:
    st.markdown('<div class="section-header">🗺️ Mapa Coroplético</div>', unsafe_allow_html=True)

    shp_key = nivel_mapa.lower()
    shp_url = SHP_URLS[shp_key]

    with st.spinner(f"Descargando shapefile de {nivel_mapa.lower()}s..."):
        try:
            gdf = load_shapefile(shp_url)

            # Detectar columna de nombre en el shapefile
            name_col_candidates = {
                "distrito":    ["DISTRITO","NOMBDIST","NOMBDIST","NOM_DIST"],
                "provincia":   ["PROVINCIA","NOMBPROV","NOM_PROV"],
                "departamento":["DEPARTAMENTO","NOMBDEP","NOM_DEP"],
            }
            candidates = name_col_candidates[shp_key]
            shp_name_col = next((c for c in candidates if c in gdf.columns), gdf.columns[0])

            # Elegir la tabla de aggregación correcta
            if shp_key == "departamento":
                agg_df = by_dept.rename(columns={"DEPARTAMENTO": shp_name_col})
            elif shp_key == "provincia":
                agg_df = by_prov.rename(columns={"PROVINCIA": shp_name_col})
            else:
                agg_df = by_dist.rename(columns={"DISTRITO": shp_name_col})

            # Normalizar texto para el join
            gdf[shp_name_col] = gdf[shp_name_col].str.upper().str.strip()
            agg_df[shp_name_col] = agg_df[shp_name_col].str.upper().str.strip()

            merged = gdf.merge(agg_df[[shp_name_col,"ELECTORES","MCPS"]],
                               on=shp_name_col, how="left")
            merged["ELECTORES"] = merged["ELECTORES"].fillna(0)
            merged["MCPS"]      = merged["MCPS"].fillna(0)

            # Calcular centroide para hover
            merged["lon"] = merged.geometry.centroid.x
            merged["lat"] = merged.geometry.centroid.y

            fig_map = px.choropleth_map(
                merged,
                geojson=merged.__geo_interface__,
                locations=merged.index,
                color="ELECTORES",
                color_continuous_scale=color_scale,
                hover_name=shp_name_col,
                hover_data={"ELECTORES": ":,", "MCPS": True},
                labels={"ELECTORES": "Electores", "MCPS": "N° MCPs"},
                center={"lat": -9.19, "lon": -75.0},
                zoom=4,
                opacity=0.75,
            )
            fig_map.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#f1faee",
                margin=dict(l=0,r=0,t=0,b=0),
                height=420,
                coloraxis_colorbar=dict(title="Electores"),
                map_style="carto-darkmatter",
            )
            st.plotly_chart(fig_map, use_container_width=True)

        except Exception as e:
            st.warning(f"⚠️ No se pudo cargar el shapefile: {e}\n\n"
                       f"Verifica que los archivos ZIP en tu repo se llamen "
                       f"`DISTRITO.zip`, `PROVINCIA.zip`, `DEPARTAMENTO.zip`.")

# ─────────────────────────────────────────────
# FILA 2: TREEMAP + DISTRIBUCIÓN MCPs
# ─────────────────────────────────────────────
st.markdown('<div class="section-header">Análisis por Provincia y Distrito</div>', unsafe_allow_html=True)
col_tree, col_hist = st.columns([2, 1], gap="medium")

with col_tree:
    df_tree = df_f.groupby(["DEPARTAMENTO","PROVINCIA","DISTRITO"]) \
                  .agg(ELECTORES=("CANTIDAD DE ELECTORES","sum")).reset_index()
    fig_tree = px.treemap(
        df_tree,
        path=["DEPARTAMENTO","PROVINCIA","DISTRITO"],
        values="ELECTORES",
        color="ELECTORES",
        color_continuous_scale=color_scale,
        title="Electores: Departamento → Provincia → Distrito",
    )
    fig_tree.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#f1faee",
        margin=dict(l=0,r=0,t=40,b=0),
        height=380,
    )
    st.plotly_chart(fig_tree, use_container_width=True)

with col_hist:
    fig_hist = px.histogram(
        df_f,
        x="CANTIDAD DE ELECTORES",
        nbins=40,
        color_discrete_sequence=["#e63946"],
        title="Distribución de tamaño de MCPs",
        labels={"CANTIDAD DE ELECTORES": "Electores por MCP", "count": "N° MCPs"},
    )
    fig_hist.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1faee",
        margin=dict(l=0,r=0,t=40,b=0),
        height=380,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ─────────────────────────────────────────────
# FILA 3: TOP DISTRITOS + SCATTER
# ─────────────────────────────────────────────
col_top, col_scatter = st.columns([1, 1], gap="medium")

with col_top:
    st.markdown(f'<div class="section-header">Top {top_n} Distritos por Electores</div>',
                unsafe_allow_html=True)
    top_dist = by_dist.head(top_n).copy()
    top_dist["LABEL"] = top_dist["DISTRITO"] + " (" + top_dist["PROVINCIA"] + ")"
    fig_dist = px.bar(
        top_dist,
        x="ELECTORES", y="LABEL",
        orientation="h",
        color="ELECTORES",
        color_continuous_scale=color_scale,
        text="ELECTORES",
    )
    fig_dist.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_dist.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1faee",
        coloraxis_showscale=False,
        margin=dict(l=0,r=60,t=10,b=10),
        height=400,
        yaxis={"categoryorder":"total ascending", "title":""},
        xaxis_title="Electores",
    )
    st.plotly_chart(fig_dist, use_container_width=True)

with col_scatter:
    st.markdown('<div class="section-header">MCPs vs Electores por Distrito</div>',
                unsafe_allow_html=True)
    fig_scat = px.scatter(
        by_dist,
        x="MCPS", y="ELECTORES",
        color="DEPARTAMENTO",
        hover_name="DISTRITO",
        hover_data={"PROVINCIA": True, "ELECTORES": ":,", "MCPS": True},
        labels={"MCPS": "N° de MCPs", "ELECTORES": "Total Electores"},
        title="",
    )
    fig_scat.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1faee",
        legend=dict(font_size=9, title=""),
        margin=dict(l=0,r=0,t=10,b=10),
        height=400,
    )
    st.plotly_chart(fig_scat, use_container_width=True)

# ─────────────────────────────────────────────
# TABLA DETALLE
# ─────────────────────────────────────────────
with st.expander("📋 Tabla detallada del padrón filtrado"):
    cols_show = ["DEPARTAMENTO","PROVINCIA","DISTRITO","MCP","CANTIDAD DE ELECTORES"]
    if "COD_MCP_RENIEC" in df_f.columns:
        cols_show = ["COD_MCP_RENIEC"] + cols_show
    st.dataframe(
        df_f[cols_show].sort_values("CANTIDAD DE ELECTORES", ascending=False),
        use_container_width=True,
        height=350,
    )
    csv_bytes = df_f[cols_show].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar filtrado (CSV)", csv_bytes,
                       file_name="padron_filtrado.csv", mime="text/csv")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.divider()
st.caption("Fuente: Padrón MCP RENIEC · Shapefiles: github.com/riegagabriel/SHAPEFILES_PERU_2025")
