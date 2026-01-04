# 🗺️ Forest Route MVP - Routing System

**Complete routing solution for generating waypoint routes from polygon areas.**

## 🚀 Quick Start (30 Seconds)

```bash
# Generate a route
python scripts/fast_routing.py --spacing-m 500

# View in Google Earth
open fast_routing_output/routes/route.kml
```

That's it! You now have a route with 400+ waypoints ready to use.

---

## 📚 Documentation

Start with one of these based on your needs:

| Document | Purpose | Time |
|----------|---------|------|
| **[QUICK_START_ROUTING.md](QUICK_START_ROUTING.md)** | Get first route in 30 seconds | 1 min |
| **[ROUTING_GUIDE.md](ROUTING_GUIDE.md)** | Learn how to use the system | 10 min |
| **[ROUTING_IMPLEMENTATION.md](ROUTING_IMPLEMENTATION.md)** | Understand the technology | 20 min |
| **[ROUTING_RESOURCES.md](ROUTING_RESOURCES.md)** | Find what you need | 5 min |

---

## 📦 What's Included

### Scripts
- ✅ **`scripts/fast_routing.py`** - Main routing script (recommended)
- ✅ **`scripts/simple_routing.py`** - Alternative implementation
- ✅ **`scripts/routing_with_astar.py`** - Advanced A* optimization

### Documentation
- ✅ Complete user guides
- ✅ Technical documentation
- ✅ API references
- ✅ Examples and workflows

### Example Outputs
- ✅ Sample route files (GeoJSON, KML)
- ✅ Various spacing examples
- ✅ Analysis reports

---

## ⚡ Features

✅ **Fast** - 1000+ waypoints in <1 second
✅ **Simple** - One command to generate route
✅ **Flexible** - Adjustable waypoint spacing (100m-1000m)
✅ **Multiple Formats** - GeoJSON, KML, JSON reports
✅ **Offline** - No cloud dependencies, local processing only
✅ **Well Documented** - Multiple documentation levels
✅ **GIS Ready** - Compatible with QGIS, Google Earth, PostGIS, Folium, etc.

---

## 📊 How It Works

```
Input Polygon (GeoJSON)
         ↓
Load & Validate
         ↓
Auto-detect UTM Zone
         ↓
Create Regular Waypoint Grid
         ↓
Export in Multiple Formats
         ↓
Output Files: GeoJSON, KML, JSON Report
```

**Typical Results:**
- 500m spacing → 420 waypoints, 130 km route
- 300m spacing → 1,200 waypoints, 370 km route
- 200m spacing → 2,650 waypoints, 825 km route

---

## 🎯 Use Cases

- 🚁 **Drone Survey Planning** - Generate flight paths
- 🌾 **Agricultural Monitoring** - Cover entire fields
- 🌍 **Ecosystem Surveys** - Systematic transect patterns
- 🔍 **Search & Rescue** - Organized sweep patterns
- 🔧 **Asset Inspection** - Equipment monitoring routes
- 🌳 **Conservation** - Forest monitoring routes

---

## 💻 Commands

### Basic Routing
```bash
# Default (500m spacing)
python scripts/fast_routing.py

# Custom spacing
python scripts/fast_routing.py --spacing-m 300

# Custom output
python scripts/fast_routing.py --output my_route --spacing-m 250

# Custom polygon
python scripts/fast_routing.py --polygon my_polygon.geojson
```

### Advanced Routing
```bash
# A* graph-based optimization
python scripts/routing_with_astar.py --spacing-m 1000 --node-area-ha 4.0
```

### View Results
```bash
# Google Earth
open fast_routing_output/routes/route.kml

# Or import into QGIS
# Layer → Add Vector Layer → fast_routing_output/routes/route.geojson
```

---

## 📂 File Structure

```
Forest Route MVP/
├── scripts/
│   ├── fast_routing.py           ⭐ Main script
│   ├── simple_routing.py
│   ├── routing_with_astar.py
│   └── complete_example.py
│
├── inputs/
│   └── map.geojson              ← Your polygon goes here
│
├── Documentation/
│   ├── QUICK_START_ROUTING.md    ← Start here!
│   ├── ROUTING_GUIDE.md
│   ├── ROUTING_IMPLEMENTATION.md
│   ├── ROUTING_RESOURCES.md
│   └── ROUTING_INDEX.md          ← This file
│
├── Example Outputs/
│   ├── fast_routing_output/
│   ├── test_fast/
│   └── final_test/
│
└── frp/
    ├── aoi.py
    ├── astar.py
    ├── cli.py
    ├── export.py
    ├── graph.py
    └── ... (core library)
```

---

## 🔧 System Requirements

- **Python**: 3.7+
- **Libraries**: geopandas, shapely, rasterio, pyproj, simplekml
- **OS**: Windows, macOS, Linux
- **Disk Space**: ~100 MB for large routes

**Install dependencies:**
```bash
pip install geopandas shapely rasterio pyproj simplekml
```

