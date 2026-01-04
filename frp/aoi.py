import json
import logging
from typing import Optional

import geopandas as gpd
from shapely.geometry import shape, mapping, box, Polygon
from pyproj import CRS

logger = logging.getLogger("frp.aoi")


def load_aoi(geojson_path: Optional[str], bbox: Optional[str]) -> Polygon:
    """Load AOI polygon from GeoJSON file or bbox string (minLon,minLat,maxLon,maxLat).

    Returns geometry in EPSG:4326 (lon/lat).
    """
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must be minLon,minLat,maxLon,maxLat")
        minx, miny, maxx, maxy = parts
        geom = box(minx, miny, maxx, maxy)
        logger.info("Loaded AOI from bbox: %s", parts)
        return geom

    if geojson_path:
        gdf = gpd.read_file(geojson_path)
        if gdf.empty:
            raise ValueError("AOI GeoJSON contains no features")
        geom = gdf.unary_union
        logger.info("Loaded AOI from %s", geojson_path)
        return geom

    raise ValueError("Either geojson_path or bbox must be provided")


def get_utm_crs_for_geometry(geom: Polygon) -> CRS:
    lon = geom.representative_point().x
    lat = geom.representative_point().y
    zone = int((lon + 180) / 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)
