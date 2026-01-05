import logging
from typing import List, Optional

import geopandas as gpd
import shapely.geometry as geom
from shapely.ops import split
from pyproj import CRS

from frp.aoi import get_utm_crs_for_geometry

logger = logging.getLogger("frp.coverage")


def plan_coverage(aoi_geom: geom.Polygon, utm_crs: CRS, resolution: float, tile_size: int, sweep_spacing_m: Optional[float] = None) -> List[geom.LineString]:
    """Generate simple lawnmower sweep lines within AOI in UTM coordinates.

    Args:
        aoi_geom: Polygon geometry in EPSG:4326 (WGS84)
        utm_crs: CRS object for UTM coordinates
        resolution: Raster resolution in meters
        tile_size: Tile size for processing
        sweep_spacing_m: Spacing between sweep lines in meters. If None, defaults to 10x resolution.

    Returns:
        List of shapely LineString geometries in UTM coordinates
    """
    # transform AOI to utm (aoi_geom is already in 4326)
    import shapely.ops as ops
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
    aoi_utm = ops.transform(transformer.transform, aoi_geom)

    minx, miny, maxx, maxy = aoi_utm.bounds
    # spacing between sweeps: default based on resolution (10x) or provided value
    if sweep_spacing_m is None:
        spacing = resolution * 10 if resolution * 10 > 10 else 50
    else:
        spacing = float(sweep_spacing_m)

    lines = []
    y = miny
    toggle = False
    while y <= maxy:
        line = geom.LineString([(minx, y), (maxx, y)])
        inter = line.intersection(aoi_utm)
        if not inter.is_empty:
            # may be MultiLineString or LineString
            if isinstance(inter, geom.LineString):
                segment = inter
                lines.append(segment if not toggle else geom.LineString(list(segment.coords)[::-1]))
            else:
                # handle MultiLineString or other multi-geometry results
                if inter.geom_type == "MultiLineString":
                    # Shapely 2.0+ compatibility: iterate over inter.geoms instead of 'for seg in inter',
                    # since direct iteration over geometry objects changed and would break in 2.x.
                    for seg in inter:
                        if seg.length > 0:
                            lines.append(seg if not toggle else geom.LineString(list(seg.coords)[::-1]))
                # ignore points or unexpected intersection types
        y += spacing
        toggle = not toggle

    logger.info("Planned %d sweep lines", len(lines))
    return lines
