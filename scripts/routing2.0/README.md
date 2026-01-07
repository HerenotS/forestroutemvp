# Routing 2.0 - 3D Visualization and Multi-dimensional Graph Routing

Advanced terrain-aware routing with 3D visualization and multi-factor optimization.

## Features

- **3D Cost Terrain Model**: Interactive visualization where elevation represents cost values
- **Multi-dimensional NetworkX Graph**: Nodes and edges with terrain factor attributes
- **Priority-based Routing**: A* pathfinding with customizable factor weights
- **Interactive Visualizations**: Plotly 3D and Matplotlib 2D outputs
- **Comprehensive Reports**: Markdown and JSON reports explaining factor influences

## Installation

Ensure you have the required dependencies:

```bash
pip install plotly networkx rasterio numpy matplotlib scipy
```

## Quick Start

### Run the Complete Pipeline

```bash
# From project root
cd scripts/routing2.0
python pipeline.py --raster-dir ../../out_demo_plan/rasters

# Or specify all paths
python pipeline.py \
    --config ../../config.json \
    --polygon ../../inputs/map.geojson \
    --raster-dir ../../out_demo_plan/rasters \
    --output-dir ./output
```

### Use Individual Modules

```python
from scripts.routing2_0 import cost_3d_model, multidim_graph, route_optimizer

# Build 3D model
results = cost_3d_model.build_3d_model(
    cost_path="path/to/cost.tif",
    output_dir="output/3d_model",
    slope_path="path/to/slope.tif",
    ndvi_path="path/to/ndvi.tif"
)

# Build multi-dimensional graph
G, meta = multidim_graph.build_multidim_graph(
    cost_path="path/to/cost.tif",
    slope_path="path/to/slope.tif",
    ndvi_path="path/to/ndvi.tif"
)

# Optimize route
route = route_optimizer.optimize_route_demo(G)
```

## Modules

### cost_3d_model.py
Transforms cost rasters into 3D terrain models.
- `build_3d_model()`: Main function generating HTML and PNG outputs
- `find_min_cost_point()`: Locates priority anchor (lowest cost)
- `generate_3d_plotly_html()`: Interactive 3D visualization

### multidim_graph.py
Builds NetworkX graphs with terrain attributes.
- `build_multidim_graph()`: Creates graph with node/edge attributes
- `save_graph()`: Export to GraphML/GEXF/JSON
- `get_graph_statistics()`: Compute graph metrics

### priority_analyzer.py
Analyzes terrain priorities and distributions.
- `find_priority_anchor()`: Global minimum cost point
- `find_local_minima()`: Multiple anchor candidates
- `compute_priority_zones()`: Quantile-based zoning
- `generate_priority_report()`: Complete analysis

### route_optimizer.py
Multi-factor A* pathfinding.
- `astar_multifactor()`: A* with weighted factors
- `optimize_route_demo()`: Auto-detect start/goal
- `compare_weight_strategies()`: Compare routing strategies

### graph_visualizer.py
2D and 3D visualization of graphs and routes.
- `visualize_2d_priority_map()`: 2D priority coloring
- `visualize_3d_network()`: Interactive 3D network
- `visualize_route_comparison()`: Multi-route comparison

### report_generator.py
Generate summary reports.
- `generate_summary_report()`: Complete markdown report
- `save_report()`: Save MD and JSON versions

### pipeline.py
Main orchestration script.
- `run_pipeline()`: Execute complete workflow
- CLI with configurable parameters

## Output Structure

```
output/
├── 3d_model/
│   ├── cost_terrain_3d.html        # Interactive 3D visualization
│   └── cost_terrain_3d_static.png  # Static image
├── graph/
│   ├── multidim_graph.graphml      # NetworkX GraphML export
│   └── multidim_graph.json         # JSON format
├── visualizations/
│   ├── priority_map_2d.png         # 2D priority map with route
│   ├── priority_heatmap.png        # Priority heatmap
│   ├── network_3d.html             # 3D network visualization
│   └── strategy_comparison.png     # Route strategy comparison
├── routing2_report.md              # Summary report (Markdown)
└── routing2_report.json            # Complete results (JSON)
```

## Routing Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| Balanced | Equal weights to all factors | General purpose |
| Cost Focused | Prioritizes low-cost terrain | Optimal routes |
| Slope Aware | Avoids steep terrain | Vehicles, heavy loads |
| Vegetation Aware | Prefers moderate NDVI | Natural paths |
| Shortest Path | Minimizes distance | Quick traversal |

## Terrain Factors

- **Cost**: Combined terrain difficulty (0-1)
- **Slope**: Terrain steepness in degrees
- **NDVI**: Vegetation index (-1 to 1)
- **Distance**: Physical distance between nodes
- **Priority**: Inverse of cost (higher = easier)

## Examples

### Custom Weight Strategy

```python
from route_optimizer import astar_multifactor

# Slope-aware routing for vehicles
weights = {"cost": 0.2, "slope": 0.6, "ndvi": 0.1, "distance": 0.1}
path, cost, stats = astar_multifactor(G, start, goal, weights)
```

### Priority Analysis

```python
from priority_analyzer import generate_priority_report

report = generate_priority_report(
    cost_path="cost.tif",
    slope_path="slope.tif"
)
print(f"Priority anchor: {report['priority_anchor']}")
print(f"High cost regions: {report['high_cost_regions']['num_regions']}")
```

## Requirements

- Python 3.8+
- numpy >= 1.24
- networkx >= 2.8
- rasterio >= 1.3
- matplotlib >= 3.5
- plotly >= 5.0 (for interactive 3D)
- scipy >= 1.9 (for local minima detection)

## License

MIT License - See project root for details.
