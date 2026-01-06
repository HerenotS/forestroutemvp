#!/usr/bin/env python
"""Create a graph visualization with rainbow-colored drone route in diagonal zig-zag pattern"""
import json
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
from matplotlib.patches import FancyArrowPatch
from pathlib import Path
import numpy as np

# Set non-interactive backend
import matplotlib
matplotlib.use('Agg')

def get_rainbow_colors(n_colors):
    """Generate rainbow color sequence: red, magenta, orange, yellow, green, blue, violet"""
    base_colors = [
        '#FF0000',  # Red
        '#FF00FF',  # Magenta
        '#FF8800',  # Orange
        '#FFFF00',  # Yellow
        '#00FF00',  # Green
        '#0000FF',  # Blue
        '#8800FF',  # Violet
    ]
    
    # Repeat the pattern to cover all nodes
    colors = []
    for i in range(n_colors):
        colors.append(base_colors[i % len(base_colors)])
    
    return colors

def create_diagonal_zigzag_order(coords):
    """
    Reorder coordinates to create a diagonal zig-zag pattern.
    Sorts by diagonal bands (x+y), then alternates direction within each band.
    """
    # Calculate diagonal value (x + y) for each point
    diagonal = coords[:, 0] + coords[:, 1]
    
    # Normalize to create bands (fewer bands = wider zig-zags covering more area)
    num_bands = 12  # Number of diagonal bands for zig-zag (reduced for wider coverage)
    diag_min, diag_max = diagonal.min(), diagonal.max()
    band_indices = ((diagonal - diag_min) / (diag_max - diag_min) * num_bands).astype(int)
    band_indices = np.clip(band_indices, 0, num_bands - 1)
    
    # Calculate perpendicular diagonal (x - y) for sorting within bands
    perpendicular = coords[:, 0] - coords[:, 1]
    
    # Build ordered indices
    ordered_indices = []
    for band in range(num_bands):
        band_mask = band_indices == band
        band_points = np.where(band_mask)[0]
        
        if len(band_points) == 0:
            continue
        
        # Sort by perpendicular diagonal
        perp_values = perpendicular[band_points]
        
        # Alternate direction for zig-zag effect
        if band % 2 == 0:
            sorted_band = band_points[np.argsort(perp_values)]
        else:
            sorted_band = band_points[np.argsort(-perp_values)]
        
        ordered_indices.extend(sorted_band)
    
    return np.array(ordered_indices)

def create_visualization():
    """Create visualization with rainbow-colored route showing drone path"""
    
    nodes_file = "demo_out_graph/nodes.geojson"
    edges_file = "demo_out_graph/edges.geojson"
    output_image = "demo_out_graph/graph_visualization.png"
    
    print("Loading graph data...")
    print(f"  Nodes: {nodes_file}")
    print(f"  Edges: {edges_file}")
    
    # Load GeoJSON files
    nodes_gdf = gpd.read_file(nodes_file)
    edges_gdf = gpd.read_file(edges_file)
    
    print(f"\nGraph statistics:")
    print(f"  Nodes: {len(nodes_gdf)}")
    print(f"  Edges: {len(edges_gdf)}")
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(24, 20), dpi=100)
    
    print("Drawing base edges (gray)...")
    # Draw all edges as light gray background
    edges_gdf.plot(
        ax=ax,
        color='#CCCCCC',
        linewidth=0.3,
        alpha=0.2,
        edgecolor='none'
    )
    
    print("Creating diagonal zig-zag pattern...")
    # Extract coordinates for each node
    coords = np.array([[geom.x, geom.y] for geom in nodes_gdf.geometry])
    
    # Reorder nodes to create diagonal zig-zag pattern
    ordered_indices = create_diagonal_zigzag_order(coords)
    ordered_coords = coords[ordered_indices]
    
    print("Generating rainbow color sequence for drone route...")
    # Generate colors for all nodes in zig-zag sequence
    node_colors = get_rainbow_colors(len(ordered_coords))
    
    print("Drawing route nodes with rainbow colors...")
    # Draw nodes with rainbow colors in zig-zag order
    for i, (coord, color) in enumerate(zip(ordered_coords, node_colors)):
        ax.plot(coord[0], coord[1], 'o', 
                color=color, 
                markersize=3, 
                alpha=0.8,
                markeredgewidth=0)
    
    print("Drawing route connections...")
    # Draw lines connecting sequential nodes in the zig-zag route
    segments = []
    for i in range(len(ordered_coords) - 1):
        segments.append([ordered_coords[i], ordered_coords[i + 1]])
    
    # Create line collection with rainbow colors
    lc = LineCollection(segments, 
                       colors=node_colors[:-1],  # Color for each segment
                       linewidths=1.5,
                       alpha=0.6)
    ax.add_collection(lc)
    
    print("Adding directional arrows...")
    # Add arrows to show flight direction (sample every N waypoints)
    arrow_interval = max(1, len(ordered_coords) // 100)  # Show ~100 arrows
    for i in range(0, len(ordered_coords) - 1, arrow_interval):
        start = ordered_coords[i]
        end = ordered_coords[i + 1]
        
        # Create arrow showing direction
        arrow = FancyArrowPatch(
            start, end,
            arrowstyle='->', 
            mutation_scale=15, 
            linewidth=2, 
            color=node_colors[i], 
            alpha=0.9,
            zorder=10
        )
        ax.add_patch(arrow)
    
    # Get bounds for title
    bounds = nodes_gdf.total_bounds
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    
    # Configure plot
    ax.set_title(
        f"Drone Route - Diagonal Zig-Zag Pattern with Arrows\n"
        f"{len(nodes_gdf):,} waypoints | Colors: Red→Magenta→Orange→Yellow→Green→Blue→Violet (repeating)\n"
        f"Arrows show flight direction | Center: ({center_lon:.2f}°, {center_lat:.2f}°)",
        fontsize=16, fontweight='bold', pad=20
    )
    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.grid(True, alpha=0.2, linestyle='--')
    
    # Add legend with color sequence and pattern info
    legend_elements = [
        mpatches.Patch(color='#FF0000', label='1st: Red'),
        mpatches.Patch(color='#FF00FF', label='2nd: Magenta'),
        mpatches.Patch(color='#FF8800', label='3rd: Orange'),
        mpatches.Patch(color='#FFFF00', label='4th: Yellow'),
        mpatches.Patch(color='#00FF00', label='5th: Green'),
        mpatches.Patch(color='#0000FF', label='6th: Blue'),
        mpatches.Patch(color='#8800FF', label='7th: Violet'),
        mpatches.Patch(color='white', label='(repeating cycle)'),
        mpatches.Patch(color='gray', label='→ = Direction')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=11, 
              title='Flight Sequence', framealpha=0.9)
    
    print("Saving image...")
    plt.tight_layout()
    plt.savefig(output_image, dpi=100, bbox_inches='tight', facecolor='white')
    
    file_size_mb = Path(output_image).stat().st_size / 1024 / 1024
    print(f"\n✅ Diagonal zig-zag route visualization saved!")
    print(f"   Location: {output_image}")
    print(f"   File size: {file_size_mb:.2f} MB")
    print(f"   Route sequence: {len(nodes_gdf):,} waypoints")
    print(f"   Pattern: Diagonal zig-zag with ~100 directional arrows")
    print(f"   Color pattern: Red→Magenta→Orange→Yellow→Green→Blue→Violet (repeating)")
    
    plt.close()

if __name__ == "__main__":
    try:
        create_visualization()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
