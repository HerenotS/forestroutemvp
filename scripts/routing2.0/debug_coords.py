#!/usr/bin/env python
"""Debug script to trace coordinate handling through the pipeline."""

from pipeline_full import generate_synthetic_terrain
from multidim_graph import build_multidim_graph
from cost_3d_model import build_3d_model
from pathlib import Path
import json
import numpy as np

# Use user's test coordinates
test_geojson = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "coordinates": [
          [
            [-99.48102480900964, 19.33092754657079],
            [-99.45615992746475, 19.174421321106877],
            [-99.19438553686399, 19.238597791679112],
            [-99.28224730285173, 19.31677622590452],
            [-99.42147679874869, 19.372813645373085],
            [-99.48102480900964, 19.33092754657079]
          ]
        ],
        "type": "Polygon"
      }
    }
  ]
}

coords = test_geojson["features"][0]["geometry"]["coordinates"][0]
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]
bounds = (min(lons), min(lats), max(lons), max(lats))

print("="*60)
print("DEBUG: Coordinate Tracing")
print("="*60)
print(f"\nInput Polygon Bounds:")
print(f"  Min Lon: {bounds[0]:.6f}")
print(f"  Min Lat: {bounds[1]:.6f}")
print(f"  Max Lon: {bounds[2]:.6f}")
print(f"  Max Lat: {bounds[3]:.6f}")

# Generate rasters
out_dir = Path("test_coord_debug")
raster_dir = out_dir / "rasters"
raster_dir.mkdir(parents=True, exist_ok=True)

print("\n--- Generating Synthetic Terrain ---")
result = generate_synthetic_terrain(bounds, raster_dir, resolution_deg=0.001)

meta = result["meta"]
print(f"\nRaster Metadata:")
print(f"  CRS: {meta['crs']}")
print(f"  Width: {meta['width']} pixels")
print(f"  Height: {meta['height']} pixels")
print(f"  Transform: {meta['transform']}")

# Decode transform
t = meta["transform"]
print(f"\nTransform Decoded:")
print(f"  Origin X (top-left lon): {t.c:.6f}")
print(f"  Origin Y (top-left lat): {t.f:.6f}")
print(f"  Pixel Size X: {t.a:.8f}")
print(f"  Pixel Size Y: {t.e:.8f}")

# Calculate expected bounds from transform
calc_max_lon = t.c + t.a * meta["width"]
calc_min_lat = t.f + t.e * meta["height"]
print(f"\nCalculated Raster Bounds from Transform:")
print(f"  Min Lon: {t.c:.6f} (expected {bounds[0]:.6f})")
print(f"  Max Lat: {t.f:.6f} (expected {bounds[3]:.6f})")
print(f"  Max Lon: {calc_max_lon:.6f} (expected {bounds[2]:.6f})")
print(f"  Min Lat: {calc_min_lat:.6f} (expected {bounds[1]:.6f})")

# Check elevation data range
elev = result["data"]["elevation"]
print(f"\nElevation Data:")
print(f"  Shape: {elev.shape}")
print(f"  Min: {np.nanmin(elev):.2f}m")
print(f"  Max: {np.nanmax(elev):.2f}m")

# Build graph
print("\n--- Building Multi-dimensional Graph ---")
G, graph_meta = build_multidim_graph(
    cost_path=str(result["cost"]),
    slope_path=str(result["slope"]),
    ndvi_path=str(result["ndvi"]),
    elevation_path=str(result["elevation"]),
    node_spacing=5,
    connectivity=8,
    polygon_coords=coords
)

print(f"\nGraph Statistics:")
print(f"  Nodes: {G.number_of_nodes()}")
print(f"  Edges: {G.number_of_edges()}")

# Sample some nodes to check coordinates
sample_nodes = list(G.nodes())[:5]
print(f"\nSample Node Coordinates (first 5):")
for n in sample_nodes:
    data = G.nodes[n]
    print(f"  Node {n}: x={data.get('x', 'N/A'):.6f}, y={data.get('y', 'N/A'):.6f}, "
          f"altitude={data.get('altitude', 'N/A'):.2f}, cost={data.get('cost', 'N/A'):.4f}")

# Check coordinate ranges
all_x = [G.nodes[n].get("x", 0) for n in G.nodes()]
all_y = [G.nodes[n].get("y", 0) for n in G.nodes()]
all_z = [G.nodes[n].get("altitude", 0) for n in G.nodes()]

print(f"\nGraph Coordinate Ranges:")
print(f"  X (Lon): {min(all_x):.6f} to {max(all_x):.6f}")
print(f"  Y (Lat): {min(all_y):.6f} to {max(all_y):.6f}")
print(f"  Z (Alt): {min(all_z):.2f} to {max(all_z):.2f}")

# Expected ranges
print(f"\nExpected Ranges (from polygon):")
print(f"  X (Lon): {bounds[0]:.6f} to {bounds[2]:.6f}")
print(f"  Y (Lat): {bounds[1]:.6f} to {bounds[3]:.6f}")

# Check if they match
lon_ok = abs(min(all_x) - bounds[0]) < 0.01 or abs(max(all_x) - bounds[2]) < 0.01
lat_ok = abs(min(all_y) - bounds[1]) < 0.01 or abs(max(all_y) - bounds[3]) < 0.01
print(f"\nCoordinate Match Check:")
print(f"  Longitude approximately correct: {lon_ok}")
print(f"  Latitude approximately correct: {lat_ok}")

if not lon_ok or not lat_ok:
    print("\n*** WARNING: Graph coordinates do not match expected polygon bounds! ***")
    print("    This indicates coordinates are not being properly transferred.")

# Build 3D model
print("\n--- Building 3D Cost Model ---")
model_out = out_dir / "3d_model" / "test_terrain.html"
model_out.parent.mkdir(parents=True, exist_ok=True)

model_result = build_3d_model(
    cost_path=str(result["cost"]),
    output_path=str(model_out),
    slope_path=str(result["slope"]),
    ndvi_path=str(result["ndvi"]),
    elevation_path=str(result["elevation"]),
    subsample=1,
    use_plotly=True
)

print(f"\n3D Model Created: {model_out}")
print(f"  Priority Anchor: ({model_result['priority_anchor']['row']}, {model_result['priority_anchor']['col']})")

print("\n" + "="*60)
print("Debug complete. Check test_coord_debug/ for outputs.")
print("="*60)
