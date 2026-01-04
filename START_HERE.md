# 🚀 START HERE - Routing in 3 Steps

## What This Does
Generates a route with waypoints across your polygon area, ready for use in GIS software, drones, or surveys.

---

## 3-Step Setup

### Step 1: Run the Script
```bash
python scripts/fast_routing_simple.py --spacing-m 500
```

### Step 2: Check the Output
```
fast_routing_output/routes/route.geojson  ← Your route file!
```

### Step 3: View Your Route
**Option A: QGIS (Recommended - Free)**
1. Download QGIS: https://www.qgis.org/
2. Open QGIS
3. Layer → Add Vector Layer
4. Select: `fast_routing_output/routes/route.geojson`
5. Your route appears on the map!

**Option B: Python**
```python
import geopandas as gpd
route = gpd.read_file("fast_routing_output/routes/route.geojson")
print(f"Distance: {route.length[0] / 1000:.2f} km")
```

**Option C: Command Line**
```bash
# View GeoJSON content
cat fast_routing_output/routes/route.geojson
```

---

## That's It!

You now have a complete route with waypoints ready to use.

---

## Next: Customize Your Route

### Change the Coverage Spacing

```bash
# Denser coverage (more waypoints)
python scripts/fast_routing_simple.py --spacing-m 200

# Sparser coverage (fewer waypoints)
python scripts/fast_routing_simple.py --spacing-m 1000

# Very dense coverage
python scripts/fast_routing_simple.py --spacing-m 100
```

### Use a Different Polygon

Place your polygon at `inputs/my_polygon.geojson`, then:
```bash
python scripts/fast_routing_simple.py --polygon inputs/my_polygon.geojson --output my_route
```

### Custom Output Location

```bash
python scripts/fast_routing_simple.py --output my_custom_output_folder
```

---

## Spacing Guide

What spacing should you use?

| Spacing | Waypoints | Coverage | Best For |
|---------|-----------|----------|----------|
| **100m** | 10,000+ | Very dense | Detailed surveys, drones |
| **200m** | 2,650 | Dense | Standard surveys |
| **300m** | 1,200 | Balanced | Recommended |
| **500m** | 427 | Moderate | Quick preview |
| **1000m** | 107 | Sparse | Reconnaissance |

**Default: 500m** - Good for most use cases

---

## Output File Explanation

### `route.geojson`
Standard GeoJSON format containing your route as a LineString:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "geometry": {
      "type": "LineString",
      "coordinates": [
        [-99.47, 19.42],
        [-99.47, 19.43],
        [-99.47, 19.44],
        ...
      ]
    }
  }]
}
```

Use with:
- QGIS
- ArcGIS
- Folium (Python web maps)
- Leaflet.js (JavaScript maps)
- Google MyMaps
- Cesium (3D web maps)
- Any GIS tool

### `routing_report.json`
Summary statistics:
```json
{
  "waypoints": 427,
  "total_distance_km": 130.48,
  "spacing_m": 500,
  "utm_crs": "EPSG:32614"
}
```

---

## Example: Use in QGIS

**5 minutes to see your route on a map:**

1. Download QGIS (free): https://www.qgis.org/
2. Run routing script:
   ```bash
   python scripts/fast_routing_simple.py
   ```
3. Open QGIS
4. Open a basemap: Web → OpenStreetMap → OpenStreetMap
5. Add your route: Layer → Add Vector Layer → `fast_routing_output/routes/route.geojson`
6. See your waypoints on the map!

---

## Example: Use in Python

**Analyze your route programmatically:**

```python
import geopandas as gpd
import json

# Load the route
route = gpd.read_file("fast_routing_output/routes/route.geojson")

# Get route length
length_km = route.length[0] / 1000
print(f"Route length: {length_km:.2f} km")

# Get coordinates
coords = route.geometry[0].coords[:]
print(f"Number of waypoints: {len(coords)}")

# Load statistics
with open("fast_routing_output/routing_report.json") as f:
    stats = json.load(f)
    print(f"Distance from report: {stats['total_distance_km']:.2f} km")
```

---

## Input Format

Your polygon must be valid GeoJSON at `inputs/map.geojson`:

```json
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
```

**Validate your GeoJSON:** https://geojsonlint.com/

---

## Troubleshooting

### Script won't run?
```bash
# Install dependencies
pip install geopandas shapely pyproj
```

### "Polygon file not found"
```bash
# Check file exists
ls inputs/map.geojson

# Or use a different path
python scripts/fast_routing_simple.py --polygon path/to/your/polygon.geojson
```

### "No route generated"
- Try reducing spacing: `--spacing-m 200`
- Validate polygon at https://geojsonlint.com/
- Check polygon bounds are valid

### Still stuck?
Check `QUICK_START_ROUTING.md` for more detailed help.

---

## What You Can Do With Your Route

✅ Visualize in QGIS
✅ Upload to Google MyMaps
✅ Use in web maps (Folium, Leaflet)
✅ Import into ArcGIS
✅ Use for drone flight planning
✅ Convert to other formats (shapefile, etc.)
✅ Analyze with Python/pandas
✅ Share as GeoJSON
✅ Use in spatial databases (PostGIS)

---

## One Command to Get Started

Copy and run this:

```bash
python scripts/fast_routing_simple.py --spacing-m 500 --output my_first_route
```

**Done!** Open `my_first_route/routes/route.geojson` in QGIS.

---

## Common Patterns

### Compare different spacings
```bash
python scripts/fast_routing_simple.py --spacing-m 200 --output route_200m
python scripts/fast_routing_simple.py --spacing-m 500 --output route_500m
python scripts/fast_routing_simple.py --spacing-m 1000 --output route_1000m
```

### Process multiple polygons
```bash
python scripts/fast_routing_simple.py --polygon area1.geojson --output route_area1
python scripts/fast_routing_simple.py --polygon area2.geojson --output route_area2
python scripts/fast_routing_simple.py --polygon area3.geojson --output route_area3
```

### Batch processing script
```bash
for spacing in 100 200 300 500 1000; do
  echo "Generating route with ${spacing}m spacing..."
  python scripts/fast_routing_simple.py --spacing-m $spacing --output "route_${spacing}m"
done
```

---

## Next Steps

1. **Run the script** (takes <1 second)
2. **View in QGIS** (free, easy)
3. **Customize spacing** based on your needs
4. **Read documentation** for advanced features

---

## Documentation Files

- **You are here**: This file (quick start)
- **More details**: `QUICK_START_ROUTING.md`
- **Complete guide**: `ROUTING_GUIDE.md`
- **Technical details**: `ROUTING_IMPLEMENTATION.md`
- **Delivery summary**: `DELIVERY_SUMMARY.md`

---

## That's Everything You Need!

### Now run this:

```bash
python scripts/fast_routing_simple.py
```

Your route is ready in: `fast_routing_output/routes/route.geojson`

**Congratulations! You have a working routing system! 🎉**

---

Questions? Check the other documentation files or try the QGIS walkthrough above.

Made with ❤️ for Forest Route MVP
