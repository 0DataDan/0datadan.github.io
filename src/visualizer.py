"""
src/visualizer.py
Renders raw geospatial rasters into standardized RGB/RGBA images,
dynamic color-coded heatmaps, and correlation analytical charts.
"""

import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from PIL import Image
from typing import Optional, Tuple


def normalize_band(band: np.ndarray, lower_pct: float = 2.0, upper_pct: float = 98.0) -> np.ndarray:
    """
    Applies a 2%-98% cumulative linear contrast stretch, standard for
    satellite optical band visualization.
    """
    valid = band[~np.isnan(band) & (band > 0)]
    if len(valid) == 0:
        return np.zeros_like(band, dtype=np.uint8)

    p_low, p_high = np.percentile(valid, (lower_pct, upper_pct))
    stretched = np.clip((band - p_low) / (p_high - p_low + 1e-8), 0.0, 1.0)
    return (stretched * 255).astype(np.uint8)


def array_to_colormap_image(
    data: np.ndarray,
    cmap_name: str = "magma",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
) -> Image.Image:
    """
    Converts a single-channel 2D float array (e.g. LST or NDVI)
    into a PIL Image using Matplotlib colormaps.
    """
    valid = data[~np.isnan(data)]
    if vmin is None:
        vmin = float(np.percentile(valid, 1)) if len(valid) > 0 else 0.0
    if vmax is None:
        vmax = float(np.percentile(valid, 99)) if len(valid) > 0 else 1.0

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax, clip=True)
    cmap = plt.get_cmap(cmap_name)

    # Map float data to RGBA
    rgba = cmap(norm(data))

    # Mask NaNs as transparent
    nan_mask = np.isnan(data)
    rgba[nan_mask] = [0, 0, 0, 0]

    img_uint8 = (rgba * 255).astype(np.uint8)
    return Image.fromarray(img_uint8)


def generate_true_color(b_red: np.ndarray, b_nir: np.ndarray, b_swir: np.ndarray) -> Image.Image:
    """
    Generates a false-color or pseudo-natural composite.
    Here we map SWIR -> R, NIR -> G, Red -> B to strongly contrast
    urban concrete (cyan/grey) vs vegetation (neon green) vs water (dark blue/black).
    """
    r_norm = normalize_band(b_swir)
    g_norm = normalize_band(b_nir)
    b_norm = normalize_band(b_red)

    rgb = np.stack([r_norm, g_norm, b_norm], axis=-1)
    return Image.fromarray(rgb)


def render_correlation_scatter(
    ndvi: np.ndarray,
    lst_c: np.ndarray,
    sample_size: int = 4000
) -> Image.Image:
    """
    Draws a 2D scatter plot with density hexbin showing the cooling
    effect of vegetation on surface temperature.
    """
    valid = ~np.isnan(ndvi) & ~np.isnan(lst_c)
    x = ndvi[valid]
    y = lst_c[valid]

    # Subsample for fast plotting
    if len(x) > sample_size:
        idx = np.random.choice(len(x), sample_size, replace=False)
        x = x[idx]
        y = y[idx]

    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')

    # Hexbin density plot
    hb = ax.hexbin(x, y, gridsize=35, cmap='inferno', mincnt=1, edgecolors='none')

    # Trend line
    if len(x) > 1:
        slope, intercept = np.polyfit(x, y, 1)
        x_vals = np.linspace(-0.2, 0.8, 100)
        ax.plot(x_vals, slope * x_vals + intercept, color='#00FFAA', linestyle='--', linewidth=1.5, label=f'Trend: {slope:.1f}°C/NDVI')
        ax.legend(facecolor='#1E2129', edgecolor='none', labelcolor='white')

    ax.set_title("Surface Temperature vs. Vegetation Cover", color='white', fontsize=11, pad=10)
    ax.set_xlabel("Vegetation Index (NDVI)", color='#CCCCCC', fontsize=9)
    ax.set_ylabel("Land Surface Temp (°C)", color='#CCCCCC', fontsize=9)

    ax.tick_params(colors='#CCCCCC', which='both', labelsize=8)
    for spine in ax.spines.values():
        spine.set_color('#333333')

    cb = fig.colorbar(hb, ax=ax)
    cb.set_label('Pixel Density', color='#CCCCCC', fontsize=8)
    cb.ax.tick_params(colors='#CCCCCC', labelsize=7)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)