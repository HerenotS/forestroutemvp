#!/usr/bin/env python3
"""
Complete routing example with visualization and analysis.

This script demonstrates the full routing workflow:
1. Load polygon from GeoJSON
2. Create regular waypoint grid
3. Export route in multiple formats
4. Analyze and visualize results
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.aoi import load_aoi, get_utm_crs_for_geometry
from frp.export import export_route
from frp.utils import ensure_dir
from shapely.geometry import Point, LineString
from shapely.ops import transform
from pyproj import Transformer
import geopandas as gpd


def main():
    print("\n" + "="*70)
    print("FOREST ROUTE MVP - COMPLETE ROUTING EXAMPLE")
    print("="*70)
    
    # Configuration
    polygon_file = "inputs/map.geojson"
    output_dir = "example_route_output"
    spacing_m = 300  # meters between waypoints
    
    ensure_dir(output_dir)
    ensure_dir(f"{output_dir}/routes")
    
    # Step 1: Load and validate polygon
    print(f"\n[Step 1] Loading polygon from {polygon_file}")
    try:
        aoi = load_aoi(polygon_file, None)
        print(f"✓ Polygon loaded successfully")
        print(f"  - Type: {aoi.geom_type}")
        print(f"  - Is valid: {aoi.is_valid}")
        print(f"  - Bounds: {aoi.bounds}")
    except Exception as e:
        print(f"✗ Error loading polygon: {e}")
        return 1
    
    # Step 2: Get UTM CRS
    print(f"\n[Step 2] Determining coordinate system")
    try:
        utm_crs = get_utm_crs_for_geometry(aoi)
        print(f"✓ UTM CRS determined: {utm_crs}")
        
        # Transform to UTM for processing
        transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
        aoi_utm = transform(transformer.transform, aoi)
        bounds_utm = aoi_utm.bounds
        print(f"  - UTM Bounds: {bounds_utm}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1
    
    # Step 3: Create waypoint grid
    print(f"\n[Step 3] Creating {spacing_m}m-spaced waypoint grid")
    try:
        minx, miny, maxx, maxy = bounds_utm
        waypoints_utm = []
        
        y = miny
        row = 0
        while y <= maxy:
            x_coords = []
            x = minx
            
            while x <= maxx:
                pt = Point(x, y)
                if aoi_utm.contains(pt):
                    x_coords.append(x)
                x += spacing_m
            
            # Alternate direction for efficient sweeping
            if row % 2 == 1:
                x_coords.reverse()
            
            waypoints_utm.extend([(x, y) for x in x_coords])
            
            y += spacing_m
            row += 1
        
        print(f"✓ Generated {len(waypoints_utm)} waypoints")
        
        # Calculate route statistics
        total_distance = 0
        for i in range(len(waypoints_utm) - 1):
            x1, y1 = waypoints_utm[i]
            x2, y2 = waypoints_utm[i + 1]
            dist = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
            total_distance += dist
        
        print(f"  - Total route distance: {total_distance / 1000:.2f} km")
        print(f"  - Avg distance per waypoint: {(total_distance / len(waypoints_utm)):.1f} m")
        
    except Exception as e:
        print(f"✗ Error creating waypoints: {e}")
        return 1
    
    # Step 4: Export routes
    print(f"\n[Step 4] Exporting routes in multiple formats")
    try:
        geojson_path = f"{output_dir}/routes/route.geojson"
        kml_path = f"{output_dir}/routes/route.kml"
        
        export_route(waypoints_utm, str(utm_crs), geojson_path, kml_path)
        
        print(f"✓ Routes exported:")
        print(f"  - GeoJSON: {geojson_path}")
        print(f"  - KML: {kml_path}")
        
    except Exception as e:
        print(f"✗ Error exporting: {e}")
        return 1
    
    # Step 5: Create detailed analysis
    print(f"\n[Step 5] Creating detailed route analysis")
    try:
        # Load exported route
        route_gdf = gpd.read_file(geojson_path)
        route_line = route_gdf.geometry[0]
        
        # Calculate statistics
        analysis = {
            "metadata": {
                "title": "Route Analysis Report",
                "polygon_source": polygon_file,
                "output_directory": output_dir,
                "spacing_m": spacing_m,
                "utm_crs": str(utm_crs)
            },
            "polygon_info": {
                "type": aoi.geom_type,
                "area_km2": aoi.area / 1e6,
                "bounds_wgs84": list(aoi.bounds),
                "is_valid": aoi.is_valid
            },
            "route_info": {
                "total_waypoints": len(waypoints_utm),
                "total_distance_km": total_distance / 1000,
                "avg_segment_length_m": total_distance / (len(waypoints_utm) - 1) if len(waypoints_utm) > 1 else 0,
                "coordinate_system": str(utm_crs)
            },
            "coverage_analysis": {
                "grid_spacing_m": spacing_m,
                "estimated_coverage_lines": row,
                "points_per_line": len(waypoints_utm) // max(row, 1)
            }
        }
        
        # Save analysis
        analysis_path = f"{output_dir}/route_analysis.json"
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2)
        
        print(f"✓ Analysis saved: {analysis_path}")
        
    except Exception as e:
        print(f"✗ Error in analysis: {e}")
        return 1
    
    # Step 6: Summary
    print(f"\n" + "="*70)
    print("ROUTING COMPLETE - SUMMARY")
    print("="*70)
    
    print(f"\n📊 Route Statistics:")
    print(f"   • Waypoints: {len(waypoints_utm):,}")
    print(f"   • Total distance: {total_distance / 1000:.2f} km")
    print(f"   • Grid spacing: {spacing_m}m")
    print(f"   • Coordinate system: {utm_crs}")
    
    print(f"\n📁 Output Files:")
    for file_path in sorted(Path(output_dir).rglob("*")):
        if file_path.is_file():
            size_kb = file_path.stat().st_size / 1024
            print(f"   • {file_path.relative_to(output_dir)} ({size_kb:.1f} KB)")
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. View route in Google Earth:")
    print(f"      • Download Google Earth Pro")
    print(f"      • Open: {kml_path}")
    print(f"")
    print(f"   2. View in QGIS:")
    print(f"      • Open QGIS")
    print(f"      • Layer > Add Layer > Add Vector Layer")
    print(f"      • Select: {geojson_path}")
    print(f"")
    print(f"   3. Programmatic analysis (Python):")
    print(f"      • import geopandas as gpd")
    print(f"      • route = gpd.read_file('{geojson_path}')")
    print(f"      • print(route.length[0] / 1000, 'km')")
    
    print(f"\n" + "="*70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
