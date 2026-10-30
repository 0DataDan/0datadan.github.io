"""
src/ai_analyst.py
Multimodal Earth Observation analysis engine using Google GenAI SDK.
Enforces structured Pydantic schemas over satellite imagery and computed metrics
with candidate fallback handling.
"""

import os
import json
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


# --- Pydantic Data Contract ---
class ThermalAnomaly(BaseModel):
    feature_name: str = Field(description="Name or description of the feature (e.g., Industrial Core, River Corridor, Urban Park)")
    feature_type: Literal["hotspot", "cool_island", "neutral_zone"]
    estimated_temp_c: float = Field(description="Estimated surface temperature in Celsius")
    cooling_factor: str = Field(description="Dominant biophysical mechanism (e.g., Evapotranspiration, Low Albedo Concrete, Water Heat Capacity)")


class UHIAnalysisReport(BaseModel):
    scene_summary: str = Field(description="High-level synthesis of thermal and vegetative surface reflectance patterns")
    uhi_severity_tier: Literal["Low", "Moderate", "Severe", "Extreme"]
    thermal_differential_rating: str = Field(description="Evaluation of the urban-to-canopy delta temperature")
    detected_anomalies: List[ThermalAnomaly]
    vegetation_buffering_assessment: str = Field(description="Analysis of how NDVI values correlate with surface temperature mitigation")
    actionable_interventions: List[str] = Field(description="Specific urban planning or surface reflectance mitigation strategies")


# --- Multimodal Analyst Caller ---
def analyze_satellite_scene(
    lst_image_path: str,
    composite_image_path: str,
    metrics: dict,
    api_key: Optional[str] = None
) -> UHIAnalysisReport:
    """
    Submits dual visual bands alongside sensor metrics to Gemini,
    with automatic model fallback handling, returning a validated Pydantic report.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not set. Provide an API key via environment variable or argument.")

    client = genai.Client(api_key=key)

    img_lst = Image.open(lst_image_path)
    img_comp = Image.open(composite_image_path)

    prompt = f"""
You are an expert Earth Observation and Urban Climatologist specializing in NASA/USGS Landsat 8/9 Level-2 products.
Analyze the two provided satellite images and the calibrated sensor metrics for this scene:

Image 1: Land Surface Temperature (LST) Thermal Heatmap (Magma colormap: dark purple = cool, bright yellow/white = hot).
Image 2: Shortwave/Near-Infrared Composite (SWIR/NIR/Red: cyan/grey = built concrete, neon green = canopy, dark = water).

Calibrated Radiometric Metrics:
- Overall Mean Surface Temp: {metrics.get('mean_temp_c')} °C
- Urban Core Mean Temp: {metrics.get('urban_mean_temp_c')} °C
- Canopy/Park Mean Temp: {metrics.get('canopy_mean_temp_c')} °C
- UHI Intensity Delta: +{metrics.get('uhi_intensity_delta_c')} °C
- NDVI to LST Correlation: {metrics.get('ndvi_lst_correlation')}
- Valid Radiometric Pixels: {metrics.get('valid_pixels')}

Evaluate the spatial distribution of surface heating, quantify the cooling effect of the vegetated zones and water bodies, and identify critical heat mitigation priorities.
"""

    candidate_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]

    last_error = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[img_lst, img_comp, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=UHIAnalysisReport,
                )
            )
            report_data = json.loads(response.text)
            return UHIAnalysisReport.model_validate(report_data)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All candidate models failed. Last error: {last_error}")