import json
import logging
from typing import List, Tuple

import geopandas as gpd
from shapely.geometry import Point, mapping
import simplekml
from pyproj import Transformer

logger = logging.getLogger("frp.export")


def export_route(points_utm: List[Tuple[float, float]], utm_crs, geojson_path: str, kml_path: str, geojson_geometry: str = "linestring") -> None:
    """Export route points (UTM coords) to GeoJSON and KML in WGS84 lat/lon.

    geojson_geometry: 'points' or 'linestring'
    """
    if not points_utm:
        logger.warning("No points to export")
        return

    transformer = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)
    coords_wgs = [transformer.transform(x, y) for x, y in points_utm]

    # GeoJSON
    if geojson_geometry == "points":
        features = []
        for lon, lat in coords_wgs:
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {}})
        gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    else:
        # default linestring
        line = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': coords_wgs}, 'properties': {}}
        gdf = gpd.GeoDataFrame.from_features([line], crs="EPSG:4326")

    gdf.to_file(geojson_path, driver="GeoJSON")

    # KML: write a LineString for visualization
    kml = simplekml.Kml()
    ls = kml.newlinestring(name="route", coords=coords_wgs)
    ls.altitudemode = simplekml.AltitudeMode.clamptoground
    ls.style.linestyle.width = 3
    kml.save(kml_path)

    logger.info("Exported route to %s and %s", geojson_path, kml_path)
