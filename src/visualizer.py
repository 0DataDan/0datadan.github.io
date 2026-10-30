"""
src/visualizer.py
Visual rendering module for Landsat 8/9 Level-2 data.
Generates georeferenced thermal overlays for Folium slippy maps with 
water transparency and interactive Plotly density analytics.
"""

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import plotly.graph_objects as go
from pyproj import Transformer
import branca.colormap as cm


def get_raster_wgs84_bounds(transform, width, height, src_crs):
    """
    Transforms raster pixel corners into WGS84 [[south, west], [north, east]]
    for direct mapping in Folium / Leaflet.
    """
    transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
    
    tl_x, tl_y = transform * (0, 0)
    br_x, br_y = transform * (width, height)
    
    min_lon, min_lat = transformer.transform(min(tl_x, br_x), min(tl_y, br_y))
    max_lon, max_lat = transformer.transform(max(tl_x, br_x), max(tl_y, br_y))
    
    return [[min_lat, min_lon], [max_lat, max_lon]]


def array_to_rgba_overlay(
    lst_data: np.ndarray, 
    ndvi_data: np.ndarray = None,
    cmap_name: str = "magma", 
    opacity: float = 0.75
) -> tuple[np.ndarray, float, float]:
    """
    Converts 2D LST array into an RGBA image array.
    Masks out deep water bodies (NDVI < -0.05 or extreme cold outliers)
    so the natural basemap water shows through without a blocky bounding box.
    Returns the RGBA array and the calibrated min/max temperature values.
    """
    valid_mask = ~np.isnan(lst_data) & (lst_data > -50.0)
    
    # Mask out open water (negative NDVI) so Lake Michigan / rivers remain transparent
    if ndvi_data is not None:
        valid_mask = valid_mask & (ndvi_data >= -0.05)

    if not np.any(valid_mask):
        empty = np.zeros((lst_data.shape[0], lst_data.shape[1], 4), dtype=np.uint8)
        return empty, 0.0, 50.0

    c_vmin = float(np.nanpercentile(lst_data[valid_mask], 2))
    c_vmax = float(np.nanpercentile(lst_data[valid_mask], 98))

    normed = np.zeros_like(lst_data, dtype=np.float32)
    normed[valid_mask] = np.clip((lst_data[valid_mask] - c_vmin) / (c_vmax - c_vmin + 1e-6), 0.0, 1.0)

    cmap = plt.get_cmap(cmap_name)
    colored = cmap(normed)

    rgba = (colored * 255).astype(np.uint8)
    rgba[~valid_mask, 3] = 0  # Fully transparent for nodata & open water
    rgba[valid_mask, 3] = int(opacity * 255)

    return rgba, c_vmin, c_vmax


def create_folium_legend(vmin: float, vmax: float):
    """Creates a Branca linear colormap legend matching Matplotlib's Magma palette."""
    magma_hex = ['#000004', '#1C1044', '#4F127B', '#812581', '#B63679', '#E15152', '#F98335', '#FEC98D', '#FCFDBF']
    colormap = cm.LinearColormap(
        colors=magma_hex,
        vmin=round(vmin, 1),
        vmax=round(vmax, 1),
        caption="Land Surface Temperature (°C)"
    )
    return colormap


def array_to_colormap_image(data: np.ndarray, cmap_name: str = "magma", vmin: float = None, vmax: float = None) -> Image.Image:
    """Converts a 2D numpy array into a PIL Image via Matplotlib colormap."""
    valid_mask = ~np.isnan(data) & (data > -50.0)
    if not np.any(valid_mask):
        return Image.fromarray(np.zeros((data.shape[0], data.shape[1], 3), dtype=np.uint8))

    c_vmin = np.nanpercentile(data[valid_mask], 2) if vmin is None else vmin
    c_vmax = np.nanpercentile(data[valid_mask], 98) if vmax is None else vmax

    normed = np.zeros_like(data, dtype=np.float32)
    normed[valid_mask] = np.clip((data[valid_mask] - c_vmin) / (c_vmax - c_vmin + 1e-6), 0.0, 1.0)

    cmap = plt.get_cmap(cmap_name)
    rgb = (cmap(normed)[:, :, :3] * 255).astype(np.uint8)
    rgb[~valid_mask] = 0
    return Image.fromarray(rgb)


def generate_true_color(red: np.ndarray, nir: np.ndarray, swir: np.ndarray) -> Image.Image:
    """Generates a False Color SWIR-2/NIR/Red (B6-B5-B4) composite."""
    def stretch(band):
        valid = band > 0
        if not np.any(valid):
            return np.zeros_like(band, dtype=np.uint8)
        p2, p98 = np.percentile(band[valid], (2, 98))
        stretched = np.clip((band - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)
        return (stretched * 255).astype(np.uint8)

    r = stretch(swir)
    g = stretch(nir)
    b = stretch(red)
    return Image.fromarray(np.dstack([r, g, b]))


def create_interactive_scatter_density(ndvi: np.ndarray, lst: np.ndarray) -> go.Figure:
    """Generates an interactive Plotly 2D density contour & scatter for NDVI vs LST."""
    valid = (ndvi > -0.5) & (lst > -20.0)
    sampled_indices = np.random.choice(np.where(valid.ravel())[0], size=min(12000, np.sum(valid)), replace=False)

    x = ndvi.ravel()[sampled_indices]
    y = lst.ravel()[sampled_indices]

    fig = go.Figure()

    fig.add_trace(go.Histogram2dContour(
        x=x,
        y=y,
        colorscale='Magma',
        reversescale=True,
        xaxis='x',
        yaxis='y',
        name='Pixel Density'
    ))

    fig.add_trace(go.Scatter(
        x=x[::4],
        y=y[::4],
        mode='markers',
        showlegend=False,
        marker=dict(
            symbol='circle',
            opacity=0.35,
            color='#00FFAA',
            size=3
        ),
        hovertemplate='NDVI: %{x:.3f}<br>LST: %{y:.1f}°C<extra></extra>'
    ))

    fig.update_layout(
        template="plotly_dark",
        title="Biophysical Microclimate Response: Surface Temperature vs. NDVI",
        xaxis_title="Normalized Difference Vegetation Index (NDVI)",
        yaxis_title="Land Surface Temperature (°C)",
        margin=dict(l=40, r=40, t=50, b=40),
        plot_bgcolor="#12141A",
        paper_bgcolor="#12141A",
        font=dict(color="#F0F2F6"),
        hovermode="closest",
    )
    return fig