#!/usr/bin/env python3
"""
Complete routing workflow: polygon -> waypoints -> route -> visualization

This script creates a complete routing solution:
1. Loads polygon from map.geojson
2. Generates sweep-line waypoints across the polygon
3. Plans an optimized route using A*
4. Exports route as GeoJSON/KML
5. Creates a visualization with the graph

Usage:
  python scripts/complete_routing.py [--polygon POLYGON] [--output OUTPUT_DIR]
"""
import argparse
import sys
import json
from pathlib import Path
import logging

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import Affine

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.aoi import load_aoi, get_utm_crs_for_geometry
from frp.coverage import plan_coverage
from frp.waypoints import lines_to_waypoints
from frp.graph import build_aoi_graph, visualize_graph_with_route
from frp.costmap import build_cost_map
from frp.derived import compute_ndvi
from frp.astar import optimize_route_segments
from frp.export import export_route
from frp.utils import ensure_dir, write_raster

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("complete_routing")


def create_synthetic_rasters(aoi_geom, utm_crs, output_dir, resolution=10):
    """Create synthetic NDVI and DEM rasters for the AOI."""
    import rasterio
    from rasterio.transform import from_bounds
    
    # Get bounds
    minx, miny, maxx, maxy = aoi_geom.bounds
    
    # Create synthetic arrays
    cols = int((maxx - minx) / resolution) + 1
    rows = int((maxy - miny) / resolution) + 1
    
    # NDVI: random values between 0.2 and 0.8 (vegetation)
    ndvi_data = np.random.uniform(0.2, 0.8, (rows, cols)).astype(np.float32)
    
    # DEM: gentle slope from min to max elevation
    dem_data = np.tile(
        np.linspace(100, 200, cols),
        (rows, 1)
    ).astype(np.float32)
    
    # Create raster metadata
    transform = Affine.translation(minx, maxy) * Affine.scale(resolution, -resolution)
    
    ensure_dir(str(Path(output_dir) / "rasters"))
    
    # Save NDVI
    ndvi_path = Path(output_dir) / "rasters" / "ndvi_synthetic.tif"
    meta = {
        'driver': 'GTiff',
        'dtype': rasterio.float32,
        'nodata': None,
        'width': cols,
        'height': rows,
        'count': 1,
        'crs': str(utm_crs),
        'transform': transform,
    }
    with rasterio.open(str(ndvi_path), 'w', **meta) as dst:
        dst.write(ndvi_data, 1)
    logger.info(f"Created synthetic NDVI: {ndvi_path}")
    
    # Save DEM
    dem_path = Path(output_dir) / "rasters" / "dem_synthetic.tif"
    with rasterio.open(str(dem_path), 'w', **meta) as dst:
        dst.write(dem_data, 1)
    logger.info(f"Created synthetic DEM: {dem_path}")
    
    return ndvi_path, dem_path


