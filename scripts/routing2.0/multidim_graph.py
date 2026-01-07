"""
Multi-dimensional Graph Builder

Creates NetworkX graphs where nodes and edges include attributes for all terrain factors:
- Cost (combined terrain difficulty)
- Slope (terrain steepness)
- NDVI (vegetation index)
- Distance (spatial distance between nodes)
- Priority (computed from cost - lower is higher priority)
"""

import logging
import math
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List

import numpy as np
import networkx as nx
import rasterio
from rasterio.transform import rowcol, xy
from shapely.geometry import Point, Polygon
from pyproj import Transformer
from shapely.ops import transform as shape_transform

logger = logging.getLogger("routing2.0.multidim_graph")


def load_raster(path: str) -> Tuple[np.ndarray, dict]:
    """Load a raster file and return (data, metadata)."""
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        meta = src.meta.copy()
        meta["transform"] = src.transform
        meta["crs"] = src.crs
        meta["bounds"] = src.bounds
    return data, meta


def sample_raster_at_point(data: np.ndarray, row: int, col: int) -> float:
    """Safely sample raster value at a grid point."""
    if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
        val = data[row, col]
        return float(val) if not np.isnan(val) else 0.0
    return 0.0


def compute_priority(cost_value: float, cost_min: float, cost_max: float) -> float:
    """Compute priority score (0-1, higher = more priority).
    
    Priority is inverse of cost - lower cost means higher priority.
    """
    if cost_max == cost_min:
        return 0.5
    # Normalize and invert
    return 1.0 - (cost_value - cost_min) / (cost_max - cost_min)


