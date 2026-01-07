"""
Routing 2.0 - Advanced 3D Visualization and Multi-dimensional Graph Routing

This package provides:
- 3D cost map visualization with terrain-based elevation
- Multi-dimensional NetworkX graphs with terrain factor attributes
- Priority-based route optimization using A*
- Interactive visualizations using Plotly

Modules:
- cost_3d_model: 3D visualization of cost maps
- multidim_graph: Multi-dimensional graph builder with terrain attributes
- priority_analyzer: Priority anchor detection and analysis
- route_optimizer: A* pathfinding with multi-factor weights
- graph_visualizer: 2D/3D graph visualization
- pipeline: Main orchestration pipeline
- report_generator: Summary report generation
"""

__version__ = "2.0.0"
__all__ = [
    "cost_3d_model",
    "multidim_graph", 
    "priority_analyzer",
    "route_optimizer",
    "graph_visualizer",
    "pipeline",
    "report_generator"
]
