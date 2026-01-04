#!/usr/bin/env python3
"""Build a NetworkX graph from a route GeoJSON.

Reads config from config.json before processing.

Usage:
  python scripts/build_route_graph.py [--route PATH] [--out PATH] [--show]
"""
import argparse
import os
import sys
from pathlib import Path
import math
import json

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {config_path}: {e}", file=sys.stderr)
    return {}


def coords_from_route(gdf):
    """Yield (x,y) coords in route order from GeoDataFrame.

    Supports a single LineString or a FeatureCollection of Points.
    """
    if gdf.empty:
        return []
    # If first geometry is a LineString, extract its coordinates
    first_geom = gdf.geometry.iloc[0]
    if isinstance(first_geom, LineString):
        return list(first_geom.coords)
    # Otherwise assume a collection of Point features in order
    pts = []
    for geom in gdf.geometry:
        if geom is None:
            continue
        if isinstance(geom, Point):
            pts.append((geom.x, geom.y))
        else:
            # if it's a LineString on a later row, include its coords sequentially
            try:
                coords = list(geom.coords)
                pts.extend(coords)
            except Exception:
                continue
    return pts


def build_graph(coords):
    G = nx.Graph()
    for i, (x, y) in enumerate(coords):
        G.add_node(i, x=float(x), y=float(y))
        if i > 0:
            px, py = coords[i - 1]
            dist = math.hypot(float(x) - float(px), float(y) - float(py))
            G.add_edge(i - 1, i, weight=float(dist))
    return G


def main():
    config = load_config("config.json")
    
    p = argparse.ArgumentParser(description="Build NetworkX graph from route GeoJSON")
    p.add_argument("--route", default=config.get("route_geojson"), help="Path to route.geojson")
    p.add_argument("--out", default=config.get("out_dir", "out_graph"), help="Output directory for graph files")
    p.add_argument("--show", action="store_true", default=config.get("show_plots", False), help="Show graph plot (matplotlib required)")
    args = p.parse_args()

    if not args.route:
        print("Error: --route must be provided or set in config.json", file=sys.stderr)
        sys.exit(1)

    route_path = Path(args.route)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not route_path.exists():
        print(f"Error: Route file not found: {route_path}", file=sys.stderr)
        sys.exit(1)

    try:
        gdf = gpd.read_file(route_path)
    except Exception as e:
        print(f"Error reading route file: {e}", file=sys.stderr)
        sys.exit(1)

    coords = coords_from_route(gdf)

    if not coords:
        print("Error: No coordinates found in route file", file=sys.stderr)
        sys.exit(1)

    G = build_graph(coords)

    graphml_path = out_dir / "route_graph.graphml"
    nx.write_graphml(G, str(graphml_path))
    print(f"Wrote graph to {graphml_path}")

    # Optionally visualize
    if args.show:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Error: matplotlib is required to show the graph. Install with: pip install matplotlib", file=sys.stderr)
            sys.exit(1)

        pos = {n: (data.get("x", 0.0), data.get("y", 0.0)) for n, data in G.nodes(data=True)}
        fig, ax = plt.subplots()
        nx.draw_networkx_edges(G, pos=pos, ax=ax, edge_color="gray", width=0.7)
        nx.draw_networkx_nodes(G, pos=pos, ax=ax, node_size=10, node_color="black")
        ax.set_aspect("equal")
        plt.axis("off")
        plt.show()

    print(f"Built graph with nodes={G.number_of_nodes()} edges={G.number_of_edges()}")


if __name__ == "__main__":
    main()
