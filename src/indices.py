"""
src/indices.py
Core Earth Observation calculation module for Landsat 8/9 Level-2 products.
Handles radiometric scaling, band math, masking, and summary metrics.
"""

import numpy as np
import rasterio
from typing import Dict, Tuple, Optional


# USGS Landsat Collection 2 Level-2 official scale & offset factors
SR_SCALE = 0.0000275
SR_OFFSET = -0.2

ST_SCALE = 0.00341802
ST_OFFSET = 149.0


def scale_surface_reflectance(raw_band: np.ndarray) -> np.ndarray:
    """Scale raw DN to physical surface reflectance (0.0 to 1.0)."""
    mask = raw_band == 0  # Fill / nodata value in Collection 2
    scaled = (raw_band.astype(np.float32) * SR_SCALE) + SR_OFFSET
    scaled[mask] = np.nan
    scaled = np.clip(scaled, 0.0, 1.0)
    return scaled


def scale_surface_temperature(raw_st: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Scale raw DN to Land Surface Temperature (Kelvin and Celsius).
    Returns (LST_Kelvin, LST_Celsius).
    """
    mask = raw_st == 0
    kelvin = (raw_st.astype(np.float32) * ST_SCALE) + ST_OFFSET
    kelvin[mask] = np.nan
    celsius = kelvin - 273.15
    return kelvin, celsius


def calculate_ndvi(red_band: np.ndarray, nir_band: np.ndarray) -> np.ndarray:
    """
    Calculate Normalized Difference Vegetation Index (NDVI).
    NDVI = (NIR - Red) / (NIR + Red)
    """
    red = scale_surface_reflectance(red_band)
    nir = scale_surface_reflectance(nir_band)

    denominator = nir + red
    # Prevent divide-by-zero or near-zero floating noise
    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi = (nir - red) / denominator
        ndvi[denominator == 0] = np.nan

    return np.clip(ndvi, -1.0, 1.0)


def calculate_ndbi(nir_band: np.ndarray, swir1_band: np.ndarray) -> np.ndarray:
    """
    Calculate Normalized Difference Built-up Index (NDBI).
    NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)
    """
    nir = scale_surface_reflectance(nir_band)
    swir = scale_surface_reflectance(swir1_band)

    denominator = swir + nir
    with np.errstate(divide='ignore', invalid='ignore'):
        ndbi = (swir - nir) / denominator
        ndbi[denominator == 0] = np.nan

    return np.clip(ndbi, -1.0, 1.0)


def extract_thermal_metrics(lst_celsius: np.ndarray, ndvi: np.ndarray) -> Dict[str, float]:
    """
    Compute statistical metrics correlating surface heating with vegetation cover.
    """
    valid_mask = ~np.isnan(lst_celsius) & ~np.isnan(ndvi)
    valid_lst = lst_celsius[valid_mask]
    valid_ndvi = ndvi[valid_mask]

    if len(valid_lst) == 0:
        return {}

    # Define urban/impervious (low vegetation) vs vegetated canopy
    low_veg_mask = valid_ndvi < 0.2
    high_veg_mask = valid_ndvi > 0.5

    mean_lst_overall = float(np.mean(valid_lst))
    mean_lst_urban = float(np.mean(valid_lst[low_veg_mask])) if np.any(low_veg_mask) else mean_lst_overall
    mean_lst_canopy = float(np.mean(valid_lst[high_veg_mask])) if np.any(high_veg_mask) else mean_lst_overall

    # UHI thermal differential (Urban vs Vegetated cooling delta)
    uhi_intensity = mean_lst_urban - mean_lst_canopy

    # Pearson correlation coefficient between vegetation deficit and temperature
    if len(valid_lst) > 1:
        corr_matrix = np.corrcoef(valid_ndvi, valid_lst)
        correlation = float(corr_matrix[0, 1])
    else:
        correlation = 0.0

    return {
        "mean_temp_c": round(mean_lst_overall, 2),
        "max_temp_c": round(float(np.max(valid_lst)), 2),
        "min_temp_c": round(float(np.min(valid_lst)), 2),
        "urban_mean_temp_c": round(mean_lst_urban, 2),
        "canopy_mean_temp_c": round(mean_lst_canopy, 2),
        "uhi_intensity_delta_c": round(uhi_intensity, 2),
        "ndvi_lst_correlation": round(correlation, 3),
        "valid_pixels": int(np.sum(valid_mask)),
    }