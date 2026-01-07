"""
Complete Full Routing Pipeline
Integrates map.geojson (AOI) with synthetic 3D terrain generation and multi-factor routing.
References: routing2.0 modules and frp modules.
"""

import sys
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import geopandas as gpd
import networkx as nx
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize
from shapely.geometry import box, shape

# Setup paths
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(project_root))

# Import local modules (migrated from frp)
from frp_graph import build_multidim_graph_from_rasters
from frp_routing import find_path_astar_multidim
from frp_viz import visualize_route_2d, visualize_terrain_3d

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(script_dir / "pipeline.log", mode='w')
    ]
)
logger = logging.getLogger("pipeline_full")

def generate_synthetic_terrain(
    bounds: Tuple[float, float, float, float], 
    output_dir: Path, 
    resolution_deg: float = 0.0001
) -> Dict[str, Any]:
    """
    Generates synthetic Altitude, Slope, and NDVI rasters based on bounds.
    Mimics 'real' terrain by creating a coherent mountain/valley structure.
    
    Args:
        bounds: (minx, miny, maxx, maxy)
        output_dir: Directory to save TIFFs
        resolution_deg: Pixel size in degrees (approx 10m at equator is ~0.0001)
        
    Returns:
        Dictionary with paths to generated rasters and metadata.
    """
    minx, miny, maxx, maxy = bounds
    width = int((maxx - minx) / resolution_deg)
    height = int((maxy - miny) / resolution_deg)
    
    if width <= 0 or height <= 0:
        raise ValueError("Invalid bounds or resolution resulted in empty grid.")
        
    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    
    meta = {
        'driver': 'GTiff',
        'height': height,
        'width': width,
        'count': 1,
        'dtype': 'float32',
        'crs': 'EPSG:4326',
        'transform': transform
    }
    
    # 1. Generate Altitude (DEM)
    # Create valid coordinate grids
    x_lin = np.linspace(minx, maxx, width)
    y_lin = np.linspace(maxy, miny, height) # MaxY at top (row 0)
    X, Y = np.meshgrid(x_lin, y_lin)
    
    # Mathematical Terrain: 
    # Center peak + Perlin-like noise (sine waves)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    
    # Distance from center normalized
    dx = (X - cx) / (maxx - minx)
    dy = (Y - cy) / (maxy - miny)
    dist_sq = dx*dx + dy*dy
    
    # Base mountain shape (Gaussian) * Scale (e.g. 2000m high) + Base (2200m)
    # Mexico City is high altitude (~2250m)
    base_elevation = 2250.0
    peak_height = 500.0             
    elevation = base_elevation + peak_height * np.exp(-10 * dist_sq)
    
    # Add roughness
    elevation += 50 * np.sin(X * 1000) * np.cos(Y * 1000)
    
    elev_path = output_dir / "elevation.tif"
    with rasterio.open(elev_path, 'w', **meta) as dst:
        dst.write(elevation.astype(np.float32), 1)
        
    # 2. Generate Slope
    # Gradient in X and Y
    # Note: This is "pixels per pixel" gradient. For degrees, need conversion, 
    # but for relative cost, this is sufficient.
    gy, gx = np.gradient(elevation)
    slope = np.sqrt(gx**2 + gy**2)
    # Normalize slope roughly to 0-45 degrees for simulation (arbitrary scaling)
    slope = np.clip(slope * 50, 0, 90)
    
    slope_path = output_dir / "slope.tif"
    with rasterio.open(slope_path, 'w', **meta) as dst:
        dst.write(slope.astype(np.float32), 1)
        
    # 3. Generate NDVI (Vegetation)
    # Higher altitude = fewer trees (maybe), Valleys = green.
    # Simple logic: Inverse of slope? Coherent noise.
    ndvi = (np.sin(X * 500) + np.cos(Y * 500) + 2) / 4.0 
    # Add dependency on elevation (tree line)
    ndvi = np.where(elevation > base_elevation + 300, ndvi * 0.5, ndvi)
    
    ndvi_path = output_dir / "ndvi.tif"
    with rasterio.open(ndvi_path, 'w', **meta) as dst:
        dst.write(ndvi.astype(np.float32), 1)
        
    # 4. Generate Cost Map
    # Combined factor
    # Cost = w1*Slope + w2*(1-NDVI)
    # Normalized Slope (0-1)
    slope_norm = slope / 90.0
    cost = slope_norm * 0.6 + (1 - ndvi) * 0.4
    
    cost_path = output_dir / "cost.tif"
    with rasterio.open(cost_path, 'w', **meta) as dst:
        dst.write(cost.astype(np.float32), 1)
        
    return {
        'elevation': elev_path,
        'slope': slope_path,
        'ndvi': ndvi_path,
        'cost': cost_path,
        'meta': meta,
        'data': {
            'elevation': elevation,
            'slope': slope,
            'ndvi': ndvi,
            'cost': cost
        }
    }

