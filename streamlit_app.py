"""
Dashboard Electoral Perú 2025
Padrón MCP × Shapefile de Distritos
Fuente: github.com/riegagabriel/SHAPEFILES_PERU_2025
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import requests, zipfile, io, os, tempfile

# ══════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard Electoral Perú",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d1117; }
  [data-testid="stSidebar"]          { background: #161b22; }
  .kpi-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
    margin-bottom: 4px;
  }
  .kpi-label { color:#8b949e; font-size:11px; font-weight:700;
               text-transform:uppercase; letter-spacing:1px; }
  .kpi-value { color:#f0f6fc; font-size:26px; font-weight:800; margin:4px 0; }
  .kpi-sub   { color:#e63946; font-size:11px; }
  .sec-title {
    border-left: 4px solid #e63946;
    padding-left: 10px;
    color: #f0f6fc;
    font-weight: 700;
    font-size: 15px;
    margin: 18px 0 8px 0;
  }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════

# Padrón: archivo local en el mismo repo que esta app
import os as _os
PADRON_PATH = _os.path.join(_os.path.dirname(__file__), "ELECTORES_POR_MCP.xlsx")

# Shapefiles: se descargan desde GitHub
GITHUB_RAW = "https://raw.githubusercontent.com/riegagabriel/SHAPEFILES_PERU_2025/main/"
DIST_ZIP   = GITHUB_RAW + "DISTRITO.zip"
PROV_ZIP   = GITHUB_RAW + "PROVINCIA.zip"
DEPT_ZIP   = GITHUB_RAW + "DEPARTAMENTO.zip"

# Metadatos de shapefiles basados en tu print()
# name_col  = columna de nombre en el shapefile (ya sabemos que es "DISTRITO", "PROVINCIA", "DEPARTAMEN")
# join_left = columna equivalente en el padrón
SHP_META = {
    "Distrito":     {"url": DIST_ZIP, "name_col": "DISTRITO",    "join_left": "DISTRITO"},
    "Provincia":    {"url": PROV_ZIP, "name_col": "PROVINCIA",   "join_left": "PROVINCIA"},
    "Departamento": {"url": DEPT_ZIP, "name_col": "DEPARTAMEN",  "join_left": "DEPARTAMENTO"},
}

# ══════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════
@st.cache_data(show_spinner="Cargando padrón…")
def load_padron() -> pd.DataFrame:
    """Lee ELECTORES_POR_MCP.xlsx desde el mismo directorio que esta app."""
    df = pd.read_excel(PADRON_PATH)
    df.columns = df.columns.str.strip().str.upper()
    df["CANTIDAD DE ELECTORES"] = (
        pd.to_numeric(df["CANTIDAD DE ELECTORES"], errors="coerce")
        .fillna(0).astype(int)
    )
    return df


@st.cache_data(show_spinner="Descargando shapefile…")
def load_shp(url: str) -> gpd.GeoDataFrame:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            z.extractall(tmp)
        shp = next(f for f in os.listdir(tmp) if f.endswith(".shp"))
        gdf = gpd.read_file(os.path.join(tmp, shp))
    gdf.columns = [c.strip().upper() for c in gdf.columns]
    return gdf.to_crs(epsg=4326)

# ══════════════════════════════════════════════
# SIDEBAR — controles
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🗳️ Electoral Perú")
    st.caption("Padrón MCP — RENIEC 2025")
    st.divider()
    st.markdown("### 🗺️ Mapa")
    nivel       = st.selectbox("Nivel geográfico", list(SHP_META.keys()))
    color_scale = st.selectbox("Paleta", ["Reds","YlOrRd","Blues","Viridis","Plasma","Oranges"])
    st.divider()
    st.markdown("### 📊 Gráficos")
    top_n = st.slider("Top N en barras", 10, 30, 15)
    st.divider()
    st.markdown("### 🔍 Filtros")

# ── Carga padrón ──────────────────────────────
try:
    df = load_padron()
except Exception as e:
    st.error(f"❌ No se pudo cargar el padrón: {e}")
    st.info("Asegúrate de que **ELECTORES_POR_MCP.xlsx** esté en el mismo directorio que `dashboard_electoral.py`.")
    st.stop()

# ── Filtros en cascada ────────────────────────
with st.sidebar:
    depts    = ["Todos"] + sorted(df["DEPARTAMENTO"].unique())
    sel_dept = st.selectbox("Departamento", depts)
    df_f     = df if sel_dept == "Todos" else df[df["DEPARTAMENTO"] == sel_dept]

    provs    = ["Todas"] + sorted(df_f["PROVINCIA"].unique())
    sel_prov = st.selectbox("Provincia", provs)
    df_f     = df_f if sel_prov == "Todas" else df_f[df_f["PROVINCIA"] == sel_prov]

    dists    = ["Todos"] + sorted(df_f["DISTRITO"].unique())
    sel_dist = st.selectbox("Distrito", dists)
    df_f     = df_f if sel_dist == "Todos" else df_f[df_f["DISTRITO"] == sel_dist]

# ══════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════
scope = " › ".join(
    x for x in [sel_dept, sel_prov, sel_dist]
    if x not in ("Todos","Todas")
) or "Nacional"

st.markdown(f"""
<div style='background:linear-gradient(90deg,#c1121f,#e63946);
            border-radius:10px;padding:14px 24px;margin-bottom:18px'>
  <h2 style='color:#fff;margin:0'>🗳️ Dashboard Electoral — Padrón MCP Perú</h2>
  <p style='color:#ffd6d6;margin:3px 0 0;font-size:13px'>Alcance: <b>{scope}</b></p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════
