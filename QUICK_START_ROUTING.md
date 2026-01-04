# 🚀 Quick Start - Routing

## 30-Second Setup

### 1. Generate a Route
```bash
python scripts/fast_routing.py --spacing-m 500
```

**That's it!** Your route is now in `fast_routing_output/routes/`

### 2. View the Route

Open the KML file in Google Earth:
```bash
# Windows
start fast_routing_output/routes/route.kml

# macOS/Linux  
open fast_routing_output/routes/route.kml
```

Or import the GeoJSON into QGIS or any other GIS tool.

---

## What You Get

✅ **route.geojson** - Import into QGIS, Folium, or any GIS software
✅ **route.kml** - Open in Google Earth Pro
✅ **routing_report.json** - Statistics and metadata

---

## Available Scripts

| Script | Use Case | Speed |
|--------|----------|-------|
| `fast_routing.py` | Quick route generation | ⚡ <1s |
| `simple_routing.py` | Minimal dependencies | ⚡ <1s |
| `routing_with_astar.py` | Graph-based optimization | 🐢 2-20s |

---

## Examples

### Dense Coverage (200m spacing)
```bash
python scripts/fast_routing.py --spacing-m 200 --output dense_route
```
**Result**: 10,000+ waypoints, 3,000 km of route

### Quick Preview (1000m spacing)
```bash
python scripts/fast_routing.py --spacing-m 1000 --output preview
```
**Result**: 100+ waypoints, 30 km of route

### Custom Polygon
```bash
python scripts/fast_routing.py --polygon my_area.geojson --output my_route
```

---

## Parameters Cheat Sheet

```bash
python scripts/fast_routing.py \
  --polygon inputs/map.geojson    # Input polygon (default shown)
  --output my_route                # Output directory
  --spacing-m 500                  # Waypoint spacing (meters)
```

---

## Spacing Guide

- **100m** - Ultra-dense, very detailed coverage
- **200m** - Dense coverage (recommended for UAV surveys)
- **300m** - Balanced coverage (default-ish)
- **500m** - Moderate spacing (quick preview)
- **1000m** - Sparse coverage (fast, minimal waypoints)

---

## Next Steps

1. ✅ Generated a route
2. 📊 View in Google Earth or QGIS
3. 🔄 Iterate with different spacings
4. 📤 Export for use in your workflow

---

## Troubleshooting

**"ModuleNotFoundError"?**
```bash
pip install geopandas shapely rasterio pyproj simplekml
```

**Route is empty?**
- Check that polygon file exists: `inputs/map.geojson`
- Reduce spacing (e.g., 200m instead of 1000m)
- Validate polygon at: https://geojsonlint.com/

**Can't open KML?**
- Download Google Earth Pro: https://www.google.com/earth/versions/
- Or import GeoJSON into QGIS (free): https://www.qgis.org/

---

## Documentation

- **Full Guide**: See `ROUTING_GUIDE.md`
- **Implementation Details**: See `ROUTING_IMPLEMENTATION.md`
- **API Reference**: See `ROUTING_IMPLEMENTATION.md` - API Reference section

---

**Ready to route? Run:**
```bash
python scripts/fast_routing.py
```