def main():
    output_dir = script_dir / "output"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    
    input_dir = output_dir / "inputs"
    input_dir.mkdir()
    
    logger.info("=== Starting Full Routing Pipeline ===")
    
    # 1. Load Map Data (AOI)
    map_geojson_path = project_root / "inputs" / "map.geojson"
    try:
        aoi_gdf = gpd.read_file(map_geojson_path)
        logger.info(f"Loaded AOI from {map_geojson_path}")
    except Exception as e:
        logger.error(f"Failed to load map.geojson: {e}")
        return

    # Use the first polygon as AOI
    aoi_poly = aoi_gdf.geometry.iloc[0]
    bounds = aoi_poly.bounds  # minx, miny, maxx, maxy
    
    # 2. Generate/Simulate 3D Terrain Data
    logger.info("Generating 3D terrain models based on AOI coordinates...")
    terrain_data = generate_synthetic_terrain(bounds, input_dir)
    logger.info(f"Terrain data generated in {input_dir}")
    
    # 3. Build Multi-Dimensional Graph
    logger.info("Building Multi-Dimensional Graph...")
    from rasterio.coords import BoundingBox
    # Add bounds object for viz
    terrain_data['meta']['bounds'] = BoundingBox(*bounds)
    
    # Using the frp_graph module to build graph from simulated rasters
    G, graph_meta = build_multidim_graph_from_rasters(
        cost_path=str(terrain_data['cost']),
        slope_path=str(terrain_data['slope']),
        ndvi_path=str(terrain_data['ndvi']),
        node_spacing=3,  # High resolution
        connectivity=8,
        aoi_polygon=aoi_poly
    )
    
    if G.number_of_nodes() == 0:
        logger.error("Graph construction failed (0 nodes). Check AOI vs Rasters.")
        return
        
    # 4. Route Optimization
    # Define start/end points based on terrain features
    # Start: Lowest Elevation (Valley)
    # End: Highest Elevation (Peak)
    logger.info("identifying optimal start/end points...")
    nodes_data = list(G.nodes(data=True))
    
    # Sort by altitude derived from generated DEM
    # We need to sample elevation for each node or use cost as proxy
    # Since we have grid nodes, we can map back to raster
    elevation_raster = terrain_data['data']['elevation']
    rows, cols = elevation_raster.shape
    
    valid_nodes = []
    for n, data in nodes_data:
        r, c = data['grid_row'], data['grid_col']
        if 0 <= r < rows and 0 <= c < cols:
            z = elevation_raster[r, c]
            valid_nodes.append((n, z))
            
    if not valid_nodes:
        logger.error("No valid nodes mapped to elevation.")
        return
        
    valid_nodes.sort(key=lambda x: x[1])
    start_node = valid_nodes[0][0]  # Lowest
    end_node = valid_nodes[-1][0]   # Highest
    
    logger.info(f"Routing from {start_node} (Elev: {valid_nodes[0][1]:.1f}m) to {end_node} (Elev: {valid_nodes[-1][1]:.1f}m)")
    
    # Weights Configuration
    weights = {
        "cost": 0.3,      # Terrain difficulty
        "slope": 0.5,     # Avoid steep slopes
        "ndvi": 0.1,      # Vegetation preference
        "distance": 0.1   # Efficiency
    }
    
    logger.info(f"Running A* with weights: {weights}")
    path_nodes = find_path_astar_multidim(G, start_node, end_node, weights)
    
    if not path_nodes:
        logger.error("No path found.")
        return
        
    logger.info(f"Path found: {len(path_nodes)} nodes")
    
    # 5. Export and Visualize
    logger.info("Generating outputs...")
    
    # Save Route GeoJSON
    route_coords = [(G.nodes[n]['x'], G.nodes[n]['y']) for n in path_nodes]
    from shapely.geometry import LineString
    route_geom = LineString(route_coords)
    route_gdf = gpd.GeoDataFrame([{'geometry': route_geom, 'id': 1}], crs=aoi_gdf.crs)
    route_path = output_dir / "route.geojson"
    route_gdf.to_file(route_path, driver='GeoJSON')
    
    # Save Graph (GraphML)
    nx.write_graphml(G, output_dir / "graph.graphml")
    
    # Visualizations
    visualize_route_2d(
        G, path_nodes, 
        output_path=str(output_dir / "visualization_2d.png"), 
        background_raster=terrain_data['data']['cost'],
        meta=terrain_data['meta']
    )
    
    visualize_terrain_3d(
        terrain_data['data']['elevation'],
        output_path=str(output_dir / "visualization_3d.png"),
        meta=terrain_data['meta']
    )
    
    # Report
    report = {
        "start_point": {"node": str(start_node), "elevation": float(valid_nodes[0][1])},
        "end_point": {"node": str(end_node), "elevation": float(valid_nodes[-1][1])},
        "path_length_nodes": len(path_nodes),
        "total_distance_m": float(route_geom.length * 111000), # Approx deg->meters
        "weights_used": weights,
        "files": {
            "route_geojson": str(route_path),
            "inputs": [str(p) for p in input_dir.glob("*.tif")]
        }
    }
    
    with open(output_dir / "report.json", 'w') as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Pipeline complete. Outputs in {output_dir}")

if __name__ == "__main__":
    main()