def main():
    p = argparse.ArgumentParser(
        description="Complete routing workflow: polygon -> waypoints -> route"
    )
    p.add_argument(
        "--polygon",
        default="inputs/map.geojson",
        help="Input polygon GeoJSON (default: inputs/map.geojson)"
    )
    p.add_argument(
        "--output",
        default="routing_output",
        help="Output directory (default: routing_output)"
    )
    p.add_argument(
        "--node-area-ha",
        type=float,
        default=2.0,
        help="Node area for A* optimization (default: 2.0 hectares = 141m spacing)"
    )
    p.add_argument(
        "--sweep-spacing-m",
        type=float,
        default=50.0,
        help="Sweep line spacing in meters (default: 50m)"
    )
    p.add_argument(
        "--waypoint-spacing-m",
        type=float,
        default=20.0,
        help="Waypoint spacing in meters (default: 20m)"
    )
    p.add_argument(
        "--resolution",
        type=float,
        default=10.0,
        help="Raster resolution in meters (default: 10m)"
    )
    
    args = p.parse_args()
    
    out_path = Path(args.output)
    ensure_dir(str(out_path))
    
    print("\n" + "="*70)
    print("COMPLETE ROUTING WORKFLOW")
    print("="*70)
    
    try:
        # Step 1: Load AOI
        print("\n[1/7] Loading polygon from map.geojson...")
        aoi = load_aoi(args.polygon, None)
        utm_crs = get_utm_crs_for_geometry(aoi)
        bounds = aoi.bounds
        print(f"    Bounds: {bounds}")
        print(f"    UTM CRS: {utm_crs}")
        
        # Step 2: Create synthetic rasters
        print("\n[2/7] Creating synthetic rasters (NDVI, DEM)...")
        ndvi_path, dem_path = create_synthetic_rasters(
            aoi, utm_crs, args.output, args.resolution
        )
        
        # Step 3: Load rasters and compute cost map
        print("\n[3/7] Computing cost map from rasters...")
        from frp.preprocess import reproject_and_clip
        
        ndvi_arr, ndvi_meta, _ = reproject_and_clip(str(ndvi_path), aoi, args.resolution)
        dem_arr, dem_meta, _ = reproject_and_clip(str(dem_path), aoi, args.resolution)
        
        # Compute slope from DEM using numpy gradients
        dy = np.gradient(dem_arr, axis=0)
        dx = np.gradient(dem_arr, axis=1)
        slope_mag = np.sqrt(dy**2 + dx**2)
        
        # Normalize and combine into cost map
        ndvi_norm = (ndvi_arr - ndvi_arr.min()) / (ndvi_arr.max() - ndvi_arr.min() + 1e-6)
        slope_norm = (slope_mag - slope_mag.min()) / (slope_mag.max() - slope_mag.min() + 1e-6)
        
        cost = 0.3 * slope_norm + 0.7 * ndvi_norm  # Prefer low slope, high vegetation
        cost = np.nan_to_num(cost, nan=1e6)
        
        print(f"    Cost map shape: {cost.shape}")
        print(f"    Cost range: [{cost.min():.3f}, {cost.max():.3f}]")
        
        # Step 4: Plan coverage (sweep lines)
        print("\n[4/7] Generating sweep lines across the polygon...")
        sweep_lines = plan_coverage(
            aoi, utm_crs, args.resolution, 
            tile_size=512, sweep_spacing_m=args.sweep_spacing_m
        )
        print(f"    Generated {len(sweep_lines)} sweep lines")
        
        # Step 5: Convert to waypoints
        print("\n[5/7] Converting sweep lines to waypoints...")
        waypoints_utm = lines_to_waypoints(
            sweep_lines, args.waypoint_spacing_m, max_waypoints=2000
        )
        print(f"    Generated {len(waypoints_utm)} waypoints")
        
        # Step 6: Optimize route with A*
        print("\n[6/7] Optimizing route with A* pathfinding...")
        meta = ndvi_meta.copy()
        meta["node_area_ha"] = args.node_area_ha
        
        optimized_points = optimize_route_segments(waypoints_utm, cost, meta)
        print(f"    Optimized route has {len(optimized_points)} points")
        
        # Step 7: Export results
        print("\n[7/7] Exporting route and creating visualizations...")
        
        # Export route
        ensure_dir(str(out_path / "routes"))
        geojson_path = str(out_path / "routes" / "route.geojson")
        kml_path = str(out_path / "routes" / "route.kml")
        export_route(optimized_points, str(utm_crs), geojson_path, kml_path)
        print(f"    Route exported to: {geojson_path}")
        print(f"                      {kml_path}")
        
        # Build and visualize graph
        print("\n    Building reference graph (200m spacing)...")
        graph_out = str(out_path / "graph")
        G, graphml_path = build_aoi_graph(
            aoi_wgs84=aoi,
            node_area_ha=4.0,  # 200m spacing
            out_dir=graph_out,
            show=False
        )
        print(f"    Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        
        # Try to create visualization
        try:
            print("\n    Creating route visualization...")
            viz_path = str(out_path / "route_visualization.png")
            nodes_path = Path(graph_out) / "nodes.geojson"
            edges_path = Path(graph_out) / "edges.geojson"
            
            if nodes_path.exists() and edges_path.exists():
                visualize_graph_with_route(
                    str(nodes_path),
                    str(edges_path),
                    geojson_path,
                    output_path=viz_path,
                    route_color="red",
                    node_color="lightblue",
                    edge_color="lightgray"
                )
                print(f"    Visualization saved to: {viz_path}")
        except Exception as e:
            logger.warning(f"Could not create visualization: {e}")
        
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
        
        print("\nNext steps:")
        print(f"  1. View route in GIS: {geojson_path}")
        print(f"  2. View in Google Earth: {kml_path}")
        if (out_path / "route_visualization.png").exists():
            print(f"  3. View visualization: {out_path / 'route_visualization.png'}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
