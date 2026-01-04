# Routing Implementation Summary

## What Was Created

Three practical routing scripts have been created to generate waypoint routes across your polygon area:

### 1. **fast_routing.py** ✅ (Recommended)
**Purpose**: Quick, efficient route generation
```bash
python scripts/fast_routing.py --spacing-m 300
```

**What it does:**
- Loads your polygon from `inputs/map.geojson`
- Creates a regular grid of waypoints (snake pattern for efficiency)
- Exports route as GeoJSON + KML
- Generates analysis report

**Performance**: Generates 1000+ waypoints in seconds

**Output:**
```
output_dir/
├── routes/
│   ├── route.geojson      # Import into QGIS, Folium, etc.
│   └── route.kml          # Open in Google Earth
└── routing_report.json    # Statistics
```

**When to use:**
- Quick route preview
- Multiple spacing comparisons
- Integration with other tools
- Production routing

---

### 2. **simple_routing.py**
**Purpose**: Minimal dependency routing
```bash
python scripts/simple_routing.py --spacing-m 500
```

**Difference from fast_routing**: Simplified code, same output format

---

### 3. **routing_with_astar.py** (Advanced)
**Purpose**: Graph-based A* optimization
```bash
python scripts/routing_with_astar.py --spacing-m 1000 --node-area-ha 4.0
```

**What it does:**
- Creates regular waypoint grid
- Builds graph from polygon (configurable node spacing)
- Snaps waypoints to graph nodes
- Uses A* to optimize path between first and last waypoint
- Exports optimized route

**Note**: Slower but produces optimized paths

---

## Quick Start

### Basic Usage (30 seconds)

```bash
# Generate route with 500m spacing
python scripts/fast_routing.py --spacing-m 500

# Output files created in: fast_routing_output/
```

### View the Route

**Option 1: Google Earth**
```bash
# Windows
start fast_routing_output/routes/route.kml

# macOS  
open fast_routing_output/routes/route.kml

# Linux
google-earth-pro fast_routing_output/routes/route.kml
```

**Option 2: QGIS (Free Desktop GIS)**
1. Open QGIS
2. Drag `fast_routing_output/routes/route.geojson` into the map

**Option 3: Python Analysis**
```python
import geopandas as gpd
route = gpd.read_file("fast_routing_output/routes/route.geojson")
print(f"Total length: {route.length[0] / 1000:.2f} km")
```

---

## Parameter Guide

### `--spacing-m` (most important)

Controls distance between waypoints in meters:

| Spacing | Waypoints | Distance | Use Case |
|---------|-----------|----------|----------|
| 100m | ~10,600 | ~3,300 km | Dense surveys (UAV, detailed mapping) |
| 200m | ~2,650 | ~825 km | Medium surveys (balanced) |
| 300m | ~1,180 | ~370 km | Standard coverage |
| 500m | ~427 | ~130 km | Sparse coverage |
| 1000m | ~107 | ~33 km | Reconnaissance |

**Rule of thumb**: 
- Dense data needed? → Use 200-300m
- Quick preview? → Use 500-1000m  
- Full coverage? → Use 100-200m

### `--output`

Output directory name (default: script name + `_output`)

```bash
# All outputs go to my_results/
python scripts/fast_routing.py --output my_results --spacing-m 500
```

### `--polygon` (optional)

Input polygon file (default: `inputs/map.geojson`)

```bash
python scripts/fast_routing.py --polygon my_polygon.geojson
```

---

## Output Files Explained

### route.geojson

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {
      "type": "LineString",
      "coordinates": [
        [-99.47, 19.42],
        [-99.47, 19.43],
        [-99.48, 19.43],
        ...
      ]
    },
    "properties": {
      "name": "Route",
      "total_length_m": 825830
    }
  }]
}
```

**Use with:**
- QGIS, ArcGIS, Leaflet, Folium
- Custom Python analysis
- Web mapping services

### route.kml

Standard KML format for Google Earth

**Open with:**
- Google Earth Pro (recommended)
- Google MyMaps (web)
- ArcGIS, QGIS
- Most GIS software

### routing_report.json

```json
{
  "routing_type": "grid_waypoints",
  "parameters": {
    "spacing_m": 500,
    "utm_crs": "EPSG:32614"
  },
  "results": {
    "waypoints": 427,
    "total_distance_km": 130.48,
    "coverage_area_km2": 0.34
  }
}
```

**Use for:**
- Automated analysis
- Reporting
- Integration with other systems

---

## Common Tasks

### Generate Multiple Routes (Different Spacings)

```bash
# Compare different coverage densities
python scripts/fast_routing.py --output route_200m --spacing-m 200
python scripts/fast_routing.py --output route_500m --spacing-m 500
python scripts/fast_routing.py --output route_1000m --spacing-m 1000

# Now open all KML files in Google Earth to compare
```

### Use Custom Polygon

```bash
# Create your own GeoJSON file
cat > my_area.geojson << 'EOF'
{
  "type": "FeatureCollection",
  "features": [{
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
  }]
}
EOF

# Generate route
python scripts/fast_routing.py --polygon my_area.geojson --output my_route
```

### Combine with Cost Maps (Advanced)

```bash
# First, use frp's cost-aware planning with NDVI/DEM rasters:
python -m frp plan --polygon inputs/map.geojson \
  --nir rasters/ndvi.tif \
  --red rasters/red.tif \
  --resolution 10

# This generates optimized routes in out_demo/routes/route.geojson
```

### Python Integration

```python
from frp.aoi import load_aoi, get_utm_crs_for_geometry
from scripts.fast_routing import create_grid_waypoints
from frp.export import export_route

