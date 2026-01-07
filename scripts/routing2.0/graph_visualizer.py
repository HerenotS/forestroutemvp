"""
Graph Visualizer Module

Creates 2D and 3D visualizations of the multi-dimensional graph with:
- Node colors/sizes representing priorities
- Edge colors representing weights
- Route highlighting
- Interactive 3D network plots
"""

import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List

import numpy as np
import networkx as nx

logger = logging.getLogger("routing2.0.graph_visualizer")


def get_node_colors_by_priority(G: nx.Graph, cmap_name: str = "RdYlGn") -> List[Tuple[float, ...]]:
    """Get colors for nodes based on priority (green=high, red=low)."""
    import matplotlib.pyplot as plt
    
    cmap = plt.get_cmap(cmap_name)
    
    # Get priority values
    priorities = []
    for n in G.nodes():
        priorities.append(G.nodes[n].get("priority", 0.5))
    
    # Normalize
    p_min = min(priorities) if priorities else 0
    p_max = max(priorities) if priorities else 1
    
    colors = []
    for p in priorities:
        if p_max > p_min:
            norm = (p - p_min) / (p_max - p_min)
        else:
            norm = 0.5
        colors.append(cmap(norm))
    
    return colors


def get_node_sizes_by_priority(G: nx.Graph, min_size: float = 10, max_size: float = 100) -> List[float]:
    """Get node sizes proportional to priority."""
    priorities = []
    for n in G.nodes():
        priorities.append(G.nodes[n].get("priority", 0.5))
    
    p_min = min(priorities) if priorities else 0
    p_max = max(priorities) if priorities else 1
    
    sizes = []
    for p in priorities:
        if p_max > p_min:
            norm = (p - p_min) / (p_max - p_min)
        else:
            norm = 0.5
        sizes.append(min_size + norm * (max_size - min_size))
    
    return sizes


