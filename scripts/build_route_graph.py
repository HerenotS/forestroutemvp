#!/usr/bin/env python3
"""Build a NetworkX graph from a route GeoJSON.

Usage:
  python scripts/build_route_graph.py --route out_real/routes/route.geojson --out out_real
"""
import argparse
import os
from pathlib import Path
import math

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point


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
    p = argparse.ArgumentParser(description="Build NetworkX graph from route GeoJSON")
    p.add_argument("--route", required=True, help="Path to route.geojson")
    p.add_argument("--out", required=True, help="Output directory for graph files")
    args = p.parse_args()

    route_path = Path(args.route)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not route_path.exists():
        raise SystemExit(f"Route file not found: {route_path}")

    gdf = gpd.read_file(route_path)
    coords = coords_from_route(gdf)

    if not coords:
        raise SystemExit("No coordinates found in route file")

    G = build_graph(coords)

    graphml_path = out_dir / "route_graph.graphml"
    nx.write_graphml(G, graphml_path)

    print(f"Built graph with nodes={G.number_of_nodes()} edges={G.number_of_edges()}")


if __name__ == "__main__":
    main()