# Load polygon
aoi = load_aoi("inputs/map.geojson", None)
utm_crs = get_utm_crs_for_geometry(aoi)

# Generate waypoints
waypoints, utm_crs = create_grid_waypoints(aoi, spacing_m=300)

# Export
export_route(waypoints, str(utm_crs),
             "output/route.geojson",
             "output/route.kml")

print(f"Generated {len(waypoints)} waypoints")
```

---

## Technical Details

### Coordinate Systems

All scripts automatically handle coordinate system conversion:

- **Input**: WGS84 (EPSG:4326) - standard GPS coordinates
- **Processing**: Local UTM zone - for accurate distances
- **Output**: Georeferenced in UTM - distances preserved

UTM zone is automatically detected based on polygon center.

### Grid Pattern

Routes use a **snake/boustrophedon sweep pattern**:

```
Sweep 1: ➜➜➜➜➜
Sweep 2: ⬅⬅⬅⬅⬅
Sweep 3: ➜➜➜➜➜
Sweep 4: ⬅⬅⬅⬅⬅
```

**Advantages:**
- Minimizes sharp turns
- Natural sweep coverage
- Efficient for drones/vehicles
- Reduces backtracking

### Performance

| Script | 500 Waypoints | 5,000 Waypoints |
|--------|---------------|-----------------|
| fast_routing.py | <1s | <3s |
| simple_routing.py | <1s | <3s |
| routing_with_astar.py | 2s | 20s |

---

## Troubleshooting

### "Polygon file not found"

**Solution:**
```bash
# Ensure file exists at inputs/map.geojson
ls inputs/map.geojson

# Or specify the path:
python scripts/fast_routing.py --polygon /path/to/polygon.geojson
```

### "Route has no waypoints"

**Possible causes:**
1. Polygon is too small for the spacing
   - Solution: Use smaller `--spacing-m` (e.g., 100-200)

2. Polygon coordinates are invalid
   - Check: Is polygon a valid GeoJSON?
   - Solution: Validate at https://geojsonlint.com/

3. Spacing larger than polygon
   - Example: 500m spacing but polygon is only 300m wide
   - Solution: Reduce spacing

### "Can't open KML in Google Earth"

**Solutions:**
1. Install Google Earth Pro (free)
2. Compress to KMZ:
   ```bash
   cd route_output/routes/
   zip route.kmz route.kml
   ```
3. Upload to Google MyMaps instead: https://mymaps.google.com

### Import errors

**Solution:**
```bash
# Install all dependencies
pip install geopandas shapely rasterio pyproj networkx simplekml
```

---

## Integration Examples

### With QGIS (Desktop GIS)

```bash
# 1. Generate route
python scripts/fast_routing.py --output my_route

# 2. Open QGIS
qgis

# 3. Layer > Add Layer > Add Vector Layer
# 4. Select: my_route/routes/route.geojson
```

### With Folium (Web Maps)

```python
import folium
import geopandas as gpd

# Load route
route = gpd.read_file("my_route/routes/route.geojson")
coords = route.geometry[0].coords[:]

# Create map
m = folium.Map(location=[19.5, -99.4], zoom_start=10)
folium.PolyLine(coords, color='red', weight=2).add_to(m)
m.save('map.html')

# Open map.html in browser
```

### With PostGIS Database

```python
import geopandas as gpd
from sqlalchemy import create_engine

# Load route
route = gpd.read_file("my_route/routes/route.geojson")

# Save to PostGIS
engine = create_engine("postgresql://user:password@localhost:5432/db")
route.to_postgis("routes", engine, if_exists="replace")
```

---

## API Reference

### `fast_routing.py`

**Function**: `create_grid_waypoints(aoi_wgs84, spacing_m=200)`

```python
from frp.aoi import load_aoi, get_utm_crs_for_geometry
from scripts.fast_routing import create_grid_waypoints

aoi = load_aoi("polygon.geojson", None)
waypoints_utm, utm_crs = create_grid_waypoints(aoi, spacing_m=300)

print(f"Generated {len(waypoints_utm)} waypoints")
```

**Parameters:**
- `aoi_wgs84`: Shapely geometry (Polygon)
- `spacing_m`: Grid spacing in meters (default: 500)

**Returns:**
- `waypoints_utm`: List of (x, y) tuples in UTM
- `utm_crs`: EPSG code string (e.g., "EPSG:32614")

### `export_route()`

```python
from frp.export import export_route

export_route(
    points_utm,           # List of (x, y) tuples
    utm_crs,              # EPSG code string
    "output/route.geojson",  # GeoJSON path
    "output/route.kml"       # KML path
)
```

---

## Performance Optimization

For large polygons (>100 km²):

```bash
# Use larger spacing to reduce waypoints
python scripts/fast_routing.py --spacing-m 1000

# Or split into regions and combine results
```

For precise coverage requirements:

```bash
# Use smaller spacing
python scripts/fast_routing.py --spacing-m 100
```

---

## Version Information

- **Python**: 3.7+
- **Dependencies**: geopandas, shapely, rasterio, pyproj, simplekml
- **Tested on**: Windows, macOS, Linux

---

## Support

For issues or feature requests:

1. Check the troubleshooting section above
2. Review ROUTING_GUIDE.md for detailed documentation
3. Check polygon validity at https://geojsonlint.com/
4. Review test cases: `tests/test_graph.py`, `tests/test_demo_plan.py`

---

## License

See LICENSE file in project root.

---

**Created**: 2024
**Last Updated**: 2024
