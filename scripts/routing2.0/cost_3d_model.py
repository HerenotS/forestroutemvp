"""
3D Cost Map Model Generator

Transforms cost map raster data into interactive 3D visualizations where:
- Elevation represents cost values (higher cost = higher elevation/peaks)
- Lowest cost points are valleys (priority anchors)
- Red/high-cost areas are emphasized as prominent peaks
"""

import logging
import json
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

import numpy as np
import rasterio
from rasterio.transform import rowcol

logger = logging.getLogger("routing2.0.cost_3d_model")


def load_raster(path: str) -> Tuple[np.ndarray, dict]:
    """Load a raster file and return (data, metadata)."""
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        meta = src.meta.copy()
        meta["transform"] = src.transform
        meta["crs"] = src.crs
        meta["bounds"] = src.bounds
    return data, meta


def find_min_cost_point(cost: np.ndarray) -> Tuple[Tuple[int, int], float]:
    """Find the minimum cost point (priority anchor) in the cost grid.
    
    Returns:
        ((row, col), min_value)
    """
    # Mask invalid values
    valid_cost = np.where(np.isnan(cost), np.inf, cost)
    valid_cost = np.where(cost <= 0, np.inf, valid_cost)
    
    min_idx = np.unravel_index(np.argmin(valid_cost), valid_cost.shape)
    min_value = float(valid_cost[min_idx])
    
    return (int(min_idx[0]), int(min_idx[1])), min_value


def create_3d_surface_data(
    cost: np.ndarray,
    slope: Optional[np.ndarray] = None,
    ndvi: Optional[np.ndarray] = None,
    elevation: Optional[np.ndarray] = None,
    transform: Any = None,
    subsample: int = 1
) -> Dict[str, Any]:
    """Prepare data for 3D surface visualization.
    
    Args:
        cost: Cost raster array
        slope: Optional slope raster array
        ndvi: Optional NDVI raster array
        elevation: Optional elevation raster array (for true Z axis)
        transform: Rasterio transform object for pixel->coord conversion
        subsample: Subsampling factor for large rasters (e.g., 2 = every 2nd pixel)
        
    Returns:
        Dictionary with X, Y, Z coordinates and color data
    """
    rows, cols = cost.shape
    
    # Subsample for performance on large rasters
    if subsample > 1:
        cost = cost[::subsample, ::subsample]
        if slope is not None:
            slope = slope[::subsample, ::subsample]
        if ndvi is not None:
            ndvi = ndvi[::subsample, ::subsample]
        if elevation is not None:
            elevation = elevation[::subsample, ::subsample]
        rows, cols = cost.shape
    
    # Create coordinate grids
    # Use transform if available to get real world coordinates
    if transform:
        # Extract affine params from transform (Affine object)
        a, b, c, d, e, f = transform.a, transform.b, transform.c, transform.d, transform.e, transform.f
        
        # Adjust step size by subsample
        step_x = a * subsample
        step_y = e * subsample
        
        # Origin (top-left)
        x_min = c
        y_max = f
        
        # Generate axes
        x_axis = x_min + np.arange(cols) * step_x
        y_axis = y_max + np.arange(rows) * step_y
        
        X, Y = np.meshgrid(x_axis, y_axis)
    else:
        # Fallback to pixel coords
        x = np.arange(cols)
        y = np.arange(rows)
        X, Y = np.meshgrid(x, y)
    
    # Z = elevation if available, else cost
    if elevation is not None:
        Z = np.nan_to_num(elevation, nan=0.0)
    else:
        Z = np.nan_to_num(cost, nan=0.0)
    
    # Normalize Z for better visualization
    z_min, z_max = np.nanmin(Z), np.nanmax(Z)
    if z_max > z_min:
        Z_norm = (Z - z_min) / (z_max - z_min)
    else:
        Z_norm = Z.copy()
    
    return {
        "X": X,
        "Y": Y,
        "Z": Z,
        "cost": np.nan_to_num(cost, nan=0.0), # Added explicit cost array
        "Z_normalized": Z_norm,
        "cost_min": float(z_min),
        "cost_max": float(z_max),
        "shape": (rows, cols),
        "subsample": subsample,
        "slope": slope,
        "ndvi": ndvi
    }