def build_multidim_graph(
    cost_path: str,
    slope_path: Optional[str] = None,
    ndvi_path: Optional[str] = None,
    elevation_path: Optional[str] = None,
    node_spacing: int = 10,
    connectivity: int = 8,
    polygon_coords: Optional[List[Tuple[float, float]]] = None
) -> Tuple[nx.Graph, Dict[str, Any]]:
    """Build a multi-dimensional graph from terrain rasters.
    
    Args:
        cost_path: Path to cost.tif
        slope_path: Optional path to slope.tif
        ndvi_path: Optional path to ndvi.tif
        elevation_path: Optional path to elevation.tif (for altitude)
        node_spacing: Grid spacing for nodes (in pixels)
        connectivity: 4 or 8 (4-way or 8-way connectivity)
        polygon_coords: Optional list of (lon, lat) tuples defining the AOI polygon
        
    Returns:
        (NetworkX Graph, metadata dict)
    """
    logger.info(f"Loading cost raster: {cost_path}")
    cost, meta = load_raster(cost_path)
    transform = meta["transform"]
    rows, cols = cost.shape
    
    # Create polygon object if coords provided
    aoi_polygon = None
    if polygon_coords:
        if len(polygon_coords) > 2:
            aoi_polygon = Polygon(polygon_coords)
            
            # Reproject polygon if raster is not Lat/Lon
            # Assuming GeoJSON is always WGS84 (EPSG:4326)
            raster_crs = meta.get("crs")
            if raster_crs and raster_crs.to_string() != "EPSG:4326":
                logger.info(f"Reprojecting Polygon from EPSG:4326 to {raster_crs}")
                try:
                    project = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True).transform
                    aoi_polygon = shape_transform(project, aoi_polygon)
                except Exception as e:
                    logger.error(f"Failed to reproject polygon: {e}")
            
            # Check for overlap with raster bounds
            r_bounds = meta["bounds"]
            # bounds: left, bottom, right, top
            # Create raster box
            from shapely.geometry import box
            raster_box = box(r_bounds.left, r_bounds.bottom, r_bounds.right, r_bounds.top)
            
            if not raster_box.intersects(aoi_polygon):
                logger.warning("AOI Polygon does not intersect Raster bounds! Ignoring Polygon mask.")
                logger.warning(f"Raster: {raster_box.bounds}")
                logger.warning(f"Polygon: {aoi_polygon.bounds}")
                # Fallback: Ignore polygon
                aoi_polygon = None
            else:
                logger.info("Using AOI polygon for graph masking")
        else:
            logger.warning("Invalid polygon coordinates provided")
    
    # Load optional rasters
    slope = None
    ndvi = None
    elevation = None
    
    if slope_path and Path(slope_path).exists():
        slope, _ = load_raster(slope_path)
        logger.info(f"Loaded slope raster: {slope_path}")
    if ndvi_path and Path(ndvi_path).exists():
        ndvi, _ = load_raster(ndvi_path)
        logger.info(f"Loaded NDVI raster: {ndvi_path}")
    if elevation_path and Path(elevation_path).exists():
        elevation, _ = load_raster(elevation_path)
        logger.info(f"Loaded Elevation raster: {elevation_path}")
    
    # Compute cost statistics
    valid_cost = cost[~np.isnan(cost) & (cost > 0)]
    if valid_cost.size == 0:
        cost_min, cost_max, cost_mean = 0.0, 1.0, 0.5
    else:
        cost_min = float(np.min(valid_cost))
        cost_max = float(np.max(valid_cost))
        cost_mean = float(np.mean(valid_cost))
    
    logger.info(f"Cost stats: min={cost_min:.4f}, max={cost_max:.4f}, mean={cost_mean:.4f}")
    
    # Create grid of nodes
    G = nx.Graph()
    node_map = {}  # (grid_row, grid_col) -> node_id
    
    grid_rows = list(range(0, rows, node_spacing))
    grid_cols = list(range(0, cols, node_spacing))
    
    node_id = 0
    for gr_idx, r in enumerate(grid_rows):
        for gc_idx, c in enumerate(grid_cols):
            # Get raster values
            cost_val = sample_raster_at_point(cost, r, c)
            slope_val = sample_raster_at_point(slope, r, c) if slope is not None else 0.0
            ndvi_val = sample_raster_at_point(ndvi, r, c) if ndvi is not None else 0.0
            elev_val = sample_raster_at_point(elevation, r, c) if elevation is not None else 0.0
            
            # Skip nodes with invalid cost
            if cost_val <= 0 or np.isnan(cost_val):
                continue
            
            # Compute priority (inverse of cost)
            priority = compute_priority(cost_val, cost_min, cost_max)
            
            # Get geographic coordinates
            x, y = xy(transform, r, c)
            
            # Check polygon inclusion
            if aoi_polygon:
                point = Point(x, y)
                if not aoi_polygon.contains(point):
                    continue

            # Add node with all attributes
            G.add_node(
                node_id,
                # Grid coordinates
                grid_row=int(r),
                grid_col=int(c),
                grid_idx_row=gr_idx,
                grid_idx_col=gc_idx,
                # Geographic coordinates
                x=float(x),
                y=float(y),
                # Terrain factors
                cost=float(cost_val),
                slope=float(slope_val),
                ndvi=float(ndvi_val),
                elevation=float(elev_val),
                altitude=float(elev_val),  # Alias for visualization compatibility
                # Computed priority (0-1, higher = better)
                priority=float(priority)
            )
            
            node_map[(gr_idx, gc_idx)] = node_id
            node_id += 1
    
    logger.info(f"Created {node_id} nodes")
    
    # Define neighbor offsets based on connectivity
    if connectivity == 8:
        neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    else:
        neighbors = [(-1, 0), (0, -1), (0, 1), (1, 0)]
    
    # Create edges
    edge_count = 0
    for (gr_idx, gc_idx), nid in node_map.items():
        node_data = G.nodes[nid]
        
        for dr, dc in neighbors:
            nbr_key = (gr_idx + dr, gc_idx + dc)
            if nbr_key not in node_map:
                continue
            
            nbr_id = node_map[nbr_key]
            if G.has_edge(nid, nbr_id):
                continue
            
            nbr_data = G.nodes[nbr_id]
            
            # Compute edge distance (in coordinate units)
            dx = nbr_data["x"] - node_data["x"]
            dy = nbr_data["y"] - node_data["y"]
            distance = math.hypot(dx, dy)
            
            # Edge cost factors (average of endpoints)
            edge_cost = (node_data["cost"] + nbr_data["cost"]) / 2.0
            edge_slope = (node_data["slope"] + nbr_data["slope"]) / 2.0
            edge_ndvi = (node_data["ndvi"] + nbr_data["ndvi"]) / 2.0
            edge_priority = (node_data["priority"] + nbr_data["priority"]) / 2.0
            
            # Combined weight (cost * distance, with diagonal penalty)
            is_diagonal = (dr != 0 and dc != 0)
            diag_factor = 1.4142 if is_diagonal else 1.0
            combined_weight = edge_cost * distance * diag_factor
            
            # Add edge with all attributes
            G.add_edge(
                nid, nbr_id,
                distance=float(distance),
                cost=float(edge_cost),
                slope=float(edge_slope),
                ndvi=float(edge_ndvi),
                priority=float(edge_priority),
                weight=float(combined_weight),
                is_diagonal=is_diagonal
            )
            edge_count += 1
    
    logger.info(f"Created {edge_count} edges")
    
    # Build metadata
    graph_meta = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "node_spacing": node_spacing,
        "connectivity": connectivity,
        "cost_stats": {
            "min": cost_min,
            "max": cost_max,
            "mean": cost_mean
        },
        "crs": str(meta.get("crs", "unknown")),
        "raster_shape": (rows, cols),
        "has_slope": slope is not None,
        "has_ndvi": ndvi is not None
    }
    
    return G, graph_meta


