# 🛰️ Urban Heat Island & Surface Reflectance Explorer

An interactive geospatial Earth Observation platform and multimodal AI diagnostic engine. The system streams authentic satellite telemetry from the **Landsat 8/9 Level-2 (Collection 2)** constellation via Microsoft Planetary Computer STAC, derives radiometrically calibrated biophysical indices, and generates structured environmental risk assessments using multimodal LLMs.

---

## 📌 Architecture Overview

[ USGS Landsat 8/9 Level-2 Constellation ]
│
▼
[ Microsoft Planetary Computer STAC API ]
│ (WGS84 Bounding Box → Native UTM Window Transformation)
▼
[ Geospatial Ingestion Engine (Rasterio / PyProj) ]
├── Band 4: Red (636–673 nm)
├── Band 5: Near-Infrared / NIR (851–879 nm)
├── Band 6: Short-Wave Infrared / SWIR-1 (1566–1651 nm)
└── Band 10: Thermal Infrared / TIRS-1 (10.60–11.19 µm)
│
▼
[ Radiometric Calibration & Biophysical Index Engine ]
├── Bottom-of-Atmosphere (BOA) Surface Reflectance Scaling
├── Planck Surface Temperature Inversion (Kelvin → Celsius)
├── NDVI (Normalized Difference Vegetation Index)
├── NDBI (Normalized Difference Built-Up Index)
└── Decoupled UHI Intensity Delta (NDBI/NDVI Joint Masking)
│
├─────────────────────────────────────────┐
▼                                         ▼
[ Interactive UI & Slippy Maps ]               [ Multimodal AI Reasoner ]
├── Georeferenced Thermal Rasters (Folium)      ├── Model Routing & Fallback
├── Water-Masked Alpha Transparencies           │   (3.5-flash-lite → 3.5-flash)
├── Interactive Density Contours (Plotly)       └── Pydantic Schema Validation
└── CDC Social Vulnerability Context (SVI)           └── Structured JSON Telemetry


---

## 🔬 Radiometric Calibration & Physics

### 1. Optical Surface Reflectance (Bands 4, 5, 6)
Raw digital numbers ($DN$) are scaled to bottom-of-atmosphere (BOA) surface reflectance:
$$\rho = (DN \times 0.0000275) - 0.2$$

### 2. Thermal Conversion to Land Surface Temperature (Band 10)
Landsat Collection 2 Level-2 Surface Temperature products provide calibrated surface temperature in Kelvin:
$$T_K = (DN \times 0.00341802) + 149.0$$
$$T_{^\circ\text{C}} = T_K - 273.15$$

### 3. Spectral Indices & Biome-Aware UHI Masking
* **Normalized Difference Vegetation Index (NDVI):**
  $$NDVI = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}}}$$
* **Normalized Difference Built-Up Index (NDBI):**
  $$NDBI = \frac{\rho_{\text{SWIR}} - \rho_{\text{NIR}}}{\rho_{\text{SWIR}} + \rho_{\text{NIR}}}$$
* **UHI Intensity Delta ($\Delta T$):**
  $$\Delta T = \bar{T}_{\text{Built Core}} - \bar{T}_{\text{Canopy Buffer}}$$
  *In arid environments, pure NDVI thresholding fails because barren desert soils run hotter than irrigated urban lawns (the "oasis effect"). The engine couples NDBI ($> 0.0$) with low NDVI ($< 0.25$) to isolate man-made impervious infrastructure from bare desert soil.*

### 4. Sensor Physics: LST vs. Canopy Air Layer (CAL)
Satellites observe **Land Surface Temperature (LST)**—the radiant skin temperature of rooftops, asphalt, and canopy envelopes. Human physiological heat illness occurs within the **Canopy Air Layer (CAL)**, 2 meters above ground. High-albedo or canopy-shaded areas buffer microclimate air temperatures via evapotranspiration, whereas deep urban street canyons trap longwave radiation, preventing nocturnal cooling.

---

## 🏙️ Comparative Biome Analysis

| Metric | Phoenix, AZ | Atlanta, GA | Chicago, IL | New York City, NY |
|---|---|---|---|---|
| **Urban Biome** | Subtropical Arid Desert | Humid Deciduous Forest | Temperate Lakefront | Ultra-Dense Coastal Megacity |
| **Peak Surface Temp** | $> 50^\circ\text{C}$ | $\sim 36–40^\circ\text{C}$ | $\sim 38–42^\circ\text{C}$ | $\sim 42–46^\circ\text{C}$ |
| **Cooling Buffer** | Oasis-effect irrigation | Continuous canopy cover | Lake Michigan breeze | Central Park thermal reservoir |
| **Dominant UHI Driver** | Low-albedo paved surfaces | Transport corridor clearings | High-density asphalt grid | Deep urban street canyon trapping |
| **CDC SVI Equity Gap** | South Phoenix industrial core | South/West corridor canopy loss | South/West side industrial belts | South Bronx & Upper Manhattan gap |

---

## 🚀 Installation & Local Deployment

### 1. Prerequisites
- Python 3.10+
- macOS / Linux / Windows WSL2

### 2. Clone & Environment Setup
```bash
git clone [https://github.com/your-username/urban-heat-explorer.git](https://github.com/your-username/urban-heat-explorer.git)
cd urban-heat-explorer

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. Configure API Credentials
Create a .env file in the root directory:

Bash
echo 'GEMINI_API_KEY="your_api_key_here"' > .env
4. Ingest Authentic Satellite Scenes
Download the cloud-optimized, coordinate-reprojected scenes across all target metropolitan biomes:

Bash
python3 download_real_scene.py
5. Launch the Dashboard
Bash
streamlit run app.py
Open http://localhost:8501 in your browser.

🛠️ Tech Stack
Geospatial Processing: rasterio, pyproj, numpy, matplotlib

Mapping & Visualization: folium, streamlit-folium, plotly, branca, Pillow

Application Framework: streamlit

AI & Structured Reasoning: google-genai (Gemini SDK), pydantic

Earth Observation Ingestion: Microsoft Planetary Computer STAC API