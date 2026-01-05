import json
import math
import os
import logging
from typing import Tuple, Dict

import numpy as np
import rasterio
from rasterio.transform import Affine
from shapely.geometry import Polygon
from pyproj import CRS

logger = logging.getLogger("frp.utils")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_raster(path: str, arr, meta: dict) -> None:
    ensure_dir(os.path.dirname(path))
    meta2 = meta.copy()
    # ensure transform serializable
    if isinstance(meta2.get("transform"), Affine):
        t = meta2["transform"]
        meta2["transform"] = [t.a, t.b, t.c, t.d, t.e, t.f]
    with rasterio.open(path, "w", **meta2) as dst:
        if arr.ndim == 2:
            dst.write(arr, 1)
        else:
            dst.write(arr)
    logger.info("Wrote raster %s", path)


def parse_weights(s: str) -> Dict[str, float]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    out = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip()] = float(v)
    return out


def make_demo_data(output_dir: str) -> Dict[str, str]:
    """Create synthetic red/nir rasters and AOI geojson in output_dir and return paths."""
    from shapely.geometry import box
    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    ensure_dir(output_dir)
    inputs = os.path.join(output_dir, "inputs")
    ensure_dir(inputs)

    # Create a square AOI in lat/lon around -0.1,51.5
    minx, miny, maxx, maxy = (-0.12, 51.48, -0.08, 51.52)
    poly = box(minx, miny, maxx, maxy)
    gdf = gpd.GeoDataFrame({"geometry": [poly]}, crs="EPSG:4326")
    aoi_path = os.path.join(inputs, "aoi.geojson")
    gdf.to_file(aoi_path, driver="GeoJSON")

    # Create small synthetic rasters in WGS84 with coarse approximation for demo
    width = 200
    height = 200
    res = 10  # meters; not accurate for latlon but fine for demo
    transform = from_origin(minx, maxy, 0.0001, 0.0001)

    # Synthetic red and nir bands
    red = np.linspace(50, 150, width * height).reshape((height, width)).astype("float32")
    nir = np.linspace(100, 200, width * height).reshape((height, width)).astype("float32")

    red_path = os.path.join(inputs, "red.tif")
    nir_path = os.path.join(inputs, "nir.tif")
    meta = {"driver": "GTiff", "dtype": "float32", "count": 1, "crs": "EPSG:4326", "transform": transform, "width": width, "height": height}
    with rasterio.open(red_path, "w", **meta) as dst:
        dst.write(red, 1)
    with rasterio.open(nir_path, "w", **meta) as dst:
        dst.write(nir, 1)

    return {"aoi": aoi_path, "red": red_path, "nir": nir_path}