def visualize_2d_priority_map(
    G: nx.Graph,
    output_path: str,
    title: str = "Multi-dimensional Graph - Priority Map",
    show_edges: bool = True,
    route_path: Optional[List[int]] = None
) -> str:
    """Create 2D visualization with priority coloring.
    
    Args:
        G: NetworkX graph with priority attributes
        output_path: Path to save PNG
        title: Plot title
        show_edges: Whether to draw edges
        route_path: Optional list of node IDs to highlight as route
        
    Returns:
        Path to saved image
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable
    
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # Get positions from node attributes
    pos = {}
    for n, data in G.nodes(data=True):
        x = data.get("x", data.get("grid_col", n))
        y = data.get("y", data.get("grid_row", n))
        pos[n] = (x, y)
    
    # Get priority values for coloring
    priorities = [G.nodes[n].get("priority", 0.5) for n in G.nodes()]
    
    # Draw edges if requested
    if show_edges:
        # Use LineCollection for performance (nx.draw_networkx_edges is slow for large graphs)
        from matplotlib.collections import LineCollection
        
        lines = []
        colors = []
        weights = []
        
        for u, v, data in G.edges(data=True):
            if u in pos and v in pos:
                lines.append([pos[u], pos[v]])
                w = data.get("weight", 1.0)
                weights.append(w)
        
        if lines:
            # Normalize weights for coloring
            w_min, w_max = min(weights), max(weights) if weights else (0, 1)
            
            # Create collection
            lc = LineCollection(lines, linewidths=0.5, alpha=0.3, cmap=plt.cm.Greys)
            lc.set_array(np.array(weights))
            ax.add_collection(lc)

    # Draw nodes
    # If too many nodes, reduce size
    node_size = 20 if G.number_of_nodes() < 1000 else 5
    
    node_colors = priorities
    nodes = nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        cmap=plt.cm.RdYlGn,
        node_size=get_node_sizes_by_priority(G, min_size=5, max_size=50),
        alpha=0.8
    )

    # Add colorbar
    if nodes is not None:
        sm = ScalarMappable(cmap=plt.cm.RdYlGn, norm=Normalize(vmin=min(priorities), vmax=max(priorities)))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8, label="Priority (Green=High, Red=Low)")
    
    # Highlight route if provided
    if route_path and len(route_path) > 1:
        route_x = [pos[n][0] for n in route_path if n in pos]
        route_y = [pos[n][1] for n in route_path if n in pos]
        ax.plot(route_x, route_y, 'b-', linewidth=3, alpha=0.8, label='Optimized Route')
        ax.scatter([route_x[0]], [route_y[0]], c='cyan', s=200, marker='D', zorder=5, label='Start')
        ax.scatter([route_x[-1]], [route_y[-1]], c='magenta', s=200, marker='*', zorder=5, label='Goal')
        ax.legend()
    
    ax.set_title(f"{title}\n({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    ax.set_aspect('equal', adjustable='datalim')
    
    plt.tight_layout()
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"Saved 2D visualization: {output_path}")
    return str(output_path)


def visualize_3d_network(
    G: nx.Graph,
    output_path: str,
    title: str = "3D Network Graph - Priority Visualization",
    z_attribute: str = "cost",
    route_path: Optional[List[int]] = None
) -> str:
    """Create 3D interactive network visualization using Plotly.
    
    Args:
        G: NetworkX graph
        output_path: Path to save HTML
        title: Plot title
        z_attribute: Node attribute to use for Z axis ('cost', 'priority', 'slope')
        route_path: Optional route to highlight
        
    Returns:
        Path to saved HTML
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise ImportError("Plotly is required. Install with: pip install plotly")
    
    # Get node positions and attributes
    node_x, node_y, node_z = [], [], []
    node_colors = []
    node_text = []
    
    for n, data in G.nodes(data=True):
        x = data.get("x", data.get("grid_col", 0))
        y = data.get("y", data.get("grid_row", 0))
        z = data.get(z_attribute, 0)
        priority = data.get("priority", 0.5)
        
        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        node_colors.append(priority)
        node_text.append(
            f"Node {n}<br>"
            f"Cost: {data.get('cost', 0):.4f}<br>"
            f"Priority: {priority:.4f}<br>"
            f"Slope: {data.get('slope', 0):.2f}<br>"
            f"NDVI: {data.get('ndvi', 0):.3f}"
        )
    
    # Create node trace
    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers',
        marker=dict(
            size=5,
            color=node_colors,
            colorscale='RdYlGn',
            colorbar=dict(title="Priority"),
            opacity=0.8
        ),
        text=node_text,
        hoverinfo='text',
        name='Nodes'
    )
    
    # Create edge traces (sample for performance)
    edge_traces = []
    edges_list = list(G.edges())
    sample_rate = max(1, len(edges_list) // 5000)
    
    edge_x, edge_y, edge_z = [], [], []
    for i, (u, v) in enumerate(edges_list):
        if i % sample_rate != 0:
            continue
        
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        
        x0 = u_data.get("x", u_data.get("grid_col", 0))
        y0 = u_data.get("y", u_data.get("grid_row", 0))
        z0 = u_data.get(z_attribute, 0)
        
        x1 = v_data.get("x", v_data.get("grid_col", 0))
        y1 = v_data.get("y", v_data.get("grid_row", 0))
        z1 = v_data.get(z_attribute, 0)
        
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])
    
    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(color='rgba(150,150,150,0.3)', width=1),
        hoverinfo='none',
        name='Edges'
    )
    
    traces = [edge_trace, node_trace]
    
    # Add route if provided
    if route_path and len(route_path) > 1:
        route_x, route_y, route_z = [], [], []
        for n in route_path:
            if n in G.nodes:
                data = G.nodes[n]
                route_x.append(data.get("x", data.get("grid_col", 0)))
                route_y.append(data.get("y", data.get("grid_row", 0)))
                route_z.append(data.get(z_attribute, 0))
        
        route_trace = go.Scatter3d(
            x=route_x, y=route_y, z=route_z,
            mode='lines+markers',
            line=dict(color='blue', width=5),
            marker=dict(size=3, color='blue'),
            name='Optimized Route'
        )
        traces.append(route_trace)
        
        # Start and end markers
        traces.append(go.Scatter3d(
            x=[route_x[0]], y=[route_y[0]], z=[route_z[0]],
            mode='markers',
            marker=dict(size=15, color='cyan', symbol='diamond'),
            name='Start'
        ))
        traces.append(go.Scatter3d(
            x=[route_x[-1]], y=[route_y[-1]], z=[route_z[-1]],
            mode='markers',
            marker=dict(size=15, color='magenta', symbol='cross'),
            name='Goal'
        ))
    
    # Create figure
    fig = go.Figure(data=traces)
    
    fig.update_layout(
        title=dict(text=title, x=0.5),
        width=1200,
        height=900,
        scene=dict(
            xaxis_title="X Coordinate",
            yaxis_title="Y Coordinate",
            zaxis_title=f"{z_attribute.capitalize()} Value",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
        ),
        showlegend=True,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs=True)
    
    logger.info(f"Saved 3D network visualization: {output_path}")
    return str(output_path)


