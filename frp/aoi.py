import json
import logging
from typing import Optional

import geopandas as gpd
from shapely.geometry import box, Polygon, shape
from shapely.ops import unary_union
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
        try:
            # Try reading with geopandas first
            gdf = gpd.read_file(geojson_path)
            if not gdf.empty:
                geom = None
                if hasattr(gdf.geometry, "union_all"):
                    try:
                        geom = gdf.geometry.union_all()
                    except Exception:
                        geom = gdf.unary_union
                else:
                    geom = gdf.unary_union
                logger.info("Loaded AOI from %s using geopandas", geojson_path)
                return geom
        except Exception as e:
            logger.debug("Geopandas read failed, trying raw JSON: %s", e)
        
        # Fallback: load from raw JSON using shapely
        try:
            with open(geojson_path, 'r') as f:
                data = json.load(f)
            
            if data.get('features'):
                geometries = []
                for feat in data['features']:
                    geom_dict = feat.get('geometry', {})
                    if geom_dict:
                        try:
                            geom = shape(geom_dict)
                            if geom.is_valid:
                                geometries.append(geom)
                        except Exception as e:
                            logger.warning("Could not load geometry: %s", e)
                
                if geometries:
                    # Union all geometries
                    if len(geometries) == 1:
                        result = geometries[0]
                    else:
                        from shapely.ops import unary_union
                        result = unary_union(geometries)
                    logger.info("Loaded AOI from %s using shapely", geojson_path)
                    return result
        except Exception as e:
            logger.error("Failed to load AOI from %s: %s", geojson_path, e)
        
        raise ValueError(f"Could not load AOI from {geojson_path}")

    raise ValueError("Either geojson_path or bbox must be provided")


def get_utm_crs_for_geometry(geom: Polygon) -> CRS:
    lon = geom.representative_point().x
    lat = geom.representative_point().y
    zone = int((lon + 180) / 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)
