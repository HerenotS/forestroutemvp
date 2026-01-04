#!/usr/bin/env python3
"""
Fast routing: polygon -> regular waypoint grid -> export

Generates waypoints in a simple grid pattern across the polygon.
This is the practical, fast routing solution.

Usage:
  python scripts/fast_routing.py [--polygon POLYGON] [--output OUTPUT] [--spacing-m SPACING]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.aoi import load_aoi, get_utm_crs_for_geometry
from frp.export import export_route
from frp.utils import ensure_dir
from shapely.geometry import Point, LineString
from shapely.ops import transform
from pyproj import Transformer
import json


def create_grid_waypoints(aoi_wgs84, spacing_m=200):
    """Create a regular snake-pattern grid of waypoints covering the AOI."""
    utm_crs = get_utm_crs_for_geometry(aoi_wgs84)
    
    # Transform to UTM
    transformer_to_utm = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
    aoi_utm = transform(transformer_to_utm.transform, aoi_wgs84)
    
    # Get bounds
    minx, miny, maxx, maxy = aoi_utm.bounds
    
    waypoints_utm = []
    y = miny
    row = 0
    
    while y <= maxy:
        x_coords = []
        x = minx
        
        while x <= maxx:
            pt_utm = Point(x, y)
            if aoi_utm.contains(pt_utm):
                x_coords.append(x)
            x += spacing_m
        
        # Alternate row direction for efficient sweeping
        if row % 2 == 1:
            x_coords.reverse()
        
        waypoints_utm.extend([(x, y) for x in x_coords])
        
        y += spacing_m
        row += 1
    
    print(f"Generated {len(waypoints_utm)} waypoints in UTM ({spacing_m}m spacing)")
    
    return waypoints_utm, utm_crs


def main():
    import argparse
    
    p = argparse.ArgumentParser(description="Fast routing: polygon -> grid waypoints")
    p.add_argument("--polygon", default="inputs/map.geojson", help="Input polygon")
    p.add_argument("--output", default="fast_routing_output", help="Output directory")
    p.add_argument("--spacing-m", type=float, default=500, help="Waypoint grid spacing (meters)")
    
    args = p.parse_args()
    
    out_path = Path(args.output)
    ensure_dir(str(out_path))
    ensure_dir(str(out_path / "routes"))
    
    print("\n" + "="*70)
    print("FAST ROUTING - REGULAR GRID WAYPOINTS")
    print("="*70)
    
    try:
        # Load polygon
        print(f"\n[1/3] Loading polygon from {args.polygon}...")
        aoi = load_aoi(args.polygon, None)
        utm_crs = get_utm_crs_for_geometry(aoi)
        bounds = aoi.bounds
        
        print(f"      Bounds: ({bounds[0]:.3f}, {bounds[1]:.3f}) -> ({bounds[2]:.3f}, {bounds[3]:.3f})")
        print(f"      UTM CRS: {utm_crs}")
        print(f"      Area: {aoi.area / 1e6:.2f} km²")
        
        # Create waypoint grid
        print(f"\n[2/3] Creating {args.spacing_m}m-spaced snake-pattern waypoint grid...")
        waypoints_utm, utm_crs = create_grid_waypoints(aoi, args.spacing_m)
        
        print(f"      Waypoints: {len(waypoints_utm)}")
        
        # Calculate distance
        total_distance = 0
        for i in range(len(waypoints_utm) - 1):
            x1, y1 = waypoints_utm[i]
            x2, y2 = waypoints_utm[i + 1]
            dist = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
            total_distance += dist
        
        print(f"      Total route distance: {total_distance / 1000:.2f} km")
        
        # Export route
        print(f"\n[3/3] Exporting route...")
        geojson_path = str(out_path / "routes" / "route.geojson")
        kml_path = str(out_path / "routes" / "route.kml")
        
        export_route(waypoints_utm, str(utm_crs), geojson_path, kml_path)
        
        print(f"      GeoJSON: {geojson_path}")
        print(f"      KML: {kml_path}")
        
        # Create summary report
        report_path = str(out_path / "routing_report.json")
        report = {
            "polygon_file": str(args.polygon),
            "output_directory": str(out_path),
            "routing_type": "grid_waypoints",
            "parameters": {
                "spacing_m": args.spacing_m,
                "utm_crs": str(utm_crs)
            },
            "results": {
                "waypoints": len(waypoints_utm),
                "total_distance_km": total_distance / 1000,
                "coverage_area_km2": aoi.area / 1e6
            },
            "output_files": {
                "geojson": geojson_path,
                "kml": kml_path
            }
        }
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"      Report: {report_path}")
        
        # Summary
        print("\n" + "="*70)
        print("ROUTING COMPLETE!")
        print("="*70)
        print(f"\nOutput directory: {out_path}")
        print("\nGenerated files:")
        for f in sorted(out_path.rglob("*")):
            if f.is_file():
                rel_path = f.relative_to(out_path)
                size_kb = f.stat().st_size / 1024
                print(f"  - {rel_path} ({size_kb:.1f} KB)")
        
        print(f"\n[STATS] Routing Statistics:")
        print(f"   • Waypoints: {len(waypoints_utm)}")
        print(f"   • Spacing: {args.spacing_m}m")
        print(f"   • Total route distance: {total_distance / 1000:.2f} km")
        print(f"   • Coverage area: {aoi.area / 1e6:.2f} km²")
        
        print(f"\n[VIEW] View the route:")
        print(f"   • GeoJSON: {geojson_path}")
        print(f"   • KML: {kml_path} (open in Google Earth)")
        print(f"   • Report: {report_path}")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