total_e   = int(df_f["CANTIDAD DE ELECTORES"].sum())
total_mcp = len(df_f)
total_d   = df_f["DISTRITO"].nunique()
total_p   = df_f["PROVINCIA"].nunique()
avg_e     = int(df_f["CANTIDAD DE ELECTORES"].mean()) if total_mcp else 0

for col, (label, val, sub) in zip(st.columns(5), [
    ("Total Electores",    f"{total_e:,}",   "padrón filtrado"),
    ("N° MCPs",            f"{total_mcp:,}", "centros de votación"),
    ("Distritos",          f"{total_d:,}",   "con cobertura"),
    ("Provincias",         f"{total_p:,}",   "cubiertas"),
    ("Promedio Elect/MCP", f"{avg_e:,}",     "por centro"),
]):
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# AGGREGACIONES
# ══════════════════════════════════════════════
def agg_by(cols):
    return (df_f.groupby(cols)
                .agg(ELECTORES=("CANTIDAD DE ELECTORES","sum"),
                     MCPS=("MCP","count"))
                .reset_index()
                .sort_values("ELECTORES", ascending=False))

by_dept = agg_by("DEPARTAMENTO")
by_prov = agg_by(["DEPARTAMENTO","PROVINCIA"])
by_dist = agg_by(["DEPARTAMENTO","PROVINCIA","DISTRITO"])

# ══════════════════════════════════════════════
# FILA 1 — MAPA + BARRAS
# ══════════════════════════════════════════════
col_map, col_bar = st.columns([3, 2], gap="medium")

with col_bar:
    st.markdown('<div class="sec-title">Top Departamentos por Electores</div>',
                unsafe_allow_html=True)
    fig_bar = px.bar(
        by_dept.head(top_n), x="ELECTORES", y="DEPARTAMENTO",
        orientation="h", color="ELECTORES",
        color_continuous_scale=color_scale, text="ELECTORES",
    )
    fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc", coloraxis_showscale=False,
        margin=dict(l=0,r=70,t=10,b=10), height=440,
        yaxis={"categoryorder":"total ascending","title":""},
        xaxis_title="Electores",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_map:
    st.markdown(f'<div class="sec-title">🗺️ Mapa por {nivel}</div>',
                unsafe_allow_html=True)
    meta = SHP_META[nivel]
    try:
        gdf      = load_shp(meta["url"])
        name_col = meta["name_col"]   # ya está en mayúsculas por load_shp

        # Fallback si la columna no existe exactamente
        if name_col not in gdf.columns:
            alt = [c for c in gdf.columns
                   if any(k in c for k in ["DIST","PROV","DEP","NOMB"])]
            name_col = alt[0] if alt else gdf.columns[0]
            st.caption(f"ℹ️ Columna usada para join: `{name_col}`")

        # Normalizar texto
        gdf[name_col] = gdf[name_col].str.upper().str.strip()

        # Tabla de aggregación correcta y renombrar para el join
        if nivel == "Departamento":
            agg = by_dept.rename(columns={"DEPARTAMENTO": name_col})
        elif nivel == "Provincia":
            agg = by_prov.rename(columns={"PROVINCIA": name_col})
        else:
            agg = by_dist.rename(columns={"DISTRITO": name_col})

        agg[name_col] = agg[name_col].str.upper().str.strip()

        merged = gdf.merge(agg[[name_col,"ELECTORES","MCPS"]],
                           on=name_col, how="left")
        merged["ELECTORES"] = merged["ELECTORES"].fillna(0).astype(int)
        merged["MCPS"]      = merged["MCPS"].fillna(0).astype(int)

        fig_map = px.choropleth_map(
            merged,
            geojson=merged.__geo_interface__,
            locations=merged.index,
            color="ELECTORES",
            color_continuous_scale=color_scale,
            hover_name=name_col,
            hover_data={"ELECTORES":":,","MCPS":True},
            labels={"ELECTORES":"Electores","MCPS":"N° MCPs"},
            center={"lat":-9.19,"lon":-75.0},
            zoom=3.8,
            opacity=0.78,
        )
        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font_color="#f0f6fc",
            margin=dict(l=0,r=0,t=0,b=0), height=440,
            coloraxis_colorbar=dict(title="Electores",
                                    tickfont_color="#f0f6fc",
                                    title_font_color="#f0f6fc"),
            map_style="carto-darkmatter",
        )
        st.plotly_chart(fig_map, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ No se pudo renderizar el mapa de {nivel.lower()}s.\n\n{e}")

# ══════════════════════════════════════════════
# FILA 2 — TREEMAP + HISTOGRAMA
# ══════════════════════════════════════════════
st.markdown('<div class="sec-title">Composición y Distribución</div>',
            unsafe_allow_html=True)
col_tree, col_hist = st.columns([2, 1], gap="medium")

with col_tree:
    df_tree = (df_f.groupby(["DEPARTAMENTO","PROVINCIA","DISTRITO"])
                   .agg(ELECTORES=("CANTIDAD DE ELECTORES","sum"))
                   .reset_index())
    fig_tree = px.treemap(
        df_tree,
        path=["DEPARTAMENTO","PROVINCIA","DISTRITO"],
        values="ELECTORES",
        color="ELECTORES",
        color_continuous_scale=color_scale,
        title="Electores: Departamento → Provincia → Distrito",
    )
    fig_tree.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color="#f0f6fc",
        margin=dict(l=0,r=0,t=40,b=0), height=380,
    )
    st.plotly_chart(fig_tree, use_container_width=True)

with col_hist:
    fig_hist = px.histogram(
        df_f, x="CANTIDAD DE ELECTORES", nbins=40,
        color_discrete_sequence=["#e63946"],
        title="Distribución de tamaño de MCPs",
        labels={"CANTIDAD DE ELECTORES":"Electores/MCP"},
    )
    fig_hist.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc", margin=dict(l=0,r=0,t=40,b=0), height=380,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ══════════════════════════════════════════════
# FILA 3 — TOP DISTRITOS + SCATTER
# ══════════════════════════════════════════════
st.markdown('<div class="sec-title">Análisis Distrital</div>',
            unsafe_allow_html=True)
col_top, col_scat = st.columns(2, gap="medium")

with col_top:
    top_dist = by_dist.head(top_n).copy()
    top_dist["LABEL"] = top_dist["DISTRITO"] + " (" + top_dist["PROVINCIA"] + ")"
    fig_td = px.bar(
        top_dist, x="ELECTORES", y="LABEL", orientation="h",
        color="ELECTORES", color_continuous_scale=color_scale,
        text="ELECTORES", title=f"Top {top_n} Distritos",
    )
    fig_td.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_td.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc", coloraxis_showscale=False,
        margin=dict(l=0,r=70,t=40,b=10), height=420,
        yaxis={"categoryorder":"total ascending","title":""},
    )
    st.plotly_chart(fig_td, use_container_width=True)

with col_scat:
    fig_sc = px.scatter(
        by_dist,
        x="MCPS", y="ELECTORES",
        color="DEPARTAMENTO",
        hover_name="DISTRITO",
        hover_data={"PROVINCIA":True,"ELECTORES":":,","MCPS":True},
        labels={"MCPS":"N° MCPs","ELECTORES":"Total Electores"},
        title="MCPs vs Electores por Distrito",
    )
    fig_sc.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc", legend=dict(font_size=9,title=""),
        margin=dict(l=0,r=0,t=40,b=10), height=420,
    )
    st.plotly_chart(fig_sc, use_container_width=True)

# ══════════════════════════════════════════════
# TABLA DETALLE
# ══════════════════════════════════════════════
with st.expander("📋 Ver tabla completa del padrón filtrado"):
    show_cols = ["COD_MCP_RENIEC","DEPARTAMENTO","PROVINCIA",
                 "DISTRITO","MCP","CANTIDAD DE ELECTORES"]
    show_cols = [c for c in show_cols if c in df_f.columns]
    st.dataframe(
        df_f[show_cols].sort_values("CANTIDAD DE ELECTORES", ascending=False),
        use_container_width=True, height=320,
    )
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        df_f[show_cols].to_csv(index=False).encode("utf-8"),
        file_name="padron_mcp_filtrado.csv",
        mime="text/csv",
    )

st.divider()
st.caption("Fuente: RENIEC · Shapefiles: github.com/riegagabriel/SHAPEFILES_PERU_2025")
