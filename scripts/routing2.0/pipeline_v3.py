#!/usr/bin/env python
"""
Complete Routing Pipeline V2
Enhances existing routing with 3D terrain-aware capabilities and multi-factor optimization.
"""
import logging
import sys
from pathlib import Path
import json

import numpy as np
import networkx as nx
import geopandas as gpd # Added import

# Add project root to path
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir.parent.parent)) # Add root for frp package if needed

# Import from local copied modules
from frp_graph import build_multidim_graph_from_rasters
from frp_routing import find_path_astar_multidim
from frp_viz import visualize_route_2d, visualize_terrain_3d
# from frp.utils import make_demo_data # We will implement custom data loading from map.geojson

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def make_data_from_geojson(geojson_path: str, output_dir: Path):
    """Generate synthetic terrain data based on GeoJSON bounds."""
    import rasterio
    from rasterio.transform import from_bounds
    
    gdf = gpd.read_file(geojson_path)
    bounds = gdf.total_bounds # minx, miny, maxx, maxy
    
    # Define resolution
    pixel_size = 0.0001 # approx 10m
    width = int((bounds[2] - bounds[0]) / pixel_size)
    height = int((bounds[3] - bounds[1]) / pixel_size)
    
    transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
    
    meta = {
        'driver': 'GTiff',
        'height': height,
        'width': width,
        'count': 1,
        'dtype': 'float32',
        'crs': gdf.crs,
        'transform': transform
    }
    
    # Store bounds in meta for visualization
    from rasterio.coords import BoundingBox
    meta['bounds'] = BoundingBox(bounds[0], bounds[1], bounds[2], bounds[3])
    
    # Generate Synthetic Terrain
    x = np.linspace(0, 4*np.pi, width)
    y = np.linspace(0, 4*np.pi, height)
    X, Y = np.meshgrid(x, y)
    
    # Elevation: Hills and valleys
    elevation = 2200 + 100 * np.sin(X) * np.cos(Y) + 50 * np.sin(X/2)
    
    # Write Elevation
    elev_path = output_dir / "elevation.tif"
    with rasterio.open(elev_path, 'w', **meta) as dst:
        dst.write(elevation.astype(np.float32), 1)
        
    # Slope
    gy, gx = np.gradient(elevation)
    slope = np.sqrt(gx**2 + gy**2)
    slope_path = output_dir / "slope.tif"
    with rasterio.open(slope_path, 'w', **meta) as dst:
        dst.write(slope.astype(np.float32), 1)
        
    # NDVI (Random + Elevation bias)
    ndvi = (np.sin(X/3) + np.cos(Y/3) + 2) / 4.0
    ndvi_path = output_dir / "ndvi.tif"
    with rasterio.open(ndvi_path, 'w', **meta) as dst:
        dst.write(ndvi.astype(np.float32), 1)
        
    # Cost
    cost = (slope / slope.max()) * 0.4 + (1 - ndvi) * 0.6
    cost_path = output_dir / "cost.tif"
    with rasterio.open(cost_path, 'w', **meta) as dst:
        dst.write(cost.astype(np.float32), 1)
        
    return {
        'cost': cost_path,
        'slope': slope_path,
        'ndvi': ndvi_path,
        'elevation': elev_path,
        'meta': meta,
        'elevation_data': elevation,
        'cost_data': cost,
        'polygon': gdf.geometry[0]
    }

def main():
    output_dir = Path("output_v3")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "inputs").mkdir(exist_ok=True)
    
    logger.info("Starting Routing Pipeline V3 (GeoJSON based)...")
    
    # 1. Data Preparation
    map_geojson_path = Path("../../inputs/map.geojson")
    if not map_geojson_path.exists():
        logger.error(f"Map GeoJSON not found at {map_geojson_path}")
        return

    logger.info(f"Loading map from {map_geojson_path}")
    data_pack = make_data_from_geojson(str(map_geojson_path), output_dir / "inputs")
    
    # 2. Build Graph
    logger.info("Building Multi-dimensional Graph...")
    G, graph_meta = build_multidim_graph_from_rasters(
        cost_path=str(data_pack['cost']),
        slope_path=str(data_pack['slope']),
        ndvi_path=str(data_pack['ndvi']),
        node_spacing=5,
        connectivity=8,
        aoi_polygon= data_pack['polygon']
    )
    
    # 3. Define Route Objectives
    # Find start (low cost) and end (high cost/peak) or just corners
    nodes = list(G.nodes(data=True))
    if not nodes:
        logger.error("Graph empty!")
        return

    # Sort by 'priority' or 'altitude'
    # Let's go from bottom to top
    sorted_by_alt = sorted(nodes, key=lambda n: n[1].get('altitude', 0))
    start_node = sorted_by_alt[0][0] # Lowest point
    end_node = sorted_by_alt[-1][0] # Highest point
    
    logger.info(f"Routing from {start_node} to {end_node}")
    
    # 4. Run Multi-Factor Optimization
    logger.info("Running A* Optimization (Weighted)...")
    weights = {
        "cost": 0.3,
        "slope": 0.4, # Avoid steep
        "ndvi": 0.1,
        "distance": 0.2
    }
    
    path = find_path_astar_multidim(G, start_node, end_node, weights=weights)
    
    if not path:
        logger.error("No path found!")
        return
        
    logger.info(f"Path found with {len(path)} steps.")
    
    # 5. Visualization and Reporting
    logger.info("Generating Visualizations...")
    
    # 2D Route Plot
    visualize_route_2d(
        G, path, 
        output_path=str(output_dir / "route_2d.png"),
        background_raster=data_pack['cost_data'],
        meta=data_pack['meta']
    )
    
    # 3D Terrain Plot
    visualize_terrain_3d(
        data_pack['elevation_data'],
        output_path=str(output_dir / "terrain_3d.png"),
        meta=data_pack['meta']
    )
    
    # Export Path
    path_coords = [(G.nodes[n]['x'], G.nodes[n]['y']) for n in path]
    import pandas as pd
    df = pd.DataFrame(path_coords, columns=['x', 'y'])
    df.to_csv(output_dir / "route_path.csv", index=False)
    
    summary = {
        "steps": len(path),
        "start": start_node,
        "end": end_node,
        "weights": weights
    }
    with open(output_dir / "report.json", 'w') as f:
        json.dump(summary, f, indent=2)
        
    logger.info("Pipeline completed successfully. Check 'out_pipeline_v2/'")

if __name__ == "__main__":
    main()