def visualize_route_comparison(
    G: nx.Graph,
    routes: Dict[str, List[int]],
    output_path: str,
    title: str = "Route Strategy Comparison"
) -> str:
    """Visualize multiple routes for comparison.
    
    Args:
        G: NetworkX graph
        routes: Dictionary of {route_name: [node_ids]}
        output_path: Path to save image
        title: Plot title
        
    Returns:
        Path to saved image
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # Get positions
    pos = {}
    for n, data in G.nodes(data=True):
        x = data.get("x", data.get("grid_col", n))
        y = data.get("y", data.get("grid_row", n))
        pos[n] = (x, y)
    
    # Draw nodes with priority coloring
    priorities = [G.nodes[n].get("priority", 0.5) for n in G.nodes()]
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=priorities,
        cmap=plt.cm.RdYlGn,
        node_size=20,
        alpha=0.5
    )
    
    # Draw each route with different color
    colors = plt.cm.tab10.colors
    for i, (name, path) in enumerate(routes.items()):
        if not path:
            continue
        color = colors[i % len(colors)]
        route_x = [pos[n][0] for n in path if n in pos]
        route_y = [pos[n][1] for n in path if n in pos]
        ax.plot(route_x, route_y, '-', color=color, linewidth=2.5, alpha=0.8, label=name)
    
    # Mark start and end
    if routes:
        first_route = list(routes.values())[0]
        if first_route and len(first_route) > 0:
            start = first_route[0]
            end = first_route[-1]
            if start in pos:
                ax.scatter([pos[start][0]], [pos[start][1]], c='cyan', s=200, marker='D', zorder=5, label='Start')
            if end in pos:
                ax.scatter([pos[end][0]], [pos[end][1]], c='magenta', s=200, marker='*', zorder=5, label='Goal')
    
    ax.set_title(title)
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    ax.legend(loc='upper right')
    ax.set_aspect('equal', adjustable='datalim')
    
    plt.tight_layout()
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"Saved route comparison: {output_path}")
    return str(output_path)


def create_priority_heatmap(
    G: nx.Graph,
    output_path: str,
    grid_shape: Tuple[int, int] = None
) -> str:
    """Create a 2D heatmap of priorities from graph nodes.
    
    Args:
        G: NetworkX graph
        output_path: Path to save image
        grid_shape: Optional (rows, cols) for the grid
        
    Returns:
        Path to saved image
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    # Determine grid size
    if grid_shape is None:
        max_row = max(G.nodes[n].get("grid_idx_row", 0) for n in G.nodes()) + 1
        max_col = max(G.nodes[n].get("grid_idx_col", 0) for n in G.nodes()) + 1
        grid_shape = (max_row, max_col)
    
    # Create priority grid
    priority_grid = np.full(grid_shape, np.nan)
    for n, data in G.nodes(data=True):
        row = data.get("grid_idx_row", 0)
        col = data.get("grid_idx_col", 0)
        if 0 <= row < grid_shape[0] and 0 <= col < grid_shape[1]:
            priority_grid[row, col] = data.get("priority", 0.5)
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    im = ax.imshow(priority_grid, cmap='RdYlGn', aspect='equal', origin='lower')
    plt.colorbar(im, ax=ax, label='Priority (Green=High, Red=Low)')
    
    ax.set_title("Priority Heatmap")
    ax.set_xlabel("Column Index")
    ax.set_ylabel("Row Index")
    
    plt.tight_layout()
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"Saved priority heatmap: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    import sys
    import json
    from multidim_graph import build_multidim_graph
    from route_optimizer import optimize_route_demo, compare_weight_strategies
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Default test paths
    cost_path = "out_demo_plan/rasters/cost.tif"
    slope_path = "out_demo_plan/rasters/slope.tif"
    ndvi_path = "out_demo_plan/rasters/ndvi.tif"
    output_dir = "scripts/routing2.0/output/visualizations"
    
    # Build graph
    logger.info("Building multi-dimensional graph...")
    G, meta = build_multidim_graph(
        cost_path=cost_path,
        slope_path=slope_path,
        ndvi_path=ndvi_path,
        node_spacing=10,
        connectivity=8
    )
    
    # Run optimization
    logger.info("Running route optimization...")
    result = optimize_route_demo(G)
    route_path = result.get("path", [])
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Create visualizations
    logger.info("Creating 2D priority map...")
    visualize_2d_priority_map(G, f"{output_dir}/priority_map_2d.png", route_path=route_path)
    
    logger.info("Creating priority heatmap...")
    create_priority_heatmap(G, f"{output_dir}/priority_heatmap.png")
    
    logger.info("Creating 3D network visualization...")
    try:
        visualize_3d_network(G, f"{output_dir}/network_3d.html", route_path=route_path)
    except ImportError as e:
        logger.warning(f"Could not create 3D visualization: {e}")
    
    print("\n=== Visualizations Created ===")
    print(f"Output directory: {output_dir}")
