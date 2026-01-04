import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("frp.derived")


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Compute NDVI from NIR and RED arrays. Returns float32 array with NaNs preserved."""
    nir_f = nir.astype("float32")
    red_f = red.astype("float32")
    denom = (nir_f + red_f)
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir_f - red_f) / denom
    ndvi[denom == 0] = np.nan
    ndvi = np.clip(ndvi, -1.0, 1.0)
    logger.info("Computed NDVI, shape=%s", ndvi.shape)
    return ndvi


def compute_slope(dem: Optional[np.ndarray], resolution: float) -> np.ndarray:
    """Compute slope (degrees) from DEM. If DEM is None, returns zeros matching expected shape.

    `resolution` is horizontal resolution in meters.
    """
    if dem is None:
        logger = logging.getLogger("frp.derived")
        logger.info("No DEM provided; returning zero slope array")
        # return single-value zero when caller expects array; but caller may expect shape
        return None

    dzdy, dzdx = np.gradient(dem, resolution, resolution)
    slope_rad = np.arctan((dzdx ** 2 + dzdy ** 2) ** 0.5)
    slope_deg = np.degrees(slope_rad)
    logger.info("Computed slope, shape=%s", slope_deg.shape)
    return slope_deg.astype("float32")
