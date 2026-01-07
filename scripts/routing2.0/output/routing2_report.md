# Routing 2.0 - 3D Visualization and Multi-dimensional Graph Report

**Generated**: 2026-01-07 13:02:49

---

## Terrain Factor Influence

### Cost
The primary routing metric combining multiple terrain characteristics. Lower cost indicates 
easier traversal. In the 3D model, cost values are represented as elevation - high cost areas 
appear as peaks (obstacles), while low cost areas appear as valleys (optimal paths).

### Slope
Terrain steepness measured in degrees. Higher slopes increase difficulty and cost:
- 0-10°: Easy terrain (low penalty)
- 10-25°: Moderate difficulty
- 25-45°: Difficult terrain (high penalty)
- >45°: Very difficult/impassable

### NDVI (Normalized Difference Vegetation Index)
Vegetation density indicator ranging from -1 to 1:
- -1 to 0: Water, bare soil, urban areas (higher traversal cost)
- 0 to 0.3: Sparse vegetation
- 0.3 to 0.6: Moderate vegetation (optimal for many routes)
- 0.6 to 1.0: Dense vegetation (may indicate difficult terrain)

### Distance
Physical distance between nodes in coordinate units. Combined with other factors to compute 
total route cost. Diagonal movements have a √2 penalty.

### Priority
Inverse of cost - represents route desirability:
- Priority = 1 - (cost - min_cost) / (max_cost - min_cost)
- Higher priority = easier traversal = lower cost
- Visualized as green (high priority) to red (low priority) gradient

---

## 3D Cost Terrain Model

The 3D visualization transforms the cost raster into a terrain-like surface where:

1. **Elevation = Cost Value**: Higher elevations represent higher cost (more difficult terrain)
2. **Colors (Cost View)**:
   - Green valleys: Low cost, easy traversal, high priority
   - Yellow/Orange slopes: Moderate difficulty
   - Red peaks: High cost, obstacles, low priority

3. **Priority Anchor**: The global minimum cost point is marked with a cyan diamond. This 
   represents the "lowest energy" point - the optimal starting location for priority-based routing.

4. **Inverted Priority View**: A second visualization shows the terrain inverted, where:
   - High priority areas become peaks
   - Low priority areas become valleys
   - Useful for visualizing optimal routing paths as ridgelines

### Interpretation
- Route planning should follow valleys in the cost view (or ridges in priority view)
- Peaks represent obstacles to route around
- Gradient direction indicates optimal movement direction toward lower cost

### Generated Model Statistics
- **Priority Anchor Location**: Row 10, Col 1
- **Priority Anchor Cost**: 0.0000
- **Cost Range**: 0.0000 to 0.5000
- **Raster Shape**: (228, 130)

---

## Multi-Dimensional NetworkX Graph

The graph encodes terrain information as a network structure:

### Node Attributes
Each node (grid point) contains:
- **Position**: Grid indices (row, col) and geographic coordinates (x, y)
- **Cost**: Combined terrain difficulty value
- **Slope**: Local terrain steepness
- **NDVI**: Vegetation index at that location
- **Priority**: Computed priority score (0-1, higher = better)

### Edge Attributes
Each edge (connection between nodes) contains:
- **Distance**: Physical distance between nodes
- **Cost**: Average cost of connected nodes
- **Slope**: Average slope along the edge
- **NDVI**: Average vegetation index
- **Weight**: Combined routing weight
- **Is_diagonal**: Flag for diagonal connections (√2 distance penalty)

### Graph Structure
- **Connectivity**: 8-way (including diagonals) or 4-way grid
- **Node Spacing**: Configurable grid resolution (default: 10 pixels)
- **Edge Weights**: Computed as cost × distance × diagonal_factor

### Usage for Routing
The graph supports multi-factor A* pathfinding where edge weights can be 
customized based on different factor priorities (cost-focused, slope-aware, etc.)

### Generated Graph Statistics
- **Total Nodes**: 1195
- **Total Edges**: 4565
- **Node Spacing**: 10 pixels
- **Connectivity**: 8-way
- **Has Slope Data**: True
- **Has NDVI Data**: True

---

## Priority Analysis

