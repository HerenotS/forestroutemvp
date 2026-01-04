import math
import logging
from pathlib import Path
from typing import Dict, Tuple

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, LineString
from shapely.ops import transform
from pyproj import Transformer

from frp.aoi import get_utm_crs_for_geometry

logger = logging.getLogger("frp.graph")


def _grid_points_in_aoi(aoi_utm, spacing_m: float) -> Dict[Tuple[int, int], Tuple[float, float]]:
    minx, miny, maxx, maxy = aoi_utm.bounds
    if maxx <= minx or maxy <= miny:
        return {}
    nx_pts = int(math.ceil((maxx - minx) / spacing_m)) + 1
    ny_pts = int(math.ceil((maxy - miny) / spacing_m)) + 1
    pts = {}
    for iy in range(ny_pts):
        y = miny + iy * spacing_m
        for ix in range(nx_pts):
            x = minx + ix * spacing_m
            p = Point(x, y)
            if aoi_utm.covers(p):
                pts[(ix, iy)] = (x, y)
    return pts


def build_aoi_graph(aoi_wgs84, node_area_ha: float = 2.0, out_dir: str = "out_graph", show: bool = False):
    """
    Build grid graph over AOI and save GraphML + nodes/edges geojson.

    Returns: tuple(graph, graphml_path)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # compute spacing (meters)
    spacing_m = math.sqrt(float(node_area_ha) * 10000.0)

    # UTM transform
    utm_crs = get_utm_crs_for_geometry(aoi_wgs84)
    to_utm = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True).transform
    to_wgs = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True).transform
    aoi_utm = transform(to_utm, aoi_wgs84)

    logger.info("AOI (UTM) bounds: %s", aoi_utm.bounds)
    logger.info("Node spacing (m): %.3f", spacing_m)

    pts = _grid_points_in_aoi(aoi_utm, spacing_m)
    if not pts:
        raise RuntimeError("No grid points generated inside AOI. Try a smaller node_area_ha or check AOI size.")

    # Build graph
    G = nx.Graph()
    index_map = {}
    for idx, ((ix, iy), (x, y)) in enumerate(sorted(pts.items())):
        lon, lat = to_wgs(x, y)
        G.add_node(idx, utm_x=float(x), utm_y=float(y), lon=float(lon), lat=float(lat))
        index_map[(ix, iy)] = idx

    # 4-neighborhood edges (right, up)
    for (ix, iy), nid in index_map.items():
        for nbr in ((ix + 1, iy), (ix, iy + 1)):
            if nbr in index_map:
                nid2 = index_map[nbr]
                x1, y1 = pts[(ix, iy)]
                x2, y2 = pts[nbr]
                dist = math.hypot(x2 - x1, y2 - y1)
                G.add_edge(nid, nid2, weight=float(dist))

    # Save GraphML
    graphml_path = out_dir / "aoi_graph.graphml"
    nx.write_graphml(G, str(graphml_path))

    # Save nodes.geojson and edges.geojson (WGS84)
    node_rows = []
    for n, attr in G.nodes(data=True):
        pt = Point(attr["lon"], attr["lat"])
        props = {"id": int(n), "utm_x": float(attr["utm_x"]), "utm_y": float(attr["utm_y"]), "lon": float(attr["lon"]), "lat": float(attr["lat"])}
        node_rows.append({**props, "geometry": pt})
    nodes_gdf = gpd.GeoDataFrame(node_rows, geometry=[r["geometry"] for r in node_rows], crs="EPSG:4326")
    nodes_path = out_dir / "nodes.geojson"
    nodes_gdf.to_file(nodes_path, driver="GeoJSON")

    edge_rows = []
    for u, v, attr in G.edges(data=True):
        x1, y1 = G.nodes[u]["lon"], G.nodes[u]["lat"]
        x2, y2 = G.nodes[v]["lon"], G.nodes[v]["lat"]
        ls = LineString([(x1, y1), (x2, y2)])
        props = {"u": int(u), "v": int(v), "weight": float(attr.get("weight", spacing_m))}
        edge_rows.append({**props, "geometry": ls})
    edges_gdf = gpd.GeoDataFrame(edge_rows, geometry=[r["geometry"] for r in edge_rows], crs="EPSG:4326")
    edges_path = out_dir / "edges.geojson"
    edges_gdf.to_file(edges_path, driver="GeoJSON")

    logger.info("Saved: %s (nodes=%d edges=%d) CRS=%s", graphml_path, G.number_of_nodes(), G.number_of_edges(), utm_crs.to_string())
    logger.info("Nodes geojson: %s, Edges geojson: %s", nodes_path, edges_path)

    # optional show
    if show:
        try:
            import matplotlib.pyplot as plt
        except Exception as e:
            logger.error("matplotlib required for --show: %s", e)
            raise
        fig, ax = plt.subplots()
        # AOI boundary in WGS84
        try:
            # aoi_wgs84 may be shapely geometry; use GeoSeries to plot
            gpd.GeoSeries([aoi_wgs84]).boundary.plot(ax=ax, edgecolor="black")
        except Exception:
            pass
        xs = [data["lon"] for _, data in G.nodes(data=True)]
        ys = [data["lat"] for _, data in G.nodes(data=True)]
        ax.scatter(xs, ys, s=6, color="red")
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_title(f"AOI graph nodes (spacing ~{spacing_m:.1f} m)")
        plt.show()

    return G, str(graphml_path)


def visualize_graph_with_route(graph_gdf_nodes: str, graph_gdf_edges: str, route_geojson: str, output_path: str = "graph_with_route.png", route_color: str = "red", node_color: str = "blue", edge_color: str = "gray"):
    """Visualize graph nodes/edges with route highlighted in a specific color.
    
    Args:
        graph_gdf_nodes: Path to nodes.geojson from graph
        graph_gdf_edges: Path to edges.geojson from graph
        route_geojson: Path to route.geojson
        output_path: Where to save the visualization PNG
        route_color: Color for route line (default: red)
        node_color: Color for graph nodes (default: blue)
        edge_color: Color for graph edges (default: gray)
    """
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        logger = logging.getLogger("frp.graph")
        logger.error("matplotlib required for visualization: %s", e)
        raise
    
    # Load graph components
    nodes_gdf = gpd.read_file(graph_gdf_nodes)
    edges_gdf = gpd.read_file(graph_gdf_edges)
    route_gdf = gpd.read_file(route_geojson)
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot graph edges in light gray
    edges_gdf.plot(ax=ax, color=edge_color, linewidth=0.5, alpha=0.5)
    
    # Plot graph nodes
    nodes_gdf.plot(ax=ax, color=node_color, markersize=2, alpha=0.6)
    
    # Highlight route in specified color (thicker)
    route_gdf.plot(ax=ax, color=route_color, linewidth=2.5, alpha=0.9)
    
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(f"Graph with Route (in {route_color})")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    
    logger = logging.getLogger("frp.graph")
    logger.info("Saved graph visualization: %s", output_path)
    
    return output_path