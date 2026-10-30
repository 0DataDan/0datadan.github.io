"""
download_real_scene.py
Programmatically queries and downloads Landsat 8/9 Level-2 bands
for selectable global metropolitan areas across contrasting urban biomes.
Includes exponential backoff retry handling for Azure/STAC rate limits.
"""

import os
import time
import requests
import rasterio
from rasterio.windows import Window

STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

# Target metropolitan coordinates [min_lon, min_lat, max_lon, max_lat]
METRO_REGISTRY = {
    "phoenix": {
        "label": "Phoenix, AZ (Arid Desert)",
        "bbox": [-112.15, 33.40, -111.95, 33.55],
        "date_range": "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z",
        "crop_offset": (4000, 4000),
    },
    "atlanta": {
        "label": "Atlanta, GA (Humid Forest)",
        "bbox": [-84.45, 33.70, -84.30, 33.85],
        "date_range": "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z",
        "crop_offset": (3800, 3800),
    },
    "chicago": {
        "label": "Chicago, IL (Temperate Lakefront)",
        "bbox": [-87.72, 41.82, -87.58, 41.95],
        "date_range": "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z",
        "crop_offset": (3600, 3600),
    },
}

band_keys = {
    "B4.TIF": "red",
    "B5.TIF": "nir08",
    "B6.TIF": "swir16",
    "B10.TIF": "lwir11"
}


def download_city_scene(city_key: str):
    if city_key not in METRO_REGISTRY:
        raise ValueError(f"Unknown city key: {city_key}")

    cfg = METRO_REGISTRY[city_key]
    out_dir = os.path.join("data", "raw", city_key)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n--- Ingesting {cfg['label']} ---")

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

    crop_window = Window(col_off=cfg["crop_offset"][0], row_off=cfg["crop_offset"][1], width=600, height=600)

    for file_suffix, asset_key in band_keys.items():
        local_path = os.path.join(out_dir, f"{city_key}_{file_suffix}")
        if os.path.exists(local_path):
            print(f"  ✓ {os.path.basename(local_path)} already cached.")
            continue

        raw_href = assets[asset_key]["href"]
        
        # Retry loop for SAS signing and rasterio streaming
        max_retries = 4
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                time.sleep(1.5)  # Throttle requests to avoid 409 concurrency conflicts
                sign_res = requests.get(f"{SIGN_URL}?href={raw_href}")
                signed_url = sign_res.json().get("href", raw_href) if sign_res.status_code == 200 else raw_href

                with rasterio.open(signed_url) as src:
                    cropped_data = src.read(1, window=crop_window)
                    crop_transform = rasterio.windows.transform(crop_window, src.transform)
                    meta = src.meta.copy()
                    meta.update({
                        "height": 600,
                        "width": 600,
                        "transform": crop_transform,
                        "nodata": 0
                    })
                    with rasterio.open(local_path, "w", **meta) as dst:
                        dst.write(cropped_data, 1)

                print(f"  ✓ Ingested {os.path.basename(local_path)}")
                success = True
                break
            except Exception as e:
                print(f"  [Attempt {attempt}/{max_retries}] Connection warning: {e}. Retrying in {attempt * 2}s...")
                time.sleep(attempt * 2)

        if not success:
            raise RuntimeError(f"Failed to ingest {file_suffix} after {max_retries} attempts.")


if __name__ == "__main__":
    for city in METRO_REGISTRY.keys():
        download_city_scene(city)
    print("\n✓ All urban climate datasets successfully synchronized to data/raw/!")