def save_graph(G: nx.Graph, output_path: str, format: str = "graphml") -> str:
    """Save graph to file.
    
    Args:
        G: NetworkX graph
        output_path: Output file path
        format: 'graphml', 'gexf', or 'json'
        
    Returns:
        Path to saved file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "graphml":
        nx.write_graphml(G, str(output_path))
    elif format == "gexf":
        nx.write_gexf(G, str(output_path))
    elif format == "json":
        import json
        from networkx.readwrite import json_graph
        data = json_graph.node_link_data(G)
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        raise ValueError(f"Unknown format: {format}")
    
    logger.info(f"Saved graph to: {output_path}")
    return str(output_path)


def load_graph(path: str) -> nx.Graph:
    """Load graph from file."""
    path = Path(path)
    if path.suffix == ".graphml":
        return nx.read_graphml(path)
    elif path.suffix == ".gexf":
        return nx.read_gexf(path)
    elif path.suffix == ".json":
        import json
        from networkx.readwrite import json_graph
        with open(path) as f:
            data = json.load(f)
        return json_graph.node_link_graph(data)
    else:
        raise ValueError(f"Unknown file format: {path.suffix}")


def find_priority_nodes(G: nx.Graph, top_n: int = 10) -> List[Tuple[int, Dict]]:
    """Find the top N highest priority nodes.
    
    Args:
        G: NetworkX graph with priority attribute on nodes
        top_n: Number of top nodes to return
        
    Returns:
        List of (node_id, node_attributes) sorted by priority descending
    """
    nodes_with_priority = [
        (n, data) for n, data in G.nodes(data=True)
        if "priority" in data
    ]
    nodes_sorted = sorted(nodes_with_priority, key=lambda x: x[1]["priority"], reverse=True)
    return nodes_sorted[:top_n]


def find_min_cost_node(G: nx.Graph) -> Tuple[int, Dict]:
    """Find the node with minimum cost (priority anchor)."""
    min_node = None
    min_cost = float('inf')
    for n, data in G.nodes(data=True):
        if "cost" in data and data["cost"] < min_cost:
            min_cost = data["cost"]
            min_node = (n, data)
    return min_node


def get_graph_statistics(G: nx.Graph) -> Dict[str, Any]:
    """Compute comprehensive statistics about the graph."""
    stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": nx.density(G),
        "is_connected": nx.is_connected(G) if G.number_of_nodes() > 0 else False
    }
    
    # Node attribute statistics
    if G.number_of_nodes() > 0:
        for attr in ["cost", "slope", "ndvi", "priority"]:
            values = [data.get(attr, 0) for _, data in G.nodes(data=True)]
            if values:
                stats[f"node_{attr}_min"] = float(min(values))
                stats[f"node_{attr}_max"] = float(max(values))
                stats[f"node_{attr}_mean"] = float(sum(values) / len(values))
    
    # Edge attribute statistics
    if G.number_of_edges() > 0:
        for attr in ["weight", "distance", "cost"]:
            values = [data.get(attr, 0) for _, _, data in G.edges(data=True)]
            if values:
                stats[f"edge_{attr}_min"] = float(min(values))
                stats[f"edge_{attr}_max"] = float(max(values))
                stats[f"edge_{attr}_mean"] = float(sum(values) / len(values))
    
    return stats


if __name__ == "__main__":
    import sys
    import json
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Default test paths
    cost_path = "out_demo_plan/rasters/cost.tif"
    slope_path = "out_demo_plan/rasters/slope.tif"
    ndvi_path = "out_demo_plan/rasters/ndvi.tif"
    output_dir = "scripts/routing2.0/output/graph"
    
    if len(sys.argv) > 1:
        cost_path = sys.argv[1]
    
    # Build graph
    G, meta = build_multidim_graph(
        cost_path=cost_path,
        slope_path=slope_path,
        ndvi_path=ndvi_path,
        node_spacing=10,
        connectivity=8
    )
    
    # Save graph
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    save_graph(G, f"{output_dir}/multidim_graph.graphml", format="graphml")
    save_graph(G, f"{output_dir}/multidim_graph.json", format="json")
    
    # Get statistics
    stats = get_graph_statistics(G)
    
    # Find priority anchor
    min_node = find_min_cost_node(G)
    top_priority = find_priority_nodes(G, top_n=5)
    
    print("\n=== Multi-dimensional Graph Results ===")
    print(f"Graph: {meta['nodes']} nodes, {meta['edges']} edges")
    print(f"Statistics: {json.dumps(stats, indent=2)}")
    
    if min_node:
        print(f"\nPriority Anchor (min cost): Node {min_node[0]}")
        print(f"  Cost: {min_node[1]['cost']:.6f}")
        print(f"  Position: ({min_node[1]['x']:.2f}, {min_node[1]['y']:.2f})")
    
    print(f"\nTop 5 Priority Nodes:")
    for nid, data in top_priority:
        print(f"  Node {nid}: priority={data['priority']:.4f}, cost={data['cost']:.6f}")
