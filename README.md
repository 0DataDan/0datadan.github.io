# 🛰️ Urban Heat Island & Surface Reflectance Explorer

An interactive geospatial Earth Observation platform and multimodal AI diagnostic engine. The system processes authentic satellite rasters from the **Landsat 8/9 Level-2 (Collection 2)** constellation, derives calibrated biophysical indices, and generates structured environmental assessments via multimodal LLMs.

---

## 📌 Architecture Overview

[ USGS Landsat 8/9 Level-2 ]
│
▼
[ Microsoft Planetary Computer STAC ]
│ (On-the-fly SAS signing & windowed HTTP streaming)
▼
[ Geospatial Ingestion Engine (Rasterio) ]
├── Band 4: Red (636–673 nm)
├── Band 5: Near-Infrared / NIR (851–879 nm)
├── Band 6: Short-Wave Infrared / SWIR-1 (1566–1651 nm)
└── Band 10: Thermal Infrared / TIRS-1 (10.60–11.19 µm)
│
▼
[ Radiometric Calibration & Biophysical Computation ]
├── Multiplicative & Additive Scale Conversions
├── NDVI (Normalized Difference Vegetation Index)
├── NDBI (Normalized Difference Built-Up Index)
└── Land Surface Temperature (LST in °C)
│
├──────────────────────────────┐
▼                              ▼
[ Interactive UI (Streamlit) ]    [ Multimodal AI Engine (Google GenAI) ]
├── False-Color Composite         ├── Model Fallback Pipeline
├── Thermal LST Heatmaps          │   (3.5-flash-lite → 3.5-flash → 3.8-flash)
├── Hexbin Density Scatter        └── Pydantic Schema Validation
└── Comparative Urban Biomes          └── Deterministic JSON Report


---

## 🔬 Radiometric Calibration & Physics

### 1. Optical Surface Reflectance (Bands 4, 5, 6)
Raw digital numbers ($DN$) are scaled to bottom-of-atmosphere (BOA) surface reflectance:
$$\rho = (DN \times 0.0000275) - 0.2$$

### 2. Thermal Conversion to Land Surface Temperature (Band 10)
Landsat Collection 2 Level-2 Surface Temperature products provide calibrated surface temperature in Kelvin:
$$T_K = (DN \times 0.00341802) + 149.0$$
$$T_{^\circ\text{C}} = T_K - 273.15$$

### 3. Spectral Indices
* **Normalized Difference Vegetation Index (NDVI):**
  $$NDVI = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}}}$$
* **Normalized Difference Built-Up Index (NDBI):**
  $$NDBI = \frac{\rho_{\text{SWIR}} - \rho_{\text{NIR}}}{\rho_{\text{SWIR}} + \rho_{\text{NIR}}}$$

---

## 🏙️ Comparative Biome Analysis

| Metric | Phoenix, AZ (Arid) | Atlanta, GA (Humid Canopy) | Chicago, IL (Temperate Lakefront) |
|---|---|---|---|
| **Urban Biome** | Subtropical Desert | Deciduous / Pine Forest Matrix | Lake Michigan Shoreline Grid |
| **Peak Surface Temp** | $> 50^\circ\text{C}$ | $\sim 36–40^\circ\text{C}$ | $\sim 38–42^\circ\text{C}$ |
| **NDVI Buffering** | Oasis-effect clustering | Pervasive canopy depression | Shoreline breeze & park cooling |
| **Dominant UHI Driver** | Low-albedo paved surfaces | High-density transit corridors | Impervious commercial core |

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
Download the cloud-optimized 600×600 pixel bounding crops across target biomes:

Bash
python3 download_real_scene.py
5. Launch the Dashboard
Bash
streamlit run app.py
Open http://localhost:8501 in your browser.

🛠️ Tech Stack
Geospatial Processing: rasterio, numpy, matplotlib

Application Framework: streamlit

AI & Reasoning: google-genai (Gemini SDK), pydantic

Data Ingestion: Microsoft Planetary Computer STAC API