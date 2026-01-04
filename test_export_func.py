from frp.aoi import load_aoi, get_utm_crs_for_geometry
from frp.export import export_route
from frp.utils import ensure_dir
from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Transformer
from pathlib import Path

print("Loading polygon...")
aoi = load_aoi("inputs/map.geojson", None)
utm_crs = get_utm_crs_for_geometry(aoi)

print("Creating test waypoints...")
transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
aoi_utm = transform(transformer.transform, aoi)
minx, miny, maxx, maxy = aoi_utm.bounds

waypoints = []
for x in range(int(minx), int(minx) + 2000, 500):
    for y in range(int(miny), int(miny) + 2000, 500):
        pt = Point(x, y)
        if aoi_utm.contains(pt):
            waypoints.append((x, y))

print(f"Generated {len(waypoints)} test waypoints")

out_path = Path("test_export")
ensure_dir(str(out_path / "routes"))

print("Exporting...")
export_route(waypoints, str(utm_crs), 
             str(out_path / "routes" / "test.geojson"),
             str(out_path / "routes" / "test.kml"))

print("Export complete!")
print(f"Files created:")
for f in (out_path / "routes").glob("*"):
    print(f"  - {f.name}")
