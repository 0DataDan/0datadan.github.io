"""
app.py
Urban Heat Island & Surface Reflectance Explorer
Interactive Geospatial AI Dashboard for Landsat 8/9 Level-2 Analysis
Fully consolidated main-canvas architecture without sidebar or visible API key inputs.
"""

import os
import streamlit as st
import numpy as np
import rasterio
from dotenv import load_dotenv

from src.indices import (
    calculate_ndvi,
    calculate_ndbi,
    scale_surface_temperature,
    extract_thermal_metrics,
)
from src.visualizer import (
    array_to_colormap_image,
    generate_true_color,
    render_correlation_scatter,
)
from src.ai_analyst import analyze_satellite_scene

load_dotenv()

st.set_page_config(
    page_title="Urban Heat Island Explorer",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Completely hide sidebar and collapse toggle icon */
    [data-testid="stSidebarCollapseButton"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    .metric-card {
        background-color: #1A1C24;
        border: 1px solid #2B2F3E;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .metric-title {
        color: #8E94A5;
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 4px;
    }
    .metric-val {
        color: #F0F2F6;
        font-size: 24px;
        font-weight: 700;
    }
    .metric-sub {
        color: #00FFAA;
        font-size: 12px;
    }
    .anomaly-hotspot {
        border-left: 4px solid #FF4B4B;
        background: rgba(255, 75, 75, 0.08);
        padding: 10px 14px;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    .anomaly-cool {
        border-left: 4px solid #00D4BB;
        background: rgba(0, 212, 187, 0.08);
        padding: 10px 14px;
        border-radius: 4px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

CITY_OPTIONS = {
    "phoenix": "Phoenix, AZ (Arid Desert)",
    "atlanta": "Atlanta, GA (Humid Canopy Forest)",
    "chicago": "Chicago, IL (Temperate Lakefront)",
}

st.title("Urban Heat Island & Surface Reflectance Explorer")
st.caption("Landsat 8/9 Level-2 Multimodal Computer Vision & Earth Observation Telemetry")

# --- Top Control Bar ---
with st.container():
    c1, c2 = st.columns([3, 1])
    with c1:
        selected_city = st.selectbox(
            "Target Metropolitan Biome",
            options=list(CITY_OPTIONS.keys()),
            format_func=lambda k: CITY_OPTIONS[k],
            key="main_city_select"
        )
    with c2:
        st.caption("**Sensor Suite:** Landsat 9 OLI/TIRS (Collection 2)")
        st.caption("**Spatial Resolution:** 30m / pixel | **Grid:** 600×600 px")

st.divider()


@st.cache_data
def load_and_process_scene(city_key: str):
    """Dynamically ingests GeoTIFFs for the selected metropolitan region."""
    city_dir = os.path.join("data", "raw", city_key)
    
    b4_path = os.path.join(city_dir, f"{city_key}_B4.TIF")
    b5_path = os.path.join(city_dir, f"{city_key}_B5.TIF")
    b6_path = os.path.join(city_dir, f"{city_key}_B6.TIF")
    b10_path = os.path.join(city_dir, f"{city_key}_B10.TIF")

    # Fallback to default root directory if city subdirectory is not populated
    if not all(os.path.exists(p) for p in [b4_path, b5_path, b6_path, b10_path]):
        b4_path, b5_path, b6_path, b10_path = (
            "data/raw/sample_B4.TIF",
            "data/raw/sample_B5.TIF",
            "data/raw/sample_B6.TIF",
            "data/raw/sample_B10.TIF"
        )

    if not all(os.path.exists(p) for p in [b4_path, b5_path, b6_path, b10_path]):
        return None

    with rasterio.open(b4_path) as r, rasterio.open(b5_path) as n, rasterio.open(b6_path) as s, rasterio.open(b10_path) as t:
        red = r.read(1)
        nir = n.read(1)
        swir = s.read(1)
        thermal = t.read(1)

    ndvi = calculate_ndvi(red, nir)
    ndbi = calculate_ndbi(nir, swir)
    _, lst_c = scale_surface_temperature(thermal)
    metrics = extract_thermal_metrics(lst_c, ndvi)

    img_comp = generate_true_color(red, nir, swir)
    img_lst = array_to_colormap_image(lst_c, cmap_name="magma")
    img_ndvi = array_to_colormap_image(ndvi, cmap_name="YlGn")
    img_scatter = render_correlation_scatter(ndvi, lst_c)

    os.makedirs("data/processed", exist_ok=True)
    lst_cache = f"data/processed/{city_key}_lst.png"
    comp_cache = f"data/processed/{city_key}_composite.png"
    img_lst.save(lst_cache)
    img_comp.save(comp_cache)

    return {
        "metrics": metrics,
        "img_comp": img_comp,
        "img_lst": img_lst,
        "img_ndvi": img_ndvi,
        "img_scatter": img_scatter,
        "lst_cache": lst_cache,
        "comp_cache": comp_cache,
    }


scene = load_and_process_scene(selected_city)

if scene is None:
    st.error(f"Datasets for `{selected_city}` not found in `data/raw/{selected_city}/`.")
    st.stop()

metrics = scene["metrics"]

# KPI Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">UHI INTENSITY DELTA</div>
        <div class="metric-val">+{metrics['uhi_intensity_delta_c']} °C</div>
        <div class="metric-sub">Urban Core vs. Canopy</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">URBAN CORE MEAN TEMP</div>
        <div class="metric-val">{metrics['urban_mean_temp_c']} °C</div>
        <div class="metric-sub">Peak: {metrics['max_temp_c']} °C</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">CANOPY MEAN TEMP</div>
        <div class="metric-val">{metrics['canopy_mean_temp_c']} °C</div>
        <div class="metric-sub">Min: {metrics['min_temp_c']} °C</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">NDVI-LST CORRELATION</div>
        <div class="metric-val">{metrics['ndvi_lst_correlation']}</div>
        <div class="metric-sub">Negative Thermal Buffering</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

tab1, tab2 = st.tabs(["🛰️ Spatial Visualizations", "📊 Biophysical Telemetry & Analysis"])

with tab1:
    vcol1, vcol2 = st.columns(2)
    with vcol1:
        st.subheader("SWIR / NIR / Red Composite")
        st.caption("Cyan/Grey: Built Concrete | Green: Canopy | Dark Blue/Black: Water")
        st.image(scene["img_comp"], use_container_width=True)

    with vcol2:
        st.subheader("Calibrated Land Surface Temp (LST)")
        st.caption("Thermal Infrared (Band 10) mapped to Magma colormap (°C)")
        st.image(scene["img_lst"], use_container_width=True)

    st.divider()

    bcol1, bcol2 = st.columns(2)
    with bcol1:
        st.subheader("Normalized Difference Vegetation Index (NDVI)")
        st.caption("Chlorophyll absorption: Yellow = Impervious/Barren | Deep Green = Dense Canopy")
        st.image(scene["img_ndvi"], use_container_width=True)

    with bcol2:
        st.subheader("Thermal Density vs. Vegetation Scatter")
        st.caption("Hexbin density correlation showing temperature reduction across NDVI gradients")
        st.image(scene["img_scatter"], use_container_width=True)

with tab2:
    st.subheader(f"Multimodal AI Scene Analysis: {CITY_OPTIONS[selected_city]}")
    st.markdown("Submits dual-band geospatial rasters and calibrated sensor metrics to Gemini using structured JSON schema output.")

    if st.button("Generate Environmental Assessment", type="primary"):
        active_key = os.getenv("GEMINI_API_KEY", "")
        if not active_key:
            st.error("No Gemini API key detected. Please define GEMINI_API_KEY in your .env environment file.")
        else:
            with st.spinner(f"Evaluating thermal distribution and biophysical dynamics for {selected_city}..."):
                try:
                    report = analyze_satellite_scene(
                        lst_image_path=scene["lst_cache"],
                        composite_image_path=scene["comp_cache"],
                        metrics=metrics,
                        api_key=active_key,
                    )

                    st.success(f"**UHI Severity Rating: {report.uhi_severity_tier}**")
                    st.write(report.scene_summary)

                    acol1, acol2 = st.columns(2)
                    with acol1:
                        st.markdown("### Detected Thermal Anomalies")
                        for a in report.detected_anomalies:
                            css_class = "anomaly-hotspot" if a.feature_type == "hotspot" else "anomaly-cool"
                            st.markdown(f"""
                            <div class="{css_class}">
                                <strong>[{a.feature_type.upper()}] {a.feature_name}</strong><br>
                                Estimated Surface Temp: ~{a.estimated_temp_c}°C<br>
                                <span style="font-size: 12px; color: #BBB;">Biophysical Driver: {a.cooling_factor}</span>
                            </div>
                            """, unsafe_allow_html=True)

                    with acol2:
                        st.markdown("### Recommended Mitigations")
                        for intervention in report.actionable_interventions:
                            st.markdown(f"• {intervention}")

                        st.markdown("### Canopy Buffering Assessment")
                        st.info(report.vegetation_buffering_assessment)

                except Exception as e:
                    st.error(f"Inference failed: {e}")