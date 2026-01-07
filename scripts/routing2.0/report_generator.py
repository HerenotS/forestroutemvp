"""
Report Generator Module

Generates comprehensive summary reports explaining:
- How terrain factors influence the 3D model and graph
- Priority analysis and distribution
- Route optimization results
- Factor correlations and weights
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("routing2.0.report_generator")


def format_number(value: float, precision: int = 4) -> str:
    """Format number for report display."""
    if isinstance(value, float):
        return f"{value:.{precision}f}"
    return str(value)


def generate_factor_explanation() -> str:
    """Generate explanation of terrain factors and their influence."""
    return """
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
"""


def generate_3d_model_explanation() -> str:
    """Generate explanation of the 3D model."""
    return """
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
"""


def generate_graph_explanation() -> str:
    """Generate explanation of the multi-dimensional graph."""
    return """
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
"""


def generate_route_analysis_text(route_result: Dict[str, Any]) -> str:
    """Generate analysis text for route optimization results."""
    if "error" in route_result:
        return f"Route optimization failed: {route_result['error']}"
    
    stats = route_result.get("statistics", {})
    
    return f"""
## Route Optimization Results

### Path Summary
- **Path Length**: {route_result.get('path_length', len(route_result.get('path', [])))} nodes
- **Total Weighted Cost**: {format_number(route_result.get('total_cost', 0))}
- **Total Distance**: {format_number(stats.get('total_distance', 0))} units

### Terrain Statistics Along Path
- **Average Cost**: {format_number(stats.get('average_cost', 0))}
- **Average Slope**: {format_number(stats.get('average_slope', 0))}°
- **Nodes Explored**: {stats.get('nodes_explored', 0)}

### Factor Weights Used
"""


def generate_strategy_comparison_text(comparison: Dict[str, Any]) -> str:
    """Generate comparison text for different routing strategies."""
    if "strategies" not in comparison:
        return "No strategy comparison available."
    
    text = "\n## Routing Strategy Comparison\n\n"
    text += "| Strategy | Path Length | Total Cost | Distance | Avg Slope |\n"
    text += "|----------|-------------|------------|----------|----------|\n"
    
    for name, data in comparison["strategies"].items():
        text += f"| {name} | {data['path_length']} | {format_number(data['total_cost'])} | "
        text += f"{format_number(data['total_distance'])} | {format_number(data['average_slope'])}° |\n"
    
    text += """
### Strategy Descriptions
- **Balanced**: Equal weight to all factors (cost, slope, NDVI, distance)
- **Cost Focused**: Prioritizes low-cost terrain over other factors
- **Slope Aware**: Avoids steep terrain, suitable for vehicles/heavy loads
- **Vegetation Aware**: Prefers moderate vegetation areas
- **Shortest Path**: Minimizes distance regardless of terrain difficulty
"""
    
    return text


def generate_summary_report(
    model_results: Dict[str, Any] = None,
    graph_meta: Dict[str, Any] = None,
    priority_report: Dict[str, Any] = None,
    route_result: Dict[str, Any] = None,
    strategy_comparison: Dict[str, Any] = None,
    output_paths: Dict[str, str] = None
) -> str:
    """Generate complete summary report.
    
    Args:
        model_results: Results from 3D model generation
        graph_meta: Metadata from graph building
        priority_report: Results from priority analysis
        route_result: Results from route optimization
        strategy_comparison: Results from strategy comparison
        output_paths: Dictionary of generated output file paths
        
    Returns:
        Markdown-formatted report string
    """
    report = f"""# Routing 2.0 - 3D Visualization and Multi-dimensional Graph Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
"""
    
    # Factor explanation
    report += generate_factor_explanation()
    report += "\n---\n"
    
    # 3D Model
    report += generate_3d_model_explanation()
    
    if model_results:
        anchor = model_results.get("priority_anchor", {})
        stats = model_results.get("cost_stats", {})
        report += f"""
### Generated Model Statistics
- **Priority Anchor Location**: Row {anchor.get('row', 'N/A')}, Col {anchor.get('col', 'N/A')}
- **Priority Anchor Cost**: {format_number(anchor.get('cost_value', 0))}
- **Cost Range**: {format_number(stats.get('min', 0))} to {format_number(stats.get('max', 0))}
- **Raster Shape**: {stats.get('shape', 'N/A')}
"""
    
    report += "\n---\n"
    
    # Graph explanation
    report += generate_graph_explanation()
    
    if graph_meta:
        report += f"""
### Generated Graph Statistics
- **Total Nodes**: {graph_meta.get('nodes', 'N/A')}
- **Total Edges**: {graph_meta.get('edges', 'N/A')}
- **Node Spacing**: {graph_meta.get('node_spacing', 'N/A')} pixels
- **Connectivity**: {graph_meta.get('connectivity', 'N/A')}-way
- **Has Slope Data**: {graph_meta.get('has_slope', False)}
- **Has NDVI Data**: {graph_meta.get('has_ndvi', False)}
"""
    
    report += "\n---\n"
    
    # Priority Analysis
    if priority_report:
        report += """
## Priority Analysis

"""
        anchor = priority_report.get("priority_anchor", {})
        if anchor.get("found"):
            report += f"""### Priority Anchor (Global Minimum Cost)
- **Location**: Row {anchor.get('row')}, Col {anchor.get('col')}
- **Cost Value**: {format_number(anchor.get('cost', 0))}
- **Description**: {anchor.get('description', 'Optimal starting point')}

"""
        
        dist = priority_report.get("distribution", {})
        if dist.get("valid"):
            cost_stats = dist.get("cost_statistics", {})
            priority_stats = dist.get("priority_statistics", {})
            report += f"""### Distribution Statistics
| Metric | Cost | Priority |
|--------|------|----------|
| Min | {format_number(cost_stats.get('min', 0))} | {format_number(priority_stats.get('min', 0))} |
| Max | {format_number(cost_stats.get('max', 0))} | {format_number(priority_stats.get('max', 0))} |
| Mean | {format_number(cost_stats.get('mean', 0))} | {format_number(priority_stats.get('mean', 0))} |
| Std Dev | {format_number(cost_stats.get('std', 0))} | {format_number(priority_stats.get('std', 0))} |

"""
        
        high_cost = priority_report.get("high_cost_regions", {})
        if high_cost.get("found"):
            report += f"""### High Cost Regions (Obstacles)
- **Threshold**: {format_number(high_cost.get('threshold', 0))} (P{high_cost.get('threshold_percentile', 90)})
- **Number of Regions**: {high_cost.get('num_regions', 0)}
- **Total High-Cost Pixels**: {high_cost.get('total_high_cost_pixels', 0)} ({format_number(high_cost.get('percentage_of_total', 0), 2)}%)

"""
        
        # Factor correlations
        if "slope_correlation" in priority_report:
            report += f"### Factor Correlations with Cost\n"
            report += f"- **Slope-Cost Correlation**: {format_number(priority_report.get('slope_correlation', 0))}\n"
        if "ndvi_correlation" in priority_report:
            report += f"- **NDVI-Cost Correlation**: {format_number(priority_report.get('ndvi_correlation', 0))}\n"
    
    report += "\n---\n"
    
    # Route optimization
    if route_result:
        report += generate_route_analysis_text(route_result)
        weights = route_result.get("statistics", {}).get("weights_used", {})
        for factor, weight in weights.items():
            report += f"- **{factor.capitalize()}**: {format_number(weight, 2)}\n"
    
    # Strategy comparison
    if strategy_comparison:
        report += generate_strategy_comparison_text(strategy_comparison)
    
    report += "\n---\n"
    
    # Output files
    if output_paths:
        report += "\n## Generated Output Files\n\n"
        for name, path in output_paths.items():
            report += f"- **{name}**: `{path}`\n"
    
    report += """
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
"""
    
    return report


def save_report(
    report: str,
    output_path: str,
    also_save_json: bool = True,
    report_data: Dict[str, Any] = None
) -> Dict[str, str]:
    """Save report to files.
    
    Args:
        report: Markdown report string
        output_path: Path for markdown file
        also_save_json: Whether to also save JSON version
        report_data: Raw data to save as JSON
        
    Returns:
        Dictionary of saved file paths
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    paths = {}
    
    # Save markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    paths["markdown"] = str(output_path)
    logger.info(f"Saved markdown report: {output_path}")
    
    # Save JSON
    if also_save_json and report_data:
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        paths["json"] = str(json_path)
        logger.info(f"Saved JSON report: {json_path}")
    
    return paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Example usage
    report = generate_summary_report()
    print(report)
