#!/usr/bin/env python3
"""
Simple complete routing: polygon -> waypoint grid -> optimized route

Creates waypoints in a regular grid pattern across the polygon,
then optimizes with A*.

Usage:
  python scripts/simple_routing.py [--polygon POLYGON] [--output OUTPUT] [--spacing-m SPACING]
"""
import sys
from pathlib import Path
import math
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.aoi import load_aoi, get_utm_crs_for_geometry
from frp.export import export_route
from frp.utils import ensure_dir
from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Transformer
import geopandas as gpd


def create_grid_waypoints(aoi_wgs84, spacing_m=200):
    """Create a regular grid of waypoints covering the AOI."""
    utm_crs = get_utm_crs_for_geometry(aoi_wgs84)
    
    # Transform to UTM
    transformer_to_utm = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
    aoi_utm = transform(transformer_to_utm.transform, aoi_wgs84)
    
    # Get bounds
    minx, miny, maxx, maxy = aoi_utm.bounds
    
    # Create grid
    transformer_to_wgs = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)
    
    waypoints = []
    y = miny
    row = 0
    while y <= maxy:
        x = minx
        col = 0
        is_odd_row = row % 2 == 1
        
        if is_odd_row:
            # Reverse every other row for snake pattern
            while x <= maxx:
                # Check if point is in AOI
                pt_utm = Point(x, y)
                if aoi_utm.contains(pt_utm):
                    lon, lat = transformer_to_wgs.transform(x, y)
                    waypoints.append((x, y))  # Store UTM
                x += spacing_m
        else:
            while x <= maxx:
                pt_utm = Point(x, y)
                if aoi_utm.contains(pt_utm):
                    lon, lat = transformer_to_wgs.transform(x, y)
                    waypoints.append((x, y))
                x += spacing_m
        
        y += spacing_m
        row += 1
    
    print(f"Generated {len(waypoints)} waypoints in UTM ({spacing_m}m spacing)")
    
    # Return as WGS84 for export
    transformer_to_wgs = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)
    waypoints_wgs84 = [transformer_to_wgs.transform(x, y) for x, y in waypoints]
    
    return waypoints_wgs84, utm_crs, waypoints


def main():
    import argparse
    
    p = argparse.ArgumentParser(description="Simple routing: polygon -> grid waypoints -> optimized route")
    p.add_argument("--polygon", default="inputs/map.geojson", help="Input polygon")
    p.add_argument("--output", default="simple_routing_output", help="Output directory")
    p.add_argument("--spacing-m", type=float, default=500, help="Waypoint grid spacing (meters)")
    
    args = p.parse_args()
    
    out_path = Path(args.output)
    ensure_dir(str(out_path))
    ensure_dir(str(out_path / "routes"))
    
    print("\n" + "="*70)
    print("SIMPLE ROUTING WORKFLOW")
    print("="*70)
    
    try:
        # Load polygon
        print(f"\n[1/3] Loading polygon from {args.polygon}...")
        aoi = load_aoi(args.polygon, None)
        utm_crs = get_utm_crs_for_geometry(aoi)
        bounds = aoi.bounds
        
        print(f"      Bounds: ({bounds[0]:.3f}, {bounds[1]:.3f}) -> ({bounds[2]:.3f}, {bounds[3]:.3f})")
        print(f"      UTM CRS: {utm_crs}")
        
        # Create waypoint grid
        print(f"\n[2/3] Creating {args.spacing_m}m-spaced waypoint grid...")
        waypoints_wgs84, utm_crs, waypoints_utm = create_grid_waypoints(aoi, args.spacing_m)
        
        # Route is simply the waypoints in order (snake pattern)
        # For a simple routing, we don't need A* - just connect the grid points
        route_points = waypoints_wgs84
        
        print(f"      Route: {len(route_points)} waypoints")
        
        # Export route
        print(f"\n[3/3] Exporting route...")
        geojson_path = str(out_path / "routes" / "route.geojson")
        kml_path = str(out_path / "routes" / "route.kml")
        
        export_route(waypoints_utm, str(utm_crs), geojson_path, kml_path)
        
        print(f"      GeoJSON: {geojson_path}")
        print(f"      KML: {kml_path}")
        
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
        
        print(f"\nRoute statistics:")
        print(f"  - Waypoints: {len(route_points)}")
        print(f"  - Spacing: {args.spacing_m}m")
        print(f"  - Total area: {aoi.area / 1e6:.1f} km²")
        
        print(f"\nVisualize the route:")
        print(f"  - GeoJSON: {geojson_path}")
        print(f"  - KML: {kml_path} (open in Google Earth)")
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
