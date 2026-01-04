import os
from pathlib import Path

from frp.utils import make_demo_data
from frp.aoi import load_aoi
from frp.graph import build_aoi_graph
import networkx as nx


def test_build_graph_from_demo(tmp_path):
    out_demo = tmp_path / "demo"
    demo = make_demo_data(str(out_demo))
    aoi = load_aoi(demo["aoi"], None)

    out_graph = tmp_path / "out_graph"
    out_graph.mkdir(parents=True, exist_ok=True)

    G, graphml = build_aoi_graph(aoi_wgs84=aoi, node_area_ha=2.0, out_dir=str(out_graph), show=False)

    assert os.path.exists(graphml)
    assert os.path.getsize(graphml) > 0
    assert G.number_of_nodes() >= 2
    assert G.number_of_edges() >= 1

    # Read back GraphML to confirm format
    G2 = nx.read_graphml(graphml)
    assert len(G2) >= 2