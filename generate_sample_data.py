"""
generate_sample_data.py
Creates a realistic 500x500 multi-band GeoTIFF test dataset modeling
an urban core, surrounding suburbs, a river corridor, and a city park.
"""

import os
import numpy as np
import rasterio
from rasterio.transform import from_origin

os.makedirs("data/raw", exist_ok=True)

height, width = 500, 500
transform = from_origin(580000, 4500000, 30, 30)  # 30-meter Landsat pixel resolution

# Base grids: X and Y coordinates
y, x = np.ogrid[:height, :width]

# 1. Define geographic features
# A river cutting diagonally
river = (y - 0.7 * x + 30)**2 < 200

# An urban concrete core in the center
center_dist = np.sqrt((x - 250)**2 + (y - 250)**2)
urban_core = center_dist < 120

# A large central park inside the urban core
park = (center_dist < 40)

# 2. Synthesize raw DN for Red (Band 4)
red_dn = np.full((height, width), 9000, dtype=np.uint16)      # baseline soil/suburbs
red_dn[urban_core] = 14000                                   # concrete reflects red
red_dn[park] = 7800                                          # vegetation absorbs red
red_dn[river] = 7400                                         # water absorbs red

# 3. Synthesize raw DN for NIR (Band 5)
nir_dn = np.full((height, width), 16000, dtype=np.uint16)    # suburbs moderate NIR
nir_dn[urban_core] = 12000                                   # concrete low NIR
nir_dn[park] = 24000                                         # high chlorophyll reflectance
nir_dn[river] = 7300                                         # water strongly absorbs NIR

# 4. Synthesize raw DN for SWIR1 (Band 6)
swir_dn = np.full((height, width), 14000, dtype=np.uint16)
swir_dn[urban_core] = 19000                                  # concrete reflects high SWIR
swir_dn[park] = 9000
swir_dn[river] = 7200

# 5. Synthesize raw DN for Thermal Band 10 (Surface Temperature)
# Formula: DN = (Kelvin - 149.0) / 0.00341802
# Target Temps: River ~20°C (293.15K), Park ~24°C (297.15K), Suburb ~28°C (301.15K), Urban ~37°C (310.15K)
def c_to_dn(celsius):
    k = celsius + 273.15
    return int((k - 149.0) / 0.00341802)

thermal_dn = np.full((height, width), c_to_dn(28.0), dtype=np.uint16)
thermal_dn[urban_core] = c_to_dn(37.5)                       # UHI Hotspot
thermal_dn[park] = c_to_dn(24.0)                             # Park Cool Island
thermal_dn[river] = c_to_dn(19.5)                            # Water cooling

# Add natural spatial noise
noise = np.random.randint(-150, 150, (height, width), dtype=np.int32)
thermal_dn = np.clip(thermal_dn.astype(np.int32) + noise, 1, 65535).astype(np.uint16)

# Save individual GeoTIFF files matching Landsat naming schema
bands = {
    "data/raw/sample_B4.TIF": red_dn,
    "data/raw/sample_B5.TIF": nir_dn,
    "data/raw/sample_B6.TIF": swir_dn,
    "data/raw/sample_B10.TIF": thermal_dn,
}

meta = {
    'driver': 'GTiff',
    'dtype': 'uint16',
    'nodata': 0,
    'width': width,
    'height': height,
    'count': 1,
    'crs': 'EPSG:32618',  # UTM Zone 18N
    'transform': transform
}

for filepath, data in bands.items():
    with rasterio.open(filepath, 'w', **meta) as dst:
        dst.write(data, 1)

print("Sample Landsat 8/9 scenes generated successfully in data/raw/")