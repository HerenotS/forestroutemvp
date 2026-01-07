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

# Add project root to path
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

from frp.graph import build_multidim_graph_from_rasters
from frp.routing import find_path_astar_multidim
from frp.viz import visualize_route_2d, visualize_terrain_3d
from frp.utils import make_demo_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    output_dir = Path("out_pipeline_v2")
    output_dir.mkdir(exist_ok=True)
    
    logger.info("Starting Routing Pipeline V2...")
    
    # 1. Data Preparation
    # If inputs exist, use them. Else generate demo data.
    # We are looking for cost, slope, ndvi rasters.
    
    # As a fallback/simulation, we generate synthetic data
    logger.info("Generating/Loading data...")
    # This creates 'red.tif', 'nir.tif' and 'aoi.geojson' in output_dir
    paths = make_demo_data(str(output_dir / "inputs")) 
    
    # Deriving synthetic cost/slope/ndvi from the demo data
    # In a real scenario, these would be computed from DEM/Spectral bands
    # Here we simulate them for the requested "3D terrain-aware" simulation
    
    import rasterio
    
    # Simulate a DEM (Altitude)
    # Just making a hill shape
    with rasterio.open(paths['red']) as src:
        meta = src.meta.copy()
        meta['bounds'] = src.bounds
        shape = src.shape
        transform = src.transform
        
    rows, cols = shape
    x, y = np.meshgrid(np.linspace(-1, 1, cols), np.linspace(-1, 1, rows))
    elevation = 100 * (1 - (x**2 + y**2)) # A hill in the middle
    elevation = np.maximum(elevation, 0)
    
    dem_path = output_dir / "inputs" / "elevation.tif"
    with rasterio.open(dem_path, 'w', **meta) as dst:
        dst.write(elevation.astype(rasterio.float32), 1)
        
    # Simulate Slope (gradient of DEM)
    gy, gx = np.gradient(elevation)
    slope = np.sqrt(gx**2 + gy**2)
    slope_path = output_dir / "inputs" / "slope.tif"
    with rasterio.open(slope_path, 'w', **meta) as dst:
        dst.write(slope.astype(rasterio.float32), 1)
        
    # Simulate NDVI (vegetation) - just noise + patches
    ndvi = np.random.rand(rows, cols) * 0.8 + 0.2
    ndvi_path = output_dir / "inputs" / "ndvi.tif"
    with rasterio.open(ndvi_path, 'w', **meta) as dst:
        dst.write(ndvi.astype(rasterio.float32), 1)

    # Cost - simpler combo
    cost = (slope / slope.max()) * 0.5 + (1 - ndvi) * 0.5
    cost_path = output_dir / "inputs" / "cost.tif"
    with rasterio.open(cost_path, 'w', **meta) as dst:
        dst.write(cost.astype(rasterio.float32), 1)

    logger.info(f"Data prepared in {output_dir}/inputs")

    # 2. Build 3D/Multi-dim Graph
    logger.info("Building Multi-dimensional Graph...")
    G, graph_meta = build_multidim_graph_from_rasters(
        cost_path=str(cost_path),
        slope_path=str(slope_path),
        ndvi_path=str(ndvi_path),
        node_spacing=5, # finer grid
        connectivity=8
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
        background_raster=cost,
        meta=meta
    )
    
    # 3D Terrain Plot
    visualize_terrain_3d(
        elevation,
        output_path=str(output_dir / "terrain_3d.png"),
        meta=meta
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
