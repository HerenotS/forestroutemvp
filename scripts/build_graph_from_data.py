#!/usr/bin/env python3
"""Build a NetworkX graph from raster/AOI data.

Reads config from config.json before processing.

Usage:
  python scripts/build_graph_from_data.py [--aoi PATH] [--bbox STR] [--node-area-ha NUM] [--out PATH] [--show]
"""
import argparse
import sys
from pathlib import Path
import math
import json
import os

import networkx as nx

# Add parent dir to path for frp imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.aoi import load_aoi
from frp.graph import build_aoi_graph


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {config_path}: {e}", file=sys.stderr)
    return {}


def get_latest_file(folder: str, extension: str = ".geojson"):
    """Find the most recently modified file with given extension in folder."""
    folder_path = Path(folder)
    if not folder_path.exists():
        return None
    
    files = list(folder_path.glob(f"*{extension}"))
    if not files:
        return None
    
    # Sort by modification time, return most recent
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return str(latest)


def load_polygon_from_json(polygon_file: str):
    """Load a polygon from a GeoJSON file."""
    from shapely.geometry import shape
    import geopandas as gpd
    
    try:
        gdf = gpd.read_file(polygon_file)
        if gdf.empty:
            # Try to fix the file: load raw JSON and validate
            with open(polygon_file, 'r') as f:
                data = json.load(f)
            
            # Close polygon rings if needed
            if data.get('features'):
                for feat in data['features']:
                    if feat.get('geometry', {}).get('type') == 'Polygon':
                        rings = feat['geometry'].get('coordinates', [])
                        for ring in rings:
                            if ring and ring[0] != ring[-1]:
                                ring.append(ring[0])
                
                # Write back fixed GeoJSON
                with open(polygon_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Re-read with geopandas
                gdf = gpd.read_file(polygon_file)
        
        if gdf.empty:
            raise ValueError(f"No geometries found in {polygon_file}")
        
        # Use union_all when available (newer geopandas) to avoid deprecation
        geom = None
        if hasattr(gdf.geometry, "union_all"):
            try:
                geom = gdf.geometry.union_all()
            except Exception:
                geom = gdf.unary_union
        else:
            geom = gdf.unary_union
        return geom
    except Exception as e:
        raise ValueError(f"Error loading polygon from {polygon_file}: {e}")


def main():
    config = load_config("config.json")
    
    p = argparse.ArgumentParser(description="Build NetworkX graph from AOI/bbox/polygon data")
    group = p.add_mutually_exclusive_group(required=False)
    group.add_argument("--aoi", help="Path to AOI GeoJSON file")
    group.add_argument("--bbox", help='bbox string "minLon,minLat,maxLon,maxLat"')
    group.add_argument("--polygon", help="Path to polygon JSON/GeoJSON file (auto-detects latest in ./inputs/)")
    p.add_argument("--node-area-ha", type=float, default=config.get("node_area_ha", 3.2), help="Target node area in hectares for 200m spacing (default 3.2 hectares = ~200m)")
    p.add_argument("--out", default=config.get("out_dir", "out_graph"), help="Output directory for graph files")
    p.add_argument("--show", action="store_true", default=config.get("show_plots", False), help="Show graph plot (matplotlib required)")
    args = p.parse_args()

    # If no args provided, use config or auto-detect
    aoi_source = args.aoi or args.bbox or args.polygon
    if not aoi_source:
        # Try config first
        if config.get("polygon_file"):
            aoi_source = config.get("polygon_file")
        elif config.get("aoi_geojson"):
            aoi_source = config.get("aoi_geojson")
        elif config.get("bbox"):
            aoi_source = config.get("bbox")
        else:
            # Auto-detect latest from inputs folder
            latest_file = get_latest_file("inputs")
            if latest_file:
                aoi_source = latest_file
                print(f"Auto-detected latest polygon: {latest_file}")
    
    if not aoi_source:
        print("Error: --aoi, --bbox, or --polygon must be provided or set in config.json, or place a .geojson file in ./inputs/", file=sys.stderr)
        sys.exit(1)

    try:
        # Determine which type of source it is
        if args.polygon:
            aoi = load_polygon_from_json(args.polygon)
        elif args.bbox:
            aoi = load_aoi(None, args.bbox)
        elif args.aoi:
            aoi = load_aoi(args.aoi, None)
        elif aoi_source.endswith(".geojson") or aoi_source.endswith(".json"):
            aoi = load_polygon_from_json(aoi_source)
        else:
            aoi = load_aoi(aoi_source, None)
    except Exception as e:
        print(f"Error loading AOI: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        G, graphml_path = build_aoi_graph(aoi_wgs84=aoi, node_area_ha=args.node_area_ha, out_dir=args.out, show=args.show)
        spacing_m = math.sqrt(args.node_area_ha * 10000.0)
        print(f"spacing_m={spacing_m:.3f}, nodes={G.number_of_nodes()}, edges={G.number_of_edges()}, crs=EPSG:4326")
    except Exception as e:
        print(f"Error building graph: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