---

## 🎓 Next Steps

### 1️⃣ First Time?
Start with [QUICK_START_ROUTING.md](QUICK_START_ROUTING.md) - Get a route in 30 seconds

### 2️⃣ Want to Learn More?
Read [ROUTING_GUIDE.md](ROUTING_GUIDE.md) - Complete usage guide with examples

### 3️⃣ Need Technical Details?
See [ROUTING_IMPLEMENTATION.md](ROUTING_IMPLEMENTATION.md) - Architecture, API, performance

### 4️⃣ Looking for Something Specific?
Check [ROUTING_RESOURCES.md](ROUTING_RESOURCES.md) - Index and quick reference

---

## ✨ Example Workflow

### Step 1: Prepare Polygon
Place your polygon at `inputs/map.geojson`:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-99.4, 19.5], [-99.3, 19.5], [-99.3, 19.6], ...]]
    }
  }]
}
```

### Step 2: Generate Route
```bash
python scripts/fast_routing.py --spacing-m 300 --output my_survey
```

### Step 3: View Results
```bash
# Google Earth
open my_survey/routes/route.kml

# Or QGIS
# Import: my_survey/routes/route.geojson
```

### Step 4: Analyze
```python
import geopandas as gpd
import json

# Load route
route = gpd.read_file("my_survey/routes/route.geojson")
print(f"Route length: {route.length[0] / 1000:.2f} km")

# Load report
with open("my_survey/routing_report.json") as f:
    report = json.load(f)
    print(f"Waypoints: {report['results']['waypoints']}")
```

---

## 📊 Output Examples

### Spacing Comparison

| Spacing | Waypoints | Distance | Use Case |
|---------|-----------|----------|----------|
| 100m | 10,600 | 3,300 km | Dense UAV surveys |
| 200m | 2,650 | 825 km | Standard surveys |
| 300m | 1,180 | 370 km | Balanced coverage |
| 500m | 427 | 130 km | Moderate coverage |
| 1000m | 107 | 33 km | Reconnaissance |

### File Sizes

| Format | Size (typical) |
|--------|---|
| route.geojson | 150-200 KB |
| route.kml | 150-200 KB |
| routing_report.json | 0.5 KB |

---

## 🚀 Getting Started NOW

Copy-paste this to get your first route immediately:

```bash
# 1. Make sure polygon is at inputs/map.geojson
# 2. Run this:
python scripts/fast_routing.py --spacing-m 500 --output my_first_route

# 3. Open the result (Windows):
start my_first_route/routes/route.kml

# 3. Open the result (macOS/Linux):
open my_first_route/routes/route.kml
```

**Done!** Your route is now visible in Google Earth.

---

## 🎯 Key Capabilities

✅ Generate routes from any polygon
✅ Adjust coverage density (100m-1000m spacing)
✅ Export in standard GIS formats (GeoJSON, KML)
✅ Works offline with no external APIs
✅ Integrates with QGIS, Google Earth, PostGIS
✅ Python-friendly for automation
✅ Fast execution (1000+ waypoints/second)

---

## 📞 Need Help?

1. **Quick question?** → Check [QUICK_START_ROUTING.md](QUICK_START_ROUTING.md)
2. **How do I use it?** → Read [ROUTING_GUIDE.md](ROUTING_GUIDE.md)
3. **How does it work?** → See [ROUTING_IMPLEMENTATION.md](ROUTING_IMPLEMENTATION.md)
4. **Can't find something?** → Check [ROUTING_RESOURCES.md](ROUTING_RESOURCES.md)

---

## 📈 Performance

All scripts generate 1000+ waypoints in **<1 second** on standard hardware.

```
100m spacing:  ~10,600 waypoints → <1 second
500m spacing:  ~427 waypoints    → <1 second  
1000m spacing: ~107 waypoints    → <1 second
```

---

## ✅ Status

✅ **Complete & Ready to Use**
- Tested with multiple polygon sizes
- Works with QGIS, Google Earth, web maps
- Full documentation included
- Example outputs provided

---

## 📄 Documentation Index

```
START HERE:
└─ QUICK_START_ROUTING.md         (This is the entry point!)

DETAILED GUIDES:
├─ ROUTING_GUIDE.md               (Complete usage guide)
├─ ROUTING_IMPLEMENTATION.md      (Technical details & API)
├─ ROUTING_RESOURCES.md           (Quick reference & index)
└─ ROUTING_SUMMARY.md             (Overview summary)

THIS FILE:
└─ ROUTING_INDEX.md               (General information)
```

---

## 🎉 You're Ready!

1. Go to [QUICK_START_ROUTING.md](QUICK_START_ROUTING.md)
2. Run the example
3. View your route in Google Earth
4. Customize spacing and parameters as needed

**Let's route! 🗺️**

---

**Created**: 2024
**Status**: ✅ Complete and tested
**Last Updated**: 2024
