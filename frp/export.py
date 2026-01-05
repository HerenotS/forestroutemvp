import logging
from typing import List, Tuple, Union

import geopandas as gpd
import simplekml
from pyproj import Transformer, CRS

logger = logging.getLogger("frp.export")


def export_route(points_utm: List[Tuple[float, float]], utm_crs: Union[str, CRS], geojson_path: str, kml_path: str, geojson_geometry: str = "linestring") -> None:
    """Export route points (UTM coords) to GeoJSON and KML in WGS84 lat/lon.

    Args:
        points_utm: List of (x, y) coordinates in UTM
        utm_crs: CRS object or EPSG string for UTM coordinates
        geojson_path: Output path for GeoJSON file
        kml_path: Output path for KML file
        geojson_geometry: 'points' or 'linestring' (default: 'linestring')
    """
    if not points_utm:
        logger.warning("No points to export")
        return

    # Ensure utm_crs is a CRS object
    if isinstance(utm_crs, str):
        utm_crs = CRS.from_string(utm_crs)
    
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
