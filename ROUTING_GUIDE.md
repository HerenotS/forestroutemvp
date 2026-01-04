# Routing Scripts Guide

This directory contains practical routing scripts for the Forest Route MVP project.

## Quick Start

### 1. Fast Routing (Recommended for most use cases)

Generate waypoints in a regular grid pattern across your polygon:

```bash
python scripts/fast_routing.py --polygon inputs/map.geojson --output my_route --spacing-m 300
```

**Output:**
- `my_route/routes/route.geojson` - Route as GeoJSON (open in QGIS, Folium, etc.)
- `my_route/routes/route.kml` - Route as KML (open in Google Earth)
- `my_route/routing_report.json` - Summary statistics

**Parameters:**
- `--polygon` - Input polygon file (GeoJSON)
- `--output` - Output directory
- `--spacing-m` - Grid spacing in meters (default: 500m)

**Example outputs:**
- 100m spacing → dense coverage, ~10-12 km per km²
- 300m spacing → balanced coverage, ~3-4 km per km²
- 500m spacing → sparse coverage, ~1-2 km per km²
- 1000m spacing → very sparse coverage, ~0.3-0.4 km per km²

### 2. Simple Routing

Create waypoints and export route (no graph building):

```bash
python scripts/simple_routing.py --polygon inputs/map.geojson --output my_simple_route --spacing-m 500
```

Same output format as Fast Routing.

### 3. Routing with A* (Advanced)

Generate graph from polygon, snap waypoints to graph, and optimize with A*:

```bash
python scripts/routing_with_astar.py --polygon inputs/map.geojson --output my_astar_route --spacing-m 1000 --node-area-ha 4.0
```

**Note:** This is slower but produces optimized paths using A* graph search.

## Input File Format

Your polygon must be a valid GeoJSON file at `inputs/map.geojson`:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-99.47, 19.42],
            [-99.32, 19.42],
            [-99.32, 19.61],
            [-99.47, 19.61],
            [-99.47, 19.42]
          ]
        ]
      }
    }
  ]
}
```

## Output Files Explained

### route.geojson

GeoJSON format with a LineString representing the route:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [x1, y1], [x2, y2], ..., [xn, yn]
        ]
      },
      "properties": {
        "name": "Route",
        "total_length_m": 12345
      }
    }
  ]
}
```

**Visualize in:**
- QGIS (free, powerful GIS desktop)
- Folium (Python library for interactive maps)
- OpenStreetMap services
- ArcGIS

### route.kml

KML format for Google Earth:

```bash
# Open in Google Earth
google-earth-pro route.kml

# Or upload to Google MyMaps
```

### routing_report.json

Summary statistics:

```json
{
  "routing_type": "grid_waypoints",
  "parameters": {
    "spacing_m": 300
  },
  "results": {
    "waypoints": 2646,
    "total_distance_km": 825.83,
    "coverage_area_km2": 0.00
  }
}
```

## Common Workflows

### Workflow 1: Quick Visualization

```bash
# Generate route
python scripts/fast_routing.py --polygon inputs/map.geojson --output route1 --spacing-m 500

# Open in Google Earth
google-earth-pro route1/routes/route.kml
```

### Workflow 2: Python Analysis

```python
import geopandas as gpd
import json

# Load route
route = gpd.read_file("route1/routes/route.geojson")
print(f"Total length: {route.length[0] / 1000:.2f} km")

# Load report
with open("route1/routing_report.json") as f:
    report = json.load(f)
    print(f"Waypoints: {report['results']['waypoints']}")
```

### Workflow 3: Multiple Spacing Comparisons

```bash
# Generate routes with different spacings
for spacing in 200 300 500 1000; do
  python scripts/fast_routing.py --output "route_${spacing}m" --spacing-m $spacing
done
```

### Workflow 4: Custom Polygon

```bash
# Create your own polygon
cat > inputs/my_area.geojson << 'EOF'
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-99.4, 19.5],
          [-99.3, 19.5],
          [-99.3, 19.6],
          [-99.4, 19.6],
          [-99.4, 19.5]
        ]]
      }
    }
  ]
}
EOF

# Generate route
python scripts/fast_routing.py --polygon inputs/my_area.geojson --output my_custom_route --spacing-m 400
```

## Routing Grid Patterns

All scripts use a **snake/boustrophedon pattern** for efficient coverage:

```
→ → → →
← ← ← ←
→ → → →
← ← ← ←
```

This minimizes sharp turns and creates a natural sweep pattern, ideal for:
- Drone surveying
- Agricultural applications
- Environmental monitoring
- Search patterns

## Technical Details

### Coordinate Systems

- **Input**: WGS84 (EPSG:4326)
- **Processing**: Local UTM zone (automatically detected)
- **Output**: UTM (georeferenced, preserves distances)

### Grid Spacing Formula

Grid spacing is straightforward:
- Distance between points: **`spacing_m`**
- Points outside polygon: **automatically filtered**
- Row alternation: **snake pattern**

### Performance

- **fast_routing.py**: ~500 waypoints/second
- **simple_routing.py**: ~500 waypoints/second
- **routing_with_astar.py**: ~10 waypoints/second (includes graph building)

## Troubleshooting

### "ModuleNotFoundError" errors

Install missing dependencies:

```bash
pip install geopandas shapely rasterio pyproj networkx matplotlib
```

### Route has no waypoints

Check that:
1. Polygon file exists at `inputs/map.geojson`
2. Polygon is valid GeoJSON (use `ogr2ogr` or online validators)
3. Spacing is smaller than polygon dimensions
4. Polygon coordinates are in WGS84 format

### KML won't open in Google Earth

Ensure you have Google Earth Pro installed, or:
1. Upload to Google MyMaps instead
2. Convert to KMZ: `zip route.kmz route.kml`
3. Use online KML viewers

## Advanced: Combining with Cost Maps

For cost-aware routing (avoid high-cost areas):

```bash
# Generate cost map from rasters
python -m frp plan --polygon inputs/map.geojson \
  --nir rasters/ndvi.tif \
  --red rasters/red.tif \
  --resolution 10

# Use the optimized route from `out_demo/routes/route.geojson`
```

## API Usage (Python)

```python
from frp.aoi import load_aoi, get_utm_crs_for_geometry
from scripts.fast_routing import create_grid_waypoints
from frp.export import export_route

# Load polygon
aoi = load_aoi("inputs/map.geojson", None)
utm_crs = get_utm_crs_for_geometry(aoi)

# Create waypoints
waypoints_utm, _ = create_grid_waypoints(aoi, spacing_m=300)

# Export
export_route(waypoints_utm, str(utm_crs), 
             "output/routes/route.geojson",
             "output/routes/route.kml")

print(f"Generated {len(waypoints_utm)} waypoints")
```

## License

See LICENSE file in project root.
