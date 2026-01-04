#!/usr/bin/env python3
"""
Complete routing: polygon -> grid waypoints -> A* optimization -> route export

Creates waypoints in a regular grid pattern across the polygon,
then optimizes the path using A* on a graph.

Usage:
  python scripts/routing_with_astar.py [--polygon POLYGON] [--output OUTPUT] [--spacing-m SPACING]
"""
import sys
from pathlib import Path
import math

sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.aoi import load_aoi, get_utm_crs_for_geometry
from frp.export import export_route
from frp.utils import ensure_dir
from frp.graph import build_aoi_graph
from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Transformer
import geopandas as gpd
import networkx as nx


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
                pt_utm = Point(x, y)
                if aoi_utm.contains(pt_utm):
                    lon, lat = transformer_to_wgs.transform(x, y)
                    waypoints.append((lon, lat, x, y))  # Store both WGS84 and UTM
                x += spacing_m
        else:
            while x <= maxx:
                pt_utm = Point(x, y)
                if aoi_utm.contains(pt_utm):
                    lon, lat = transformer_to_wgs.transform(x, y)
                    waypoints.append((lon, lat, x, y))
                x += spacing_m
        
        y += spacing_m
        row += 1
    
    print(f"Generated {len(waypoints)} waypoints in UTM ({spacing_m}m spacing)")
    
    return waypoints, utm_crs


def snap_waypoints_to_graph(waypoints, graph):
    """Snap waypoints to nearest nodes in graph."""
    snapped = []
    for lon, lat, x, y in waypoints:
        # Find nearest node
        nearest_node = None
        min_dist = float('inf')
        
        for node, data in graph.nodes(data=True):
            nx_val, ny_val = data['geometry'].x, data['geometry'].y
            dist = math.sqrt((nx_val - x)**2 + (ny_val - y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
        
        if nearest_node:
            snapped.append(nearest_node)
    
    return snapped


def main():
    import argparse
    
    p = argparse.ArgumentParser(description="Routing with A*: polygon -> grid waypoints -> graph -> A* -> route")
    p.add_argument("--polygon", default="inputs/map.geojson", help="Input polygon")
    p.add_argument("--output", default="routing_astar_output", help="Output directory")
    p.add_argument("--spacing-m", type=float, default=500, help="Waypoint grid spacing (meters)")
    p.add_argument("--node-area-ha", type=float, default=3.2, help="Node area for graph (hectares)")
    
    args = p.parse_args()
    
    out_path = Path(args.output)
    ensure_dir(str(out_path))
    ensure_dir(str(out_path / "routes"))
    ensure_dir(str(out_path / "inputs"))
    
    print("\n" + "="*70)
    print("ROUTING WITH A* OPTIMIZATION")
    print("="*70)
    
    try:
        # Load polygon
        print(f"\n[1/5] Loading polygon from {args.polygon}...")
        aoi = load_aoi(args.polygon, None)
        utm_crs = get_utm_crs_for_geometry(aoi)
        bounds = aoi.bounds
        
        print(f"      Bounds: ({bounds[0]:.3f}, {bounds[1]:.3f}) -> ({bounds[2]:.3f}, {bounds[3]:.3f})")
        print(f"      UTM CRS: {utm_crs}")
        
        # Create waypoint grid
        print(f"\n[2/5] Creating {args.spacing_m}m-spaced waypoint grid...")
        waypoints, utm_crs = create_grid_waypoints(aoi, args.spacing_m)
        
        # Build graph from polygon
        print(f"\n[3/5] Building graph from polygon (node area: {args.node_area_ha} ha)...")
        graph, nodes_gdf, edges_gdf = build_aoi_graph(
            aoi, 
            node_area_ha=args.node_area_ha,
            out_dir=str(out_path / "graph"),
            show=False
        )
        print(f"      Graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")
        
        # Snap waypoints to graph
        print(f"\n[4/5] Snapping waypoints to graph...")
        snapped_waypoints = snap_waypoints_to_graph(waypoints, graph)
        print(f"      Snapped to {len(snapped_waypoints)} graph nodes")
        
        if len(snapped_waypoints) < 2:
            print("      Warning: Not enough snapped waypoints for A*, using original waypoints")
            route_points = [(lon, lat) for lon, lat, x, y in waypoints]
        else:
            # A* optimization between first and last waypoint
            print(f"      Running A* from waypoint 0 to waypoint {len(snapped_waypoints)-1}...")
            
            start_node = snapped_waypoints[0]
            end_node = snapped_waypoints[-1]
            
            try:
                path_nodes = nx.astar_path(
                    graph, 
                    start_node, 
                    end_node,
                    heuristic=lambda n1, n2: 0  # Simple cost heuristic
                )
                
                # Convert path to coordinates
                route_points = []
                for node_id in path_nodes:
                    node_data = graph.nodes[node_id]
                    geom = node_data['geometry']
                    route_points.append((geom.x, geom.y))
                
                print(f"      A* found path with {len(path_nodes)} nodes")
            except nx.NetworkXNoPath:
                print("      Warning: No path found, using waypoint sequence")
                route_points = [(graph.nodes[n]['geometry'].x, graph.nodes[n]['geometry'].y) 
                              for n in snapped_waypoints]
        
        # Export route
        print(f"\n[5/5] Exporting route...")
        geojson_path = str(out_path / "routes" / "route.geojson")
        kml_path = str(out_path / "routes" / "route.kml")
        
        # Convert UTM coords to WGS84 for export
        transformer = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)
        route_wgs84 = [transformer.transform(x, y) for x, y in route_points]
        
        # Export in UTM (astar returns UTM coords, need to export properly)
        export_route(route_points, str(utm_crs), geojson_path, kml_path)
        
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
        print(f"  - Original waypoints: {len(waypoints)}")
        print(f"  - Optimized route nodes: {len(route_points)}")
        print(f"  - Graph nodes: {len(graph.nodes())}")
        print(f"  - Graph edges: {len(graph.edges())}")
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
