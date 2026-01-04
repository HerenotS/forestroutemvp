import logging
from typing import Tuple

import numpy as np
import rasterio

logger = logging.getLogger("frp.costmap")


def build_cost_map(ndvi: np.ndarray, slope: np.ndarray, meta: dict, weights: dict = None) -> Tuple[np.ndarray, dict]:
    """Build cost map combining slope and NDVI. Returns cost array and meta.

    weights: {'slope': float, 'ndvi': float}
    """
    if weights is None:
        weights = {"slope": 0.5, "ndvi": 0.5}

    # normalize slope
    if slope is None:
        slope_norm = np.zeros_like(ndvi, dtype="float32")
    else:
        s = np.nan_to_num(slope, nan=0.0)
        maxs = s.max() if s.size and s.max() > 0 else 1.0
        slope_norm = s / float(maxs)

    # normalize ndvi to 0-1
    nd = np.nan_to_num(ndvi.copy(), nan=0.0)
    nd_min = float(np.nanmin(nd)) if nd.size else -1.0
    nd_max = float(np.nanmax(nd)) if nd.size else 1.0
    if nd_max - nd_min == 0:
        ndvi_norm = np.zeros_like(nd)
    else:
        ndvi_norm = (nd - nd_min) / (nd_max - nd_min)

    cost = weights.get("slope", 0.5) * slope_norm + weights.get("ndvi", 0.5) * (1.0 - ndvi_norm)
    cost = cost.astype("float32")

    out_meta = meta.copy()
    out_meta.update({"dtype": "float32", "count": 1})
    logger.info("Built cost map, shape=%s", cost.shape)
    return cost, out_meta
