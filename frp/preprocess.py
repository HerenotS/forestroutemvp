import logging
import math
from typing import Tuple, Optional

import numpy as np
import rasterio
from rasterio import features
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import transform_geom
from shapely.geometry import mapping
from pyproj import CRS, Transformer

from frp.aoi import get_utm_crs_for_geometry

logger = logging.getLogger("frp.preprocess")


def reproject_and_clip(
    src_path: str,
    aoi_geom,  # shapely geometry in EPSG:4326
    target_resolution: float,
) -> Tuple[np.ndarray, dict, CRS]:
    """Reproject source raster to UTM (computed from AOI), clip to AOI and resample to target_resolution (meters).

    Returns (array (1, H, W) or (H, W)), metadata, utm_crs
    """
    with rasterio.open(src_path) as src:
        src_crs = CRS.from_user_input(src.crs)
        utm_crs = get_utm_crs_for_geometry(aoi_geom)

        # determine bounds of AOI in UTM meters
        transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
        minx, miny, maxx, maxy = aoi_geom.bounds
        minx_u, miny_u = transformer.transform(minx, miny)
        maxx_u, maxy_u = transformer.transform(maxx, maxy)
        # ensure min/max ordering
        left, right = min(minx_u, maxx_u), max(minx_u, maxx_u)
        bottom, top = min(miny_u, maxy_u), max(miny_u, maxy_u)

        width = int(math.ceil((right - left) / target_resolution))
        height = int(math.ceil((top - bottom) / target_resolution))
        transform = from_origin(left, top, target_resolution, target_resolution)

        dst_meta = src.meta.copy()
        dst_meta.update({
            "crs": utm_crs.to_string(),
            "transform": transform,
            "width": width,
            "height": height,
            "count": 1,
            "dtype": "float32",
        })

        # prepare destination array
        dst = np.zeros((height, width), dtype="float32")

        rasterio.warp.reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=utm_crs.to_string(),
            resampling=Resampling.bilinear,
            num_threads=2,
        )

        # mask out outside AOI by transforming AOI to UTM and making a mask
        aoi_utm = transform_geom("EPSG:4326", utm_crs.to_string(), mapping(aoi_geom))
        mask = features.geometry_mask([aoi_utm], out_shape=(height, width), transform=transform, invert=True)
        dst[~mask] = np.nan

        logger.info("Reprojected %s -> %s, shape=%s", src_path, utm_crs.to_string(), dst.shape)
        return dst, dst_meta, utm_crs
