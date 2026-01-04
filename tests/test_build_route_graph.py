from pathlib import Path

from frp.utils import make_demo_data
from frp.aoi import load_aoi
from frp.cli import run_pipeline
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point


def _find_route_file(out_dir: Path):
    # common location
    p = out_dir / "routes" / "route.geojson"
    if p.exists():
        return p
    # fallback: search
    for f in out_dir.rglob("route.geojson"):
        return f
    return None


def test_build_route_graph_from_demo(tmp_path):
    out_demo = tmp_path / "demo"
    out_demo_str = str(out_demo)

    # create demo inputs
    demo_paths = make_demo_data(out_demo_str)
    aoi = load_aoi(demo_paths["aoi"], None)

    # run pipeline (demo behavior: run_astar=False)
    weights = {"slope": 0.5, "ndvi": 0.5}
    run_pipeline(
        aoi,
        demo_paths["nir"],
        demo_paths["red"],
        None,
        10.0,
        512,
        weights,
        out_demo_str,
        run_astar=False,
        mode="demo",
        node_area_ha=2.0,
        time_limit_s=1.0,
        sweep_spacing_m=None,
        waypoint_spacing_m=10.0,
        simplify_m=0.0,
        geojson_geometry="linestring",
        max_waypoints=2000,
    )

    route_file = _find_route_file(out_demo)
    assert route_file is not None and route_file.exists(), "route.geojson not found"

    gdf = gpd.read_file(route_file)
    coords = []
    if not gdf.empty:
        first = gdf.geometry.iloc[0]
        if isinstance(first, LineString):
            coords = list(first.coords)
        else:
            for geom in gdf.geometry:
                if isinstance(geom, Point):
                    coords.append((geom.x, geom.y))

    assert len(coords) >= 2, "Route must contain at least 2 points"

    # build graph
    G = nx.Graph()
    for i, (x, y) in enumerate(coords):
        G.add_node(i, x=float(x), y=float(y))
        if i > 0:
            px, py = coords[i - 1]
            G.add_edge(i - 1, i, weight=float(((x - px) ** 2 + (y - py) ** 2) ** 0.5))

    graphs_dir = out_demo / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    graphml_path = graphs_dir / "route_graph.graphml"
    nx.write_graphml(G, str(graphml_path))

    assert G.number_of_nodes() >= 2
    assert G.number_of_edges() >= 1
    assert graphml_path.exists() and graphml_path.stat().st_size > 0
