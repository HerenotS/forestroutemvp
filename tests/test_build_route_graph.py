"""Tests for build_route_graph module."""
import sys
from pathlib import Path
import tempfile
import json

import pytest
import networkx as nx
from shapely.geometry import LineString, Point

# Add scripts dir to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_route_graph import coords_from_route, build_graph


def test_coords_from_linestring():
    """Test extracting coords from a GeoJSON LineString."""
    import geopandas as gpd
    
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[0, 0], [1, 1], [2, 2]]
            }
        }]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
        json.dump(geojson, f)
        f.flush()
        gdf = gpd.read_file(f.name)
        coords = coords_from_route(gdf)
        assert coords == [(0, 0), (1, 1), (2, 2)]


def test_coords_from_points():
    """Test extracting coords from a GeoJSON Point collection."""
    import geopandas as gpd
    
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 1]}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [2, 2]}},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
        json.dump(geojson, f)
        f.flush()
        gdf = gpd.read_file(f.name)
        coords = coords_from_route(gdf)
        assert coords == [(0, 0), (1, 1), (2, 2)]


def test_build_graph():
    """Test building a NetworkX graph from coordinates."""
    coords = [(0, 0), (1, 1), (2, 2)]
    G = build_graph(coords)
    
    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 2
    assert all('x' in G.nodes[n] and 'y' in G.nodes[n] for n in G.nodes())
    assert all('weight' in G[u][v] for u, v in G.edges())


def test_build_graph_single_point():
    """Test building a graph from a single coordinate."""
    coords = [(0, 0)]
    G = build_graph(coords)
    
    assert G.number_of_nodes() == 1
    assert G.number_of_edges() == 0