### Priority Anchor (Global Minimum Cost)
- **Location**: Row 10, Col 1
- **Cost Value**: 0.0000
- **Description**: Global minimum cost point - optimal priority anchor

### Distribution Statistics
| Metric | Cost | Priority |
|--------|------|----------|
| Min | 0.0000 | 0.0000 |
| Max | 0.5000 | 1.0000 |
| Mean | 0.4254 | 0.1493 |
| Std Dev | 0.1396 | 0.2792 |

### High Cost Regions (Obstacles)
- **Threshold**: 0.5000 (P90)
- **Number of Regions**: 1
- **Total High-Cost Pixels**: 90583 (76.40%)

### Factor Correlations with Cost
- **Slope-Cost Correlation**: 0.0000
- **NDVI-Cost Correlation**: -1.0000

---

## Route Optimization Results

### Path Summary
- **Path Length**: 44 nodes
- **Total Weighted Cost**: 20.6389
- **Total Distance**: 4879.8990 units

### Terrain Statistics Along Path
- **Average Cost**: 0.3993
- **Average Slope**: 0.0000°
- **Nodes Explored**: 162

### Factor Weights Used
- **Cost**: 0.40
- **Slope**: 0.20
- **Ndvi**: 0.20
- **Distance**: 0.20

## Routing Strategy Comparison

| Strategy | Path Length | Total Cost | Distance | Avg Slope |
|----------|-------------|------------|----------|----------|
| balanced | 44 | 21.5064 | 4879.8990 | 0.0000° |
| cost_focused | 44 | 18.9039 | 4879.8990 | 0.0000° |
| slope_aware | 44 | 10.3194 | 4879.8990 | 0.0000° |
| vegetation_aware | 44 | 20.3482 | 4879.8990 | 0.0000° |
| shortest_path | 44 | 37.8819 | 4879.8990 | 0.0000° |

### Strategy Descriptions
- **Balanced**: Equal weight to all factors (cost, slope, NDVI, distance)
- **Cost Focused**: Prioritizes low-cost terrain over other factors
- **Slope Aware**: Avoids steep terrain, suitable for vehicles/heavy loads
- **Vegetation Aware**: Prefers moderate vegetation areas
- **Shortest Path**: Minimizes distance regardless of terrain difficulty

---

## Generated Output Files

- **3d_model**: `C:\Users\rasan\EDIFY\forestroutemvp\scripts\routing2.0\output\3d_model\cost_terrain_3d.html`
- **graph_graphml**: `C:\Users\rasan\EDIFY\forestroutemvp\scripts\routing2.0\output\graph\multidim_graph.graphml`
- **graph_json**: `C:\Users\rasan\EDIFY\forestroutemvp\scripts\routing2.0\output\graph\multidim_graph.json`
- **priority_map_2d**: `C:\Users\rasan\EDIFY\forestroutemvp\scripts\routing2.0\output\visualizations\priority_map_2d.png`
- **priority_heatmap**: `C:\Users\rasan\EDIFY\forestroutemvp\scripts\routing2.0\output\visualizations\priority_heatmap.png`
- **network_3d**: `C:\Users\rasan\EDIFY\forestroutemvp\scripts\routing2.0\output\visualizations\network_3d.html`
- **strategy_comparison**: `C:\Users\rasan\EDIFY\forestroutemvp\scripts\routing2.0\output\visualizations\strategy_comparison.png`

---

## Recommendations

### For Route Planning
1. Use the **priority anchor** as the preferred starting point for optimal routes
2. Choose weight strategy based on use case:
   - Heavy vehicles: Use **slope-aware** strategy
   - Quick traversal: Use **cost-focused** strategy
   - Natural paths: Use **vegetation-aware** strategy
3. Avoid red peaks in 3D visualization (high cost obstacles)

### For Visualization
1. Use interactive 3D HTML for exploration and presentation
2. Use 2D priority map for quick overview and route validation
3. Use strategy comparison plot to justify routing decisions

### For Graph Analysis
1. High-priority nodes (green) are optimal waypoint candidates
2. Edge weights encode multi-factor difficulty
3. Graph can be exported to GraphML for external analysis
