#!/usr/bin/env python3
"""Visualize a graph with route highlighted in a specific color.

Usage:
  python scripts/visualize_graph_with_route.py --nodes NODES_GEOJSON --edges EDGES_GEOJSON --route ROUTE_GEOJSON [--out OUTPUT_PNG] [--route-color COLOR] [--node-color COLOR] [--edge-color COLOR]
"""
import argparse
import sys
from pathlib import Path

# Add parent dir to path for frp imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.graph import visualize_graph_with_route


def main():
    p = argparse.ArgumentParser(description="Visualize graph with route highlighted")
    p.add_argument("--nodes", required=True, help="Path to nodes.geojson from graph")
    p.add_argument("--edges", required=True, help="Path to edges.geojson from graph")
    p.add_argument("--route", required=True, help="Path to route.geojson")
    p.add_argument("--out", default="graph_with_route.png", help="Output PNG file (default: graph_with_route.png)")
    p.add_argument("--route-color", default="red", help="Route line color (default: red)")
    p.add_argument("--node-color", default="blue", help="Graph nodes color (default: blue)")
    p.add_argument("--edge-color", default="gray", help="Graph edges color (default: gray)")
    
    args = p.parse_args()
    
    try:
        output = visualize_graph_with_route(
            graph_gdf_nodes=args.nodes,
            graph_gdf_edges=args.edges,
            route_geojson=args.route,
            output_path=args.out,
            route_color=args.route_color,
            node_color=args.node_color,
            edge_color=args.edge_color
        )
        print(f"Graph visualization saved: {output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
