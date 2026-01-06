#!/usr/bin/env python
"""Generate a visual image of the graph from GraphML file"""
import networkx as nx
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import sys
from pathlib import Path

def visualize_graph(graphml_path, output_image):
    """Load GraphML and create a visualization image"""
    
    print(f"Loading graph from: {graphml_path}")
    
    # Read the graph
    G = nx.read_graphml(graphml_path)
    
    print(f"Graph statistics:")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    
    # Create figure with large size for high-resolution output
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=150)
    
    print("Computing layout (this may take a moment)...")
    # Use circular layout (doesn't require scipy)
    # For large graphs, use a simplified circular arrangement
    if G.number_of_nodes() > 5000:
        print(f"  Using shell layout for large graph ({G.number_of_nodes()} nodes)")
        pos = nx.shell_layout(G)
    else:
        pos = nx.circular_layout(G)
    
    print("Drawing nodes and edges...")
    # Draw edges first (so they appear behind nodes)
    nx.draw_networkx_edges(
        G, pos,
        ax=ax,
        width=0.3,
        alpha=0.2,
        edge_color='gray'
    )
    
    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos,
        ax=ax,
        node_size=10,
        node_color='#1f77b4',
        alpha=0.8
    )
    
    # Configure the plot
    ax.set_title(f"Forest Route Network Graph\n({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)", 
                 fontsize=16, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    
    # Save the image
    print(f"Saving image to: {output_image}")
    plt.savefig(output_image, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Image saved successfully!")
    print(f"   File size: {Path(output_image).stat().st_size / 1024 / 1024:.2f} MB")
    
    plt.close()

if __name__ == "__main__":
    graphml_path = "demo_out_graph/aoi_graph.graphml"
    output_image = "demo_out_graph/graph_visualization.png"
    
    if not Path(graphml_path).exists():
        print(f"Error: {graphml_path} not found")
        sys.exit(1)
    
    visualize_graph(graphml_path, output_image)
