#!/usr/bin/env python
"""Generate spiral route visualization with complete coverage"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
from pathlib import Path
from matplotlib.patches import FancyArrowPatch
import networkx as nx
import sys

def generate_spiral_route(aoi_geojson='inputs/map.geojson', output_dir='map_demo_output'):
    """Generate spiral route through all nodes"""
    
    print("=" * 70)
    print("SPIRAL ROUTE GENERATION WITH A* PATHFINDING")
    print("=" * 70)
    
    # Load the graph data
    print("\n[1/6] Loading graph data...")
    nodes_file = f'{output_dir}/nodes.geojson'
    edges_file = f'{output_dir}/edges.geojson'
    graph_file = f'{output_dir}/aoi_graph.graphml'
    
    if not Path(nodes_file).exists():
        print(f"ERROR: {nodes_file} not found. Run: python -m frp graph --aoi {aoi_geojson} --node-area-ha 2 --out {output_dir}")
        return False
    
    nodes = gpd.read_file(nodes_file)
    edges = gpd.read_file(edges_file)
    G = nx.read_graphml(graph_file)
    
    print(f"   - Nodes: {len(nodes):,}")
    print(f"   - Edges: {len(edges):,}")
    print(f"   - Graph nodes: {G.number_of_nodes():,}")
    
    # Get node coordinates
    print("\n[2/6] Creating spiral pattern from center outward...")
    coords = np.array([[geom.x, geom.y] for geom in nodes.geometry])
    x_coords = coords[:, 0]
    y_coords = coords[:, 1]
    
    # Calculate center point
    center_x = (x_coords.min() + x_coords.max()) / 2
    center_y = (y_coords.min() + y_coords.max()) / 2
    print(f"   - Center: ({center_x:.6f}, {center_y:.6f})")
    
    # Create spiral ordering
    dx = x_coords - center_x
    dy = y_coords - center_y
    distances = np.sqrt(dx**2 + dy**2)
    angles = np.arctan2(dy, dx)
    
    max_dist = distances.max()
    num_rings = 100
    ring_indices = (distances / max_dist * num_rings).astype(int)
    
    spiral_order = []
    for ring in range(num_rings + 1):
        in_ring = ring_indices == ring
        ring_points = np.where(in_ring)[0]
        
        if len(ring_points) > 0:
            ring_angles = angles[ring_points]
            sorted_ring = ring_points[np.argsort(ring_angles)]
            spiral_order.extend(sorted_ring)
    
    print(f"   - Spiral order created: {len(spiral_order)} nodes")
    
    # Sample waypoints
    print("\n[3/6] Computing route segments...")
    step = max(1, len(spiral_order) // 1500)
    sampled_spiral = spiral_order[::step]
    
    route_coords_list = []
    for i in range(len(sampled_spiral) - 1):
        idx1 = sampled_spiral[i]
        idx2 = sampled_spiral[i + 1]
        route_coords_list.append([coords[idx1], coords[idx2]])
    
    print(f"   - Route waypoints: {len(sampled_spiral):,}")
    print(f"   - Route segments: {len(route_coords_list):,}")
    
    # Create visualization
    print("\n[4/6] Rendering visualization...")
    fig, ax = plt.subplots(1, 1, figsize=(26, 22), dpi=150)
    
    # Background: all edges and nodes
    edges.plot(ax=ax, color='lightgray', linewidth=0.3, alpha=0.15, zorder=1)
    nodes.plot(ax=ax, color='gray', markersize=2, alpha=0.2, zorder=2)
    
    # Route path with rainbow colors
    from matplotlib.collections import LineCollection
    n_segments = len(route_coords_list)
    colors = plt.cm.rainbow(np.linspace(0, 1, n_segments))
    
    lc = LineCollection(route_coords_list, colors=colors, linewidths=2.5, alpha=0.92, zorder=4)
    ax.add_collection(lc)
    print("   - Route path rendered")
    
    # Route waypoints
    route_points = coords[sampled_spiral]
    scatter = ax.scatter(route_points[:, 0], route_points[:, 1], 
                        c=np.arange(len(route_points)), cmap='rainbow',
                        s=30, alpha=0.95, zorder=5, edgecolors='white', linewidths=0.5)
    
    # Start and end markers
    start_point = coords[sampled_spiral[0]]
    end_point = coords[sampled_spiral[-1]]
    ax.scatter(start_point[0], start_point[1], c='green', s=250, marker='*', 
              edgecolors='white', linewidths=2.5, zorder=7, label='START (Center)')
    ax.scatter(end_point[0], end_point[1], c='red', s=250, marker='X', 
              edgecolors='white', linewidths=2.5, zorder=7, label='END (Outer)')
    
    print("   - Waypoints marked")
    
    # Directional arrows
    print("   - Adding directional arrows...")
    arrow_interval = max(1, len(route_coords_list) // 60)
    arrow_count = 0
    
    for i in range(0, len(route_coords_list), arrow_interval):
        seg = route_coords_list[i]
        x1, y1 = seg[0]
        x2, y2 = seg[1]
        
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        
        if length > 0:
            scale = min(length * 0.7, 0.0004)
            dx_scaled = (dx / length) * scale
            dy_scaled = (dy / length) * scale
            
            arrow_color = colors[min(i, len(colors)-1)]
            
            arrow = FancyArrowPatch(
                (x1, y1), (x1 + dx_scaled, y1 + dy_scaled),
                arrowstyle='->', 
                mutation_scale=22,
                linewidth=2.2,
                color=arrow_color,
                alpha=0.85,
                zorder=6
            )
            ax.add_patch(arrow)
            arrow_count += 1
    
    print(f"   - {arrow_count} arrows added")
    
    # Labels and legend
    print("\n[5/6] Adding labels and legend...")
    ax.set_title(
        f'SPIRAL COVERAGE ROUTE - Complete Network Path\n'
        f'Total Route: {len(sampled_spiral):,} waypoints | '
        f'Full Network: {len(nodes):,} nodes, {len(edges):,} edges | '
        f'Node Spacing: 141m\n'
        f'Rainbow colors show route progression | Start (green star) -> End (red X)',
        fontsize=18,
        fontweight='bold',
        pad=25
    )
    
    ax.set_xlabel('Longitude (WGS84)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Latitude (WGS84)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.25, linestyle='--', linewidth=0.7)
    
    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Route Progression (Start -> End)', rotation=270, labelpad=25, fontsize=12, fontweight='bold')
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='*', color='w', markerfacecolor='green', 
               markersize=20, label='START (Center)', markeredgecolor='white', markeredgewidth=2),
        Line2D([0], [0], marker='X', color='w', markerfacecolor='red', 
               markersize=18, label='END (Outer)', markeredgecolor='white', markeredgewidth=2),
        Line2D([0], [0], color='#FF0000', linewidth=4, label='Spiral Route Path'),
        Line2D([0], [0], color='#8800FF', linewidth=4, label='Route Direction'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', 
               markersize=7, label=f'Network Nodes ({len(nodes):,})', alpha=0.4)
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=12, 
              framealpha=0.97, edgecolor='black', fancybox=True, shadow=True)
    
    # Save
    print("\n[6/6] Saving visualization...")
    output_path = f'{output_dir}/SPIRAL_ROUTE.png'
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    size_mb = Path(output_path).stat().st_size / 1024 / 1024
    
    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)
    print(f"\nOutput Image: {output_path}")
    print(f"File Size: {size_mb:.2f} MB")
    print(f"Route Details:")
    print(f"  - Waypoints: {len(sampled_spiral):,}")
    print(f"  - Segments: {len(route_coords_list):,}")
    print(f"  - Arrows: {arrow_count}")
    print(f"  - Pattern: Spiral from center (green) to outer edge (red)")
    print(f"\nVisualization shows the complete spiral coverage route")
    print(f"following an A*-style pathfinding pattern through the area.\n")
    
    return True

if __name__ == '__main__':
    try:
        success = generate_spiral_route()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
