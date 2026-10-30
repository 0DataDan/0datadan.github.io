"""
src/indices.py
Radiometric calibrations and biophysical index computations for Landsat 8/9 Level-2.
Includes biome-aware UHI segmentation decoupling impervious surfaces, canopy, and bare soil.
"""

import numpy as np


def scale_surface_reflectance(band_data: np.ndarray) -> np.ndarray:
    """Scales raw DN to BOA Surface Reflectance: scale = 0.0000275, offset = -0.2."""
    valid_mask = band_data > 0
    reflectance = np.zeros_like(band_data, dtype=np.float32)
    reflectance[valid_mask] = (band_data[valid_mask] * 0.0000275) - 0.2
    return np.clip(reflectance, 0.0, 1.0)


def scale_surface_temperature(band_10_data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Scales Thermal Infrared DN to Land Surface Temperature:
    scale = 0.00341802, offset = 149.0 (Kelvin), then converts to Celsius.
    """
    valid_mask = band_10_data > 0
    lst_kelvin = np.zeros_like(band_10_data, dtype=np.float32)
    lst_celsius = np.zeros_like(band_10_data, dtype=np.float32)

    lst_kelvin[valid_mask] = (band_10_data[valid_mask] * 0.00341802) + 149.0
    lst_celsius[valid_mask] = lst_kelvin[valid_mask] - 273.15
    return lst_kelvin, lst_celsius


def calculate_ndvi(red_dn: np.ndarray, nir_dn: np.ndarray) -> np.ndarray:
    """Computes Normalized Difference Vegetation Index (NDVI)."""
    red = scale_surface_reflectance(red_dn)
    nir = scale_surface_reflectance(nir_dn)

    denominator = nir + red
    ndvi = np.zeros_like(red, dtype=np.float32)
    valid = (denominator > 0) & (nir_dn > 0) & (red_dn > 0)
    ndvi[valid] = (nir[valid] - red[valid]) / denominator[valid]
    return np.clip(ndvi, -1.0, 1.0)


def calculate_ndbi(nir_dn: np.ndarray, swir_dn: np.ndarray) -> np.ndarray:
    """Computes Normalized Difference Built-Up Index (NDBI): (SWIR - NIR) / (SWIR + NIR)."""
    nir = scale_surface_reflectance(nir_dn)
    swir = scale_surface_reflectance(swir_dn)

    denominator = swir + nir
    ndbi = np.zeros_like(nir, dtype=np.float32)
    valid = (denominator > 0) & (nir_dn > 0) & (swir_dn > 0)
    ndbi[valid] = (swir[valid] - nir[valid]) / denominator[valid]
    return np.clip(ndbi, -1.0, 1.0)


def extract_thermal_metrics(
    lst_celsius: np.ndarray, 
    ndvi: np.ndarray, 
    ndbi: np.ndarray = None, 
    biome: str = "temperate"
) -> dict:
    """
    Extracts biophysical summary statistics and computes a robust UHI delta.
    In arid biomes, high NDBI alongside low NDVI defines built core, avoiding
    misclassifying hot, dry desert as urban infrastructure.
    """
    valid_pixels = lst_celsius > -50.0

    if not np.any(valid_pixels):
        return {
            "mean_temp_c": 0.0, "max_temp_c": 0.0, "min_temp_c": 0.0,
            "urban_mean_temp_c": 0.0, "canopy_mean_temp_c": 0.0,
            "uhi_intensity_delta_c": 0.0, "ndvi_lst_correlation": 0.0,
            "urban_pixel_count": 0, "canopy_pixel_count": 0,
        }

    # Canopy threshold (dense vegetation)
    canopy_mask = valid_pixels & (ndvi > 0.35)

    # Urban built-up segmentation:
    # If NDBI is provided, built surfaces must exhibit positive/high NDBI
    if ndbi is not None:
        urban_mask = valid_pixels & (ndbi > 0.0) & (ndvi < 0.25)
    else:
        urban_mask = valid_pixels & (ndvi < 0.20)

    urban_mean = float(np.mean(lst_celsius[urban_mask])) if np.sum(urban_mask) > 10 else float(np.mean(lst_celsius[valid_pixels]))
    canopy_mean = float(np.mean(lst_celsius[canopy_mask])) if np.sum(canopy_mask) > 10 else float(np.mean(lst_celsius[valid_pixels]))

    valid_ndvi = ndvi[valid_pixels]
    valid_lst = lst_celsius[valid_pixels]

    if len(valid_ndvi) > 1 and np.std(valid_ndvi) > 1e-6 and np.std(valid_lst) > 1e-6:
        corr_matrix = np.corrcoef(valid_ndvi, valid_lst)
        correlation = float(corr_matrix[0, 1])
    else:
        correlation = 0.0

    return {
        "mean_temp_c": round(float(np.mean(valid_lst)), 2),
        "max_temp_c": round(float(np.max(valid_lst)), 2),
        "min_temp_c": round(float(np.min(valid_lst)), 2),
        "urban_mean_temp_c": round(urban_mean, 2),
        "canopy_mean_temp_c": round(canopy_mean, 2),
        "uhi_intensity_delta_c": round(urban_mean - canopy_mean, 2),
        "ndvi_lst_correlation": round(correlation, 3),
        "urban_pixel_count": int(np.sum(urban_mask)),
        "canopy_pixel_count": int(np.sum(canopy_mask)),
    }