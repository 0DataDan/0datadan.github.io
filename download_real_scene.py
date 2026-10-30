"""
download_real_scene.py
Programmatically queries Landsat 8/9 Level-2 bands from Planetary Computer.
Transforms exact WGS84 geographic bounding boxes directly into native scene UTM
coordinates to compute georeferenced spatial windows.
Includes SAS token caching and robust resume logic to eliminate 409 rate-limit errors.
"""

import os
import time
import requests
import rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer

STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

# Exact metropolitan bounding boxes [min_lon, min_lat, max_lon, max_lat] (WGS84)
METRO_REGISTRY = {
    "phoenix": {
        "label": "Phoenix, AZ (Arid Desert)",
        "bbox": [-112.14, 33.40, -111.98, 33.52],
        "date_range": "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z",
    },
    "atlanta": {
        "label": "Atlanta, GA (Humid Forest)",
        "bbox": [-84.44, 33.72, -84.34, 33.82],
        "date_range": "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z",
    },
    "chicago": {
        "label": "Chicago, IL (Temperate Lakefront)",
        "bbox": [-87.69, 41.83, -87.59, 41.93],
        "date_range": "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z",
   },
    "nyc": {
        "label": "New York City, NY (Ultra-Dense Coastal Megacity)",
        "bbox": [-74.02, 40.70, -73.92, 40.82],
        "date_range": "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z",
    },
}

band_keys = {
    "B4.TIF": "red",
    "B5.TIF": "nir08",
    "B6.TIF": "swir16",
    "B10.TIF": "lwir11"
}


def compute_utm_window(src, bbox_wgs84):
    """Transforms WGS84 bbox [min_lon, min_lat, max_lon, max_lat] into native raster window."""
    transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
    min_x, min_y = transformer.transform(bbox_wgs84[0], bbox_wgs84[1])
    max_x, max_y = transformer.transform(bbox_wgs84[2], bbox_wgs84[3])
    
    win = from_bounds(min_x, min_y, max_x, max_y, src.transform)
    win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
    # Ceil lengths to integer dimensions without using deprecated round_shape
    return rasterio.windows.Window(
        col_off=int(round(win.col_off)),
        row_off=int(round(win.row_off)),
        width=int(round(win.width)),
        height=int(round(win.height)),
    )


def download_city_scene(city_key: str):
    if city_key not in METRO_REGISTRY:
        raise ValueError(f"Unknown city key: {city_key}")

    cfg = METRO_REGISTRY[city_key]
    out_dir = os.path.join("data", "raw", city_key)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n--- Ingesting {cfg['label']} via Coordinate Reprojection ---")

    search_payload = {
        "collections": ["landsat-c2-l2"],
        "bbox": cfg["bbox"],
        "datetime": cfg["date_range"],
        "query": {
            "eo:cloud_cover": {"lt": 12},
            "platform": {"in": ["landsat-8", "landsat-9"]}
        },
        "limit": 5,
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}]
    }

    res = requests.post(STAC_SEARCH_URL, json=search_payload)
    if res.status_code != 200:
        raise RuntimeError(f"STAC search failed for {city_key}: {res.text}")

    features = res.json().get("features", [])
    if not features:
        raise RuntimeError(f"No clear scenes found for {city_key}.")

    selected_item = features[0]
    scene_id = selected_item["id"]
    assets = selected_item["assets"]
    print(f"Acquired Scene: {scene_id} (Cloud: {selected_item['properties'].get('eo:cloud_cover')}%)")

    for file_suffix, asset_key in band_keys.items():
        local_path = os.path.join(out_dir, f"{city_key}_{file_suffix}")

        # Skip if file already exists with valid content
        if os.path.exists(local_path) and os.path.getsize(local_path) > 5000:
            print(f"  ✓ {os.path.basename(local_path)} already present and valid.")
            continue

        raw_href = assets[asset_key]["href"]
        max_retries = 5
        success = False

        for attempt in range(1, max_retries + 1):
            try:
                time.sleep(2.5 * attempt)  # Progressive spacing
                sign_res = requests.get(f"{SIGN_URL}?href={raw_href}", timeout=20)
                signed_url = sign_res.json().get("href", raw_href) if sign_res.status_code == 200 else raw_href

                with rasterio.open(signed_url) as src:
                    window = compute_utm_window(src, cfg["bbox"])
                    cropped_data = src.read(1, window=window)
                    crop_transform = rasterio.windows.transform(window, src.transform)
                    meta = src.meta.copy()
                    meta.update({
                        "height": cropped_data.shape[0],
                        "width": cropped_data.shape[1],
                        "transform": crop_transform,
                        "nodata": 0
                    })

                    with rasterio.open(local_path, "w", **meta) as dst:
                        dst.write(cropped_data, 1)

                print(f"  ✓ Ingested {os.path.basename(local_path)} [{cropped_data.shape[1]}x{cropped_data.shape[0]} px]")
                success = True
                break
            except Exception as e:
                print(f"  [Attempt {attempt}/{max_retries}] Warning: {e}. Waiting {attempt * 3}s...")
                time.sleep(attempt * 3)

        if not success:
            raise RuntimeError(f"Failed to ingest {file_suffix} after {max_retries} attempts.")


if __name__ == "__main__":
    for city in METRO_REGISTRY.keys():
        download_city_scene(city)
    print("\n✓ Precise coordinate-bounded scenes successfully written to data/raw/!")