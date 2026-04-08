"""
Dashboard Electoral Perú — Análisis de MCPs
Mesas de Centro de Votación × Padrón Electoral RENIEC 2025

"""

import os
import io
import zipfile
import tempfile

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go

# ══════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="MCPs Perú — Dashboard Electoral",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background:#0d1117; }
  [data-testid="stSidebar"]          { background:#161b22; }
  .kpi-card {
    background:#161b22; border:1px solid #30363d;
    border-radius:10px; padding:16px 12px;
    text-align:center; margin-bottom:6px;
  }
  .kpi-icon  { font-size:22px; margin-bottom:4px; }
  .kpi-label { color:#8b949e; font-size:10px; font-weight:700;
               text-transform:uppercase; letter-spacing:1.2px; }
  .kpi-value { color:#f0f6fc; font-size:24px; font-weight:800; margin:5px 0 3px; }
  .kpi-sub   { color:#e63946; font-size:11px; font-weight:600; }
  .sec-title {
    border-left:4px solid #e63946; padding-left:10px;
    color:#f0f6fc; font-weight:700; font-size:15px;
    margin:20px 0 10px;
  }
  .badge {
    display:inline-block; background:#21262d;
    border:1px solid #30363d; border-radius:6px;
    padding:3px 10px; font-size:12px; color:#8b949e;
    margin-right:6px;
  }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# RUTAS LOCALES  (mismo directorio que este script)
# ══════════════════════════════════════════════
BASE = os.path.dirname(__file__)

PADRON_PATH = os.path.join(BASE, "ELECTORES_POR_MCP.xlsx")
SHP_ZIPS = {
    "Departamento": os.path.join(BASE, "DEPARTAMENTOS_LIMITES.zip"),
    "Provincia":    os.path.join(BASE, "PROVINCIAL_LIMITES.zip"),
    "Distrito":     os.path.join(BASE, "DISTRITOS_LIMITES.zip"),
}

MAP_HTML = {
    "Departamento": os.path.join(BASE, "mapa_departamento.zip"),
    "Provincia":    os.path.join(BASE, "mapa_provincia.zip"),
    "Distrito":     os.path.join(BASE, "mapa_distrito.zip"),
}

# Columnas de nombre en cada shapefile (según tu print())
SHP_NAME_COL = {
    "Departamento": "DEPARTAMEN",   # truncado por ESRI
    "Provincia":    "PROVINCIA",
    "Distrito":     "DISTRITO",
}
# Columna equivalente en el padrón
PADRON_JOIN_COL = {
    "Departamento": "DEPARTAMENTO",
    "Provincia":    "PROVINCIA",
    "Distrito":     "DISTRITO",
}

# ══════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════
@st.cache_data(show_spinner="Cargando padrón…")
def load_padron() -> pd.DataFrame:
    df = pd.read_excel(PADRON_PATH)
    df.columns = df.columns.str.strip().str.upper()
    df["CANTIDAD DE ELECTORES"] = (
        pd.to_numeric(df["CANTIDAD DE ELECTORES"], errors="coerce")
        .fillna(0).astype(int)
    )
    return df


@st.cache_data(show_spinner="Leyendo shapefile…")
def load_shp(zip_path: str) -> gpd.GeoDataFrame:
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        shp = next(f for f in os.listdir(tmp) if f.endswith(".shp"))
        gdf = gpd.read_file(os.path.join(tmp, shp))
    gdf.columns = [c.strip().upper() for c in gdf.columns]
    gdf = gdf.set_geometry("GEOMETRY")
    return gdf.to_crs(epsg=4326)

# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🗳️ MCPs Perú")
    st.caption("Mesas de Centro de Votación · RENIEC 2025")
    st.divider()

    st.markdown("### 🗺️ Mapa")
    nivel = st.selectbox("Nivel geográfico", ["Departamento", "Provincia", "Distrito"])
    color_scale = st.selectbox("Paleta", ["Reds","YlOrRd","Blues","Plasma","Oranges","Viridis"])
    # Métrica visual en el mapa (Folium siempre muestra N° MCPs en color
    # y el popup muestra el detalle completo al hacer click)
    st.caption("🗺️ Color = N° MCPs · Click = lista de MCPs del área")
    st.divider()
    st.markdown("### 📊 Gráficos")
    top_n = st.slider("Top N", 10, 25, 15)
    st.divider()
    st.markdown("### 🔍 Filtros")

# ── Carga ─────────────────────────────────────
try:
    df = load_padron()
except Exception as e:
    st.error(f"❌ No se pudo cargar **ELECTORES_POR_MCP.xlsx**: {e}")
    st.stop()

# ── Filtros en cascada ─────────────────────────
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
    if x not in ("Todos", "Todas")
) or "Nacional"

st.markdown(f"""
<div style='background:linear-gradient(90deg,#c1121f,#e63946);
            border-radius:10px;padding:14px 24px;margin-bottom:18px'>
  <h2 style='color:#fff;margin:0'>🗳️ Dashboard de MCPs — Padrón Electoral Perú</h2>
  <p style='color:#ffd6d6;margin:4px 0 0;font-size:13px'>
    <b>MCP</b> = Mesa de Centro de Votación &nbsp;|&nbsp; Alcance: <b>{scope}</b>
  </p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# MÉTRICAS BASE
# ══════════════════════════════════════════════
total_mcp    = len(df_f)
total_e      = int(df_f["CANTIDAD DE ELECTORES"].sum())
avg_e_mcp    = int(df_f["CANTIDAD DE ELECTORES"].mean())  if total_mcp else 0
median_e_mcp = int(df_f["CANTIDAD DE ELECTORES"].median()) if total_mcp else 0
max_e        = int(df_f["CANTIDAD DE ELECTORES"].max())    if total_mcp else 0
min_e        = int(df_f["CANTIDAD DE ELECTORES"].min())    if total_mcp else 0
total_d      = df_f["DISTRITO"].nunique()
mcp_per_dist = round(total_mcp / total_d, 1) if total_d else 0

kpis = [
    ("🏛️", "Total MCPs",            f"{total_mcp:,}"),
    ("🗂️", "Total Electores",        f"{total_e:,}",        "en elecciones de MCP"),
    ("📍", "MCPs por Distrito",      f"{mcp_per_dist}",     f"{total_d:,} distritos"),
]

cols_kpi = st.columns(6)
for col, (icon, label, val, sub) in zip(cols_kpi, kpis):
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# AGGREGACIONES POR NIVEL
# ══════════════════════════════════════════════
def agg_nivel(cols):
    return (
        df_f.groupby(cols)
            .agg(
                MCPS        =("MCP","count"),
                ELECTORES   =("CANTIDAD DE ELECTORES","sum"),
                PROM_ELECT  =("CANTIDAD DE ELECTORES","mean"),
            )
            .reset_index()
            .assign(PROM_ELECT=lambda x: x["PROM_ELECT"].round(0).astype(int))
    )

by_dept = agg_nivel("DEPARTAMENTO").sort_values("MCPS", ascending=False)
by_prov = agg_nivel(["DEPARTAMENTO","PROVINCIA"]).sort_values("MCPS", ascending=False)
by_dist = agg_nivel(["DEPARTAMENTO","PROVINCIA","DISTRITO"]).sort_values("MCPS", ascending=False)

# ══════════════════════════════════════════════
# FILA 1 — MAPA + BARRAS MCPs POR DEPARTAMENTO
# ══════════════════════════════════════════════
col_map, col_bar = st.columns([3, 2], gap="medium")

# ── Barras: MCPs por departamento ─────────────
with col_bar:
    st.markdown('<div class="sec-title">MCPs y Electores por Departamento</div>',
                unsafe_allow_html=True)

    # Doble eje: barras = MCPs, línea = electores
    dept_top = by_dept.head(top_n).sort_values("MCPS")
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=dept_top["DEPARTAMENTO"], x=dept_top["MCPS"],
        orientation="h", name="N° MCPs",
        marker_color="#e63946",
        text=dept_top["MCPS"], textposition="outside",
        textfont_color="#f0f6fc",
    ))
    fig_bar.add_trace(go.Scatter(
        y=dept_top["DEPARTAMENTO"],
        x=dept_top["ELECTORES"] / dept_top["ELECTORES"].max() * dept_top["MCPS"].max(),
        mode="markers",
        name="Electores (rel.)",
        marker=dict(color="#ffd166", size=8, symbol="diamond"),
        hovertemplate="%{customdata:,} electores<extra></extra>",
        customdata=dept_top["ELECTORES"],
    ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc",
        legend=dict(orientation="h", y=1.08, font_size=11),
        margin=dict(l=0, r=60, t=10, b=10), height=440,
        xaxis_title="N° MCPs",
        yaxis_title="",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Mapa HTML pre-generado (Folium) ──────────
with col_map:
    st.markdown(
        f'<div class="sec-title">🗺️ MCPs por {nivel} — click para ver detalle</div>',
        unsafe_allow_html=True,
    )
    html_path = MAP_HTML[nivel]

if not os.path.exists(html_path):
    st.info(
        f"📋 El mapa **{os.path.basename(html_path)}** aún no existe.",
        icon="ℹ️",
    )
else:
    # Si es ZIP → extraer y leer HTML
    if html_path.endswith(".zip"):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(html_path, 'r') as z:
                z.extractall(tmp)

            # Buscar el .html dentro del zip
            html_file = next(
                (f for f in os.listdir(tmp) if f.endswith(".html")),
                None
            )

            if html_file is None:
                st.error("❌ No se encontró archivo HTML dentro del ZIP")
            else:
                with open(os.path.join(tmp, html_file), "r", encoding="utf-8") as f:
                    html_content = f.read()

                components.html(html_content, height=460, scrolling=False)

    # Si ya es HTML directo
    else:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=460, scrolling=False)

# ══════════════════════════════════════════════
# FILA 2 — DISTRIBUCIÓN DE ELECTORES POR MCP
# ══════════════════════════════════════════════
st.markdown('<div class="sec-title">Distribución de Electores por MCP</div>',
            unsafe_allow_html=True)

col_hist, col_box, col_pie = st.columns([2, 2, 1], gap="medium")

with col_hist:
    fig_hist = px.histogram(
        df_f, x="CANTIDAD DE ELECTORES", nbins=50,
        color_discrete_sequence=["#e63946"],
        title="Histograma de tamaño de MCPs",
        labels={"CANTIDAD DE ELECTORES": "Electores/MCP", "count": "N° MCPs"},
    )
    fig_hist.add_vline(x=avg_e_mcp, line_dash="dash", line_color="#ffd166",
                       annotation_text=f"Promedio: {avg_e_mcp:,}",
                       annotation_font_color="#ffd166")
    fig_hist.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc", margin=dict(l=0,r=0,t=40,b=0), height=320,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col_box:
    # Box plot por departamento (top 10 por cantidad de MCPs)
    top_depts_box = by_dept.head(10)["DEPARTAMENTO"].tolist()
    df_box = df_f[df_f["DEPARTAMENTO"].isin(top_depts_box)]
    fig_box = px.box(
        df_box, x="DEPARTAMENTO", y="CANTIDAD DE ELECTORES",
        color="DEPARTAMENTO",
        title="Dispersión Electores/MCP (top 10 depts.)",
        labels={"CANTIDAD DE ELECTORES":"Electores/MCP","DEPARTAMENTO":""},
    )
    fig_box.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc", showlegend=False,
        margin=dict(l=0,r=0,t=40,b=0), height=320,
        xaxis_tickangle=-35,
    )
    st.plotly_chart(fig_box, use_container_width=True)

with col_pie:
    # Rangos de tamaño de MCP
    bins   = [0, 500, 1000, 2000, 5000, 999999]
    labels = ["≤500","501-1k","1k-2k","2k-5k",">5k"]
    df_f2  = df_f.copy()
    df_f2["RANGO"] = pd.cut(df_f2["CANTIDAD DE ELECTORES"],
                             bins=bins, labels=labels)
    rango_cnt = df_f2["RANGO"].value_counts().reset_index()
    rango_cnt.columns = ["RANGO","MCPs"]
    fig_pie = px.pie(
        rango_cnt, names="RANGO", values="MCPs",
        color_discrete_sequence=px.colors.sequential.Reds_r,
        title="MCPs por rango de tamaño",
        hole=0.45,
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color="#f0f6fc",
        margin=dict(l=0,r=0,t=40,b=0), height=320,
        legend=dict(font_size=10),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ══════════════════════════════════════════════
# FILA 3 — TOP DISTRITOS MCPs + SCATTER
# ══════════════════════════════════════════════
st.markdown('<div class="sec-title">Análisis Distrital de MCPs</div>',
            unsafe_allow_html=True)

col_top, col_scat = st.columns(2, gap="medium")

with col_top:
    top_dist = by_dist.head(top_n).copy()
    top_dist["LABEL"] = top_dist["DISTRITO"] + " (" + top_dist["PROVINCIA"] + ")"
    fig_td = px.bar(
        top_dist.sort_values("MCPS"),
        x="MCPS", y="LABEL", orientation="h",
        color="ELECTORES", color_continuous_scale=color_scale,
        text="MCPS",
        title=f"Top {top_n} Distritos por N° de MCPs",
        labels={"MCPS":"N° MCPs","LABEL":"","ELECTORES":"Electores totales"},
    )
    fig_td.update_traces(texttemplate="%{text}", textposition="outside")
    fig_td.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc",
        margin=dict(l=0,r=50,t=40,b=10), height=420,
        yaxis_title="",
        coloraxis_colorbar=dict(title="Electores",
                                tickfont_color="#f0f6fc",
                                title_font_color="#f0f6fc"),
    )
    st.plotly_chart(fig_td, use_container_width=True)

with col_scat:
    fig_sc = px.scatter(
        by_dist,
        x="MCPS", y="PROM_ELECT",
        size="ELECTORES",
        color="DEPARTAMENTO",
        hover_name="DISTRITO",
        hover_data={"PROVINCIA":True,
                    "MCPS":True,
                    "ELECTORES":":,",
                    "PROM_ELECT":True},
        labels={"MCPS":"N° MCPs",
                "PROM_ELECT":"Promedio Electores/MCP",
                "ELECTORES":"Total Electores"},
        title="N° MCPs vs Promedio Electores/MCP por Distrito",
    )
    fig_sc.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f0f6fc", legend=dict(font_size=9, title=""),
        margin=dict(l=0,r=0,t=40,b=10), height=420,
    )
    st.plotly_chart(fig_sc, use_container_width=True)

# ══════════════════════════════════════════════
# TABLA DETALLE MCPs
# ══════════════════════════════════════════════
with st.expander("📋 Ver detalle de MCPs (padrón filtrado)"):
    show_cols = [c for c in
                 ["COD_MCP_RENIEC","DEPARTAMENTO","PROVINCIA","DISTRITO",
                  "MCP","CANTIDAD DE ELECTORES"]
                 if c in df_f.columns]
    st.dataframe(
        df_f[show_cols].sort_values("CANTIDAD DE ELECTORES", ascending=False)
                       .reset_index(drop=True),
        use_container_width=True, height=320,
    )
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        df_f[show_cols].to_csv(index=False).encode("utf-8"),
        file_name="mcps_filtrado.csv",
        mime="text/csv",
    )

st.divider()
st.caption("Fuente: RENIEC · Shapefiles: INEI 2025")