def generate_3d_plotly_html(
    surface_data: Dict[str, Any],
    min_point: Tuple[int, int],
    output_path: str,
    title: str = "3D Cost Map Terrain Model",
    route_coords: Optional[List[Tuple[float, float]]] = None,
    spiral_coords: Optional[List[Tuple[float, float]]] = None
) -> str:
    """Generate interactive 3D HTML visualization using Plotly."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        raise ImportError("Plotly is required for 3D visualization. Install with: pip install plotly")
    
    X = surface_data["X"]
    Y = surface_data["Y"]
    Z = surface_data["Z"]
    subsample = surface_data["subsample"]
    
    # Adjust min_point for subsampling
    min_row = min_point[0] // subsample
    min_col = min_point[1] // subsample
    
    # Create figure with subplots
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "surface"}, {"type": "surface"}]],
        subplot_titles=("Cost Terrain (Red = High Cost Peaks)", "Priority Heatmap View"),
        horizontal_spacing=0.05
    )
    
    # Main 3D surface with cost-based coloring (red = high cost)
    surface1 = go.Surface(
        x=X,
        y=Y,
        z=Z,
        surfacecolor=surface_data.get("cost"), # Use cost for color (independent of Z height)
        colorscale=[
            [0.0, "rgb(0, 100, 0)"],      # Green (low cost - valleys)
            [0.3, "rgb(255, 255, 0)"],    # Yellow
            [0.6, "rgb(255, 165, 0)"],    # Orange
            [0.8, "rgb(255, 69, 0)"],     # Red-Orange
            [1.0, "rgb(139, 0, 0)"]       # Dark Red (high cost - peaks)
        ],
        colorbar=dict(title="Cost Value", x=0.45),
        name="Cost Terrain",
        showscale=True,
        opacity=0.9,
        lighting=dict(
            ambient=0.6,
            diffuse=0.8,
            specular=0.3,
            roughness=0.5
        )
    )
    fig.add_trace(surface1, row=1, col=1)
    
    # Add marker for minimum cost point (priority anchor)
    # Use actual GPS coordinates from the X/Y arrays
    anchor_x = float(X[min_row, min_col])
    anchor_y = float(Y[min_row, min_col])
    anchor_z = float(Z[min_row, min_col])
    
    fig.add_trace(go.Scatter3d(
        x=[anchor_x],
        y=[anchor_y],
        z=[anchor_z + 20],  # Slightly above surface
        mode='markers+text',
        marker=dict(size=10, color='cyan', symbol='diamond'),
        text=['Priority Anchor'],
        textposition='top center',
        name='Priority Anchor',
        showlegend=True
    ), row=1, col=1)
    
    # Second view: Inverted for priority visualization (valleys become peaks)
    Z_inverted = surface_data["cost_max"] - Z + surface_data["cost_min"]
    surface2 = go.Surface(
        x=X,
        y=Y,
        z=Z_inverted,
        colorscale=[
            [0.0, "rgb(139, 0, 0)"],       # Dark Red (low priority)
            [0.3, "rgb(255, 165, 0)"],     # Orange
            [0.6, "rgb(255, 255, 0)"],     # Yellow
            [0.8, "rgb(144, 238, 144)"],   # Light Green
            [1.0, "rgb(0, 100, 0)"]        # Dark Green (high priority)
        ],
        colorbar=dict(title="Priority Level", x=1.0),
        name="Priority View",
        showscale=True,
        opacity=0.9
    )
    fig.add_trace(surface2, row=1, col=2)
    
    # Add priority anchor marker to second view (use GPS coords)
    fig.add_trace(go.Scatter3d(
        x=[anchor_x],
        y=[anchor_y],
        z=[float(Z_inverted[min_row, min_col]) + 20],
        mode='markers',
        marker=dict(size=10, color='cyan', symbol='diamond'),
        name='Highest Priority',
        showlegend=False
    ), row=1, col=2)
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f"{title}<br><sub>Min Cost: {surface_data['cost_min']:.4f} | Max Cost: {surface_data['cost_max']:.4f}</sub>",
            x=0.5
        ),
        width=1600,
        height=800,
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Elevation (m)",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            aspectratio=dict(x=1, y=1, z=0.5)
        ),
        scene2=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Priority",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            aspectratio=dict(x=1, y=1, z=0.5)
        ),
        margin=dict(l=10, r=10, t=80, b=10)
    )
    
    # Save as HTML
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs=True, full_html=True)
    
    logger.info(f"Saved 3D interactive model: {output_path}")
    return str(output_path)


def generate_3d_matplotlib(
    surface_data: Dict[str, Any],
    min_point: Tuple[int, int],
    output_path: str,
    title: str = "3D Cost Map Terrain"
) -> str:
    """Generate static 3D visualization using Matplotlib (fallback).
    
    Args:
        surface_data: Data from create_3d_surface_data()
        min_point: (row, col) of minimum cost point
        output_path: Path to save PNG file
        title: Plot title
        
    Returns:
        Path to saved PNG file
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from matplotlib import cm
    
    X = surface_data["X"]
    Y = surface_data["Y"]
    Z = surface_data["Z"]
    subsample = surface_data["subsample"]
    
    # Adjust min_point for subsampling
    min_row = min_point[0] // subsample
    min_col = min_point[1] // subsample
    
    # Get anchor GPS coordinates
    anchor_x = float(X[min_row, min_col])
    anchor_y = float(Y[min_row, min_col])
    anchor_z = float(Z[min_row, min_col])
    
    fig = plt.figure(figsize=(16, 12))
    
    # First subplot: Cost terrain
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')
    surf1 = ax1.plot_surface(X, Y, Z, cmap='RdYlGn_r', alpha=0.9,
                              linewidth=0, antialiased=True)
    ax1.scatter([anchor_x], [anchor_y], [anchor_z], 
                c='cyan', s=100, marker='D', label='Priority Anchor')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_zlabel('Elevation (m)')
    ax1.set_title('Terrain with Cost Overlay')
    fig.colorbar(surf1, ax=ax1, shrink=0.5, label='Cost Value')
    
    # Second subplot: Priority view (inverted)
    ax2 = fig.add_subplot(1, 2, 2, projection='3d')
    Z_inverted = surface_data["cost_max"] - Z + surface_data["cost_min"]
    surf2 = ax2.plot_surface(X, Y, Z_inverted, cmap='RdYlGn', alpha=0.9,
                              linewidth=0, antialiased=True)
    ax2.scatter([anchor_x], [anchor_y], [float(Z_inverted[min_row, min_col])], 
                c='cyan', s=100, marker='D', label='Highest Priority')
    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('Latitude')
    ax2.set_zlabel('Priority')
    ax2.set_title('Priority View (Green = High Priority)')
    fig.colorbar(surf2, ax=ax2, shrink=0.5, label='Priority Level')
    
    plt.suptitle(f"{title}\nMin Cost: {surface_data['cost_min']:.4f} | Max Cost: {surface_data['cost_max']:.4f}")
    plt.tight_layout()
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved 3D static image: {output_path}")
    return str(output_path)


