#!/usr/bin/env python3
"""Convert map.geojson polygon area to a 200m-spaced graph.

Creates a graph with nodes spaced approximately 200 meters apart in real life,
converts to a route visualization, and saves as GeoJSON.

Usage:
  python scripts/map_to_graph.py [--input map.geojson] [--output output_dir] [--spacing-m 200]
"""
import argparse
import sys
from pathlib import Path
import math
import json

# Add parent dir to path for frp imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from frp.aoi import load_aoi
from frp.graph import build_aoi_graph


def main():
    p = argparse.ArgumentParser(
        description="Convert map.geojson polygon area to a 200m-spaced graph"
    )
    p.add_argument(
        "--input",
        default="inputs/map.geojson",
        help="Input polygon GeoJSON file (default: inputs/map.geojson)"
    )
    p.add_argument(
        "--output",
        default="map_graph",
        help="Output directory for graph files (default: map_graph)"
    )
    p.add_argument(
        "--spacing-m",
        type=float,
        default=200,
        help="Node spacing in meters (default: 200m)"
    )
    
    args = p.parse_args()
    
    # Convert spacing to hectares: area = spacing_m^2 / 10000
    node_area_ha = (args.spacing_m ** 2) / 10000.0
    
    print(f"Map-to-Graph Converter")
    print(f"=====================")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Spacing: {args.spacing_m}m")
    print(f"Node area: {node_area_ha:.3f} hectares")
    print()
    
    try:
        # Load the polygon from map.geojson
        print(f"Loading polygon from {args.input}...")
        aoi = load_aoi(args.input, None)
        print(f"✓ Polygon loaded successfully")
        print(f"  Bounds: {aoi.bounds}")
        
        # Build graph from the polygon area
        print(f"\nBuilding graph with {args.spacing_m}m node spacing...")
        Path(args.output).mkdir(parents=True, exist_ok=True)
        
        G, graphml_path = build_aoi_graph(
            aoi_wgs84=aoi,
            node_area_ha=node_area_ha,
            out_dir=args.output,
            show=False
        )
        
        print(f"✓ Graph created successfully")
        print(f"  Nodes: {G.number_of_nodes()}")
        print(f"  Edges: {G.number_of_edges()}")
        print(f"  GraphML: {graphml_path}")
        
        # List output files
        output_path = Path(args.output)
        print(f"\nOutput files:")
        for f in sorted(output_path.glob("*")):
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                print(f"  - {f.name} ({size_kb:.1f} KB)")
        
        print(f"\n✓ Conversion complete!")
        print(f"\nNext steps:")
        print(f"  1. Use the graph nodes/edges for planning")
        print(f"  2. Visualize: python scripts/visualize_graph_with_route.py --nodes {output_path}/nodes.geojson --edges {output_path}/edges.geojson --route <route.geojson>")
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
