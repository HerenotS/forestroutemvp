"""
Visualization Module

Functions for visualizing routing results, terrain, and graphs.
"""
import logging
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

import geopandas as gpd
import networkx as nx

logger = logging.getLogger("frp.viz")

def visualize_route_2d(
    G: nx.Graph,
    path_nodes: List,
    output_path: str,
    background_raster: Optional[np.ndarray] = None,
    meta: Optional[dict] = None
):
    """Visualize route on 2D map."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not found, skipping visualization")
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot raster background if provided
    if background_raster is not None:
        ax.imshow(
            background_raster, 
            cmap='terrain', 
            alpha=0.4,
            extent=[
                meta['bounds'].left, meta['bounds'].right, 
                meta['bounds'].bottom, meta['bounds'].top
            ]
        )

    # Plot graph nodes (optional, can be crowded)
    # xs = [G.nodes[n]['x'] for n in G.nodes]
    # ys = [G.nodes[n]['y'] for n in G.nodes]
    # ax.scatter(xs, ys, s=1, c='gray', alpha=0.3)

    # Plot path
    if path_nodes:
        path_xs = [G.nodes[n]['x'] for n in path_nodes]
        path_ys = [G.nodes[n]['y'] for n in path_nodes]
        ax.plot(path_xs, path_ys, 'r-', linewidth=2, label='Route')
        
        # Start/End
        ax.scatter([path_xs[0]], [path_ys[0]], c='green', s=100, label='Start')
        ax.scatter([path_xs[-1]], [path_ys[-1]], c='blue', s=100, label='End')

    ax.legend()
    ax.set_title("Route Visualization")
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved 2D visualization to {output_path}")

def visualize_terrain_3d(
    cost_data: np.ndarray,
    output_path: str,
    meta: Optional[dict] = None
):
    """Visualize 3D terrain cost model."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib import cm
    except ImportError:
        logger.warning("matplotlib not found, skipping 3D visualization")
        return

    # Downsample for performance if needed
    stride = max(1, min(cost_data.shape) // 100)
    data = cost_data[::stride, ::stride]
    
    rows, cols = data.shape
    X = np.arange(0, cols, 1)
    Y = np.arange(0, rows, 1)
    X, Y = np.meshgrid(X, Y)
    Z = data

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    surf = ax.plot_surface(
        X, Y, Z, 
        cmap=cm.coolwarm,
        linewidth=0, 
        antialiased=False
    )
    
    fig.colorbar(surf, shrink=0.5, aspect=5)
    ax.set_title("3D Terrain Cost Model")
    
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved 3D visualization to {output_path}")