def build_3d_model(
    cost_path: str,
    output_path: str, # changed from output_dir
    slope_path: Optional[str] = None,
    ndvi_path: Optional[str] = None,
    elevation_path: Optional[str] = None,
    subsample: int = 1,
    use_plotly: bool = True,
    route_coords: Optional[List[Tuple[float, float]]] = None, # Added
    spiral_coords: Optional[List[Tuple[float, float]]] = None # Added
) -> Dict[str, Any]:
    """Main function to build 3D model from cost raster."""
    logger.info(f"Loading cost raster from: {cost_path}")
    cost, meta = load_raster(cost_path)
    
    # Load optional rasters
    slope = None
    ndvi = None
    elevation = None
    
    if slope_path and Path(slope_path).exists():
        slope, _ = load_raster(slope_path)
        logger.info(f"Loaded slope raster: {slope_path}")
    if ndvi_path and Path(ndvi_path).exists():
        ndvi, _ = load_raster(ndvi_path)
        logger.info(f"Loaded NDVI raster: {ndvi_path}")
    if elevation_path and Path(elevation_path).exists():
        elevation, _ = load_raster(elevation_path)
        logger.info(f"Loaded Elevation raster: {elevation_path}")
    
    # Find minimum cost point
    min_point, min_value = find_min_cost_point(cost)
    logger.info(f"Priority anchor (min cost): ({min_point[0]}, {min_point[1]}) = {min_value:.6f}")
    
    # Prepare surface data
    surface_data = create_3d_surface_data(
        cost, slope, ndvi, elevation, meta['transform'], subsample
    )
    
    # Create output directory
    output_file = Path(output_path)
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate visualizations
    results = {
        "priority_anchor": {
            "row": min_point[0],
            "col": min_point[1],
            "cost_value": min_value
        },
        "cost_stats": {
            "min": float(surface_data["cost_min"]),
            "max": float(surface_data["cost_max"]),
            "shape": surface_data["shape"]
        },
        "meta": {
            "crs": str(meta.get("crs", "unknown")),
            "subsample": subsample
        }
    }
    
    if use_plotly:
        try:
            html_path = generate_3d_plotly_html(
                surface_data, min_point,
                str(output_file),
                title="3D Cost Map Terrain Model",
                route_coords=route_coords,
                spiral_coords=spiral_coords
            )
            results["html_3d"] = html_path
        except ImportError as e:
            logger.warning(f"Plotly not available: {e}. Falling back to Matplotlib.")
            use_plotly = False
    
    if not use_plotly:
        png_path = generate_3d_matplotlib(
            surface_data, min_point,
            str(output_file.with_suffix('.png')),
            title="3D Cost Map Terrain Model"
        )
        results["png_3d"] = png_path
    
    # Also generate static image if plotly was used
    if use_plotly:
        try:
            png_path = generate_3d_matplotlib(
                surface_data, min_point,
                str(output_file.with_name(output_file.stem + "_static.png")),
                title="3D Cost Map Terrain Model"
            )
            results["png_3d_static"] = png_path
        except Exception as e:
            logger.warning(f"Could not generate static image: {e}")
    
    return results


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Default test with out_demo_plan
    cost_path = "out_demo_plan/rasters/cost.tif"
    slope_path = "out_demo_plan/rasters/slope.tif"
    ndvi_path = "out_demo_plan/rasters/ndvi.tif"
    output_dir = "scripts/routing2.0/output/3d_model"
    
    if len(sys.argv) > 1:
        cost_path = sys.argv[1]
    
    results = build_3d_model(
        cost_path=cost_path,
        output_dir=output_dir,
        slope_path=slope_path,
        ndvi_path=ndvi_path,
        subsample=2,
        use_plotly=True
    )
    
    print("\n=== 3D Model Results ===")
    print(json.dumps(results, indent=2))
