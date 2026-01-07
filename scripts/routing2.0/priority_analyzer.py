"""
Priority Analyzer Module

Analyzes terrain data to identify:
- Priority anchor points (lowest cost / easiest traversal)
- High-cost regions (obstacles/difficult terrain)
- Priority zones and gradients
- Statistical distribution of priorities
"""

import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List

import numpy as np

logger = logging.getLogger("routing2.0.priority_analyzer")


def load_raster(path: str) -> Tuple[np.ndarray, dict]:
    """Load a raster file and return (data, metadata)."""
    import rasterio
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        meta = src.meta.copy()
        meta["transform"] = src.transform
        meta["crs"] = src.crs
        meta["bounds"] = src.bounds
    return data, meta


def find_priority_anchor(cost: np.ndarray) -> Dict[str, Any]:
    """Find the global minimum cost point (priority anchor).
    
    This represents the 'lowest energy' point - easiest traversal location.
    """
    # Mask invalid values
    valid_mask = ~np.isnan(cost) & (cost > 0)
    if not np.any(valid_mask):
        return {"found": False}
    
    valid_cost = np.where(valid_mask, cost, np.inf)
    min_idx = np.unravel_index(np.argmin(valid_cost), valid_cost.shape)
    min_value = float(valid_cost[min_idx])
    
    return {
        "found": True,
        "row": int(min_idx[0]),
        "col": int(min_idx[1]),
        "cost": min_value,
        "description": "Global minimum cost point - optimal priority anchor"
    }


def find_local_minima(cost: np.ndarray, neighborhood: int = 5) -> List[Dict[str, Any]]:
    """Find local minima in the cost surface (multiple priority anchor candidates).
    
    Args:
        cost: Cost raster array
        neighborhood: Size of neighborhood to check for local minimum
        
    Returns:
        List of local minima with their properties
    """
    from scipy.ndimage import minimum_filter, label
    
    # Handle NaN values
    valid_mask = ~np.isnan(cost) & (cost > 0)
    cost_filled = np.where(valid_mask, cost, np.max(cost[valid_mask]) if np.any(valid_mask) else 1.0)
    
    # Find local minima using minimum filter
    local_min = minimum_filter(cost_filled, size=neighborhood)
    is_minimum = (cost_filled == local_min) & valid_mask
    
    # Label connected regions
    labeled, num_features = label(is_minimum)
    
    minima = []
    for i in range(1, num_features + 1):
        region_mask = labeled == i
        region_indices = np.where(region_mask)
        if len(region_indices[0]) == 0:
            continue
        
        # Find centroid of region
        center_row = int(np.mean(region_indices[0]))
        center_col = int(np.mean(region_indices[1]))
        
        # Get cost at centroid
        cost_val = float(cost[center_row, center_col])
        
        minima.append({
            "id": i,
            "row": center_row,
            "col": center_col,
            "cost": cost_val,
            "area_pixels": int(np.sum(region_mask))
        })
    
    # Sort by cost (lowest first)
    minima.sort(key=lambda x: x["cost"])
    
    return minima


def find_high_cost_regions(
    cost: np.ndarray,
    threshold_percentile: float = 90
) -> Dict[str, Any]:
    """Find high-cost regions that represent obstacles or difficult terrain.
    
    Args:
        cost: Cost raster array
        threshold_percentile: Percentile above which is considered high-cost
        
    Returns:
        Dictionary with high-cost region analysis
    """
    from scipy.ndimage import label
    
    valid_mask = ~np.isnan(cost) & (cost > 0)
    valid_values = cost[valid_mask]
    
    if len(valid_values) == 0:
        return {"found": False}
    
    threshold = float(np.percentile(valid_values, threshold_percentile))
    high_cost_mask = valid_mask & (cost >= threshold)
    
    labeled, num_regions = label(high_cost_mask)
    
    regions = []
    for i in range(1, num_regions + 1):
        region_mask = labeled == i
        region_values = cost[region_mask]
        region_indices = np.where(region_mask)
        
        if len(region_values) == 0:
            continue
        
        # Find centroid
        center_row = int(np.mean(region_indices[0]))
        center_col = int(np.mean(region_indices[1]))
        
        regions.append({
            "id": i,
            "center_row": center_row,
            "center_col": center_col,
            "area_pixels": int(np.sum(region_mask)),
            "mean_cost": float(np.mean(region_values)),
            "max_cost": float(np.max(region_values))
        })
    
    # Sort by area (largest first)
    regions.sort(key=lambda x: x["area_pixels"], reverse=True)
    
    return {
        "found": len(regions) > 0,
        "threshold": threshold,
        "threshold_percentile": threshold_percentile,
        "num_regions": len(regions),
        "total_high_cost_pixels": int(np.sum(high_cost_mask)),
        "percentage_of_total": float(np.sum(high_cost_mask)) / float(np.sum(valid_mask)) * 100,
        "regions": regions[:20]  # Top 20 regions
    }


def compute_priority_zones(
    cost: np.ndarray,
    num_zones: int = 5
) -> Dict[str, Any]:
    """Divide the area into priority zones based on cost quantiles.
    
    Args:
        cost: Cost raster array
        num_zones: Number of priority zones (1 = highest priority, N = lowest)
        
    Returns:
        Dictionary with zone boundaries and statistics
    """
    valid_mask = ~np.isnan(cost) & (cost > 0)
    valid_values = cost[valid_mask]
    
    if len(valid_values) == 0:
        return {"zones": []}
    
    # Compute quantile boundaries
    quantiles = np.linspace(0, 100, num_zones + 1)
    boundaries = [float(np.percentile(valid_values, q)) for q in quantiles]
    
    zones = []
    zone_map = np.zeros_like(cost, dtype=np.int32)
    
    for i in range(num_zones):
        lower = boundaries[i]
        upper = boundaries[i + 1]
        
        if i == num_zones - 1:
            zone_mask = valid_mask & (cost >= lower) & (cost <= upper)
        else:
            zone_mask = valid_mask & (cost >= lower) & (cost < upper)
        
        zone_values = cost[zone_mask]
        zone_map[zone_mask] = i + 1
        
        zones.append({
            "zone": i + 1,
            "priority_level": num_zones - i,  # Higher zone number = lower priority
            "cost_range": [float(lower), float(upper)],
            "pixel_count": int(np.sum(zone_mask)),
            "mean_cost": float(np.mean(zone_values)) if len(zone_values) > 0 else 0.0,
            "description": f"Zone {i+1}: {'High' if i == 0 else 'Medium' if i < num_zones-1 else 'Low'} priority"
        })
    
    return {
        "num_zones": num_zones,
        "boundaries": boundaries,
        "zones": zones,
        "zone_map": zone_map
    }


def compute_gradient_field(cost: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Compute gradient field showing direction of steepest descent (toward low cost).
    
    Returns:
        (gradient_y, gradient_x) - negative gradient points toward low cost
    """
    # Handle NaN
    cost_filled = np.nan_to_num(cost, nan=np.nanmax(cost))
    
    # Compute gradient (negative = toward low cost)
    grad_y, grad_x = np.gradient(cost_filled)
    
    return -grad_y, -grad_x  # Negative to point toward low cost


def analyze_priority_distribution(cost: np.ndarray) -> Dict[str, Any]:
    """Analyze the statistical distribution of priorities (inverse of cost).
    
    Returns comprehensive statistics about the priority distribution.
    """
    valid_mask = ~np.isnan(cost) & (cost > 0)
    valid_values = cost[valid_mask]
    
    if len(valid_values) == 0:
        return {"valid": False}
    
    cost_min = float(np.min(valid_values))
    cost_max = float(np.max(valid_values))
    
    # Priority = 1 - normalized_cost (0-1 scale)
    if cost_max > cost_min:
        priority_values = 1.0 - (valid_values - cost_min) / (cost_max - cost_min)
    else:
        priority_values = np.ones_like(valid_values) * 0.5
    
    return {
        "valid": True,
        "cost_statistics": {
            "min": cost_min,
            "max": cost_max,
            "mean": float(np.mean(valid_values)),
            "std": float(np.std(valid_values)),
            "median": float(np.median(valid_values))
        },
        "priority_statistics": {
            "min": float(np.min(priority_values)),
            "max": float(np.max(priority_values)),
            "mean": float(np.mean(priority_values)),
            "std": float(np.std(priority_values)),
            "median": float(np.median(priority_values))
        },
        "percentiles": {
            "p10": float(np.percentile(valid_values, 10)),
            "p25": float(np.percentile(valid_values, 25)),
            "p50": float(np.percentile(valid_values, 50)),
            "p75": float(np.percentile(valid_values, 75)),
            "p90": float(np.percentile(valid_values, 90))
        },
        "total_valid_pixels": int(len(valid_values))
    }


def generate_priority_report(
    cost_path: str,
    slope_path: Optional[str] = None,
    ndvi_path: Optional[str] = None
) -> Dict[str, Any]:
    """Generate comprehensive priority analysis report.
    
    Args:
        cost_path: Path to cost.tif
        slope_path: Optional path to slope.tif
        ndvi_path: Optional path to ndvi.tif
        
    Returns:
        Dictionary with complete priority analysis
    """
    logger.info(f"Loading cost raster: {cost_path}")
    cost, meta = load_raster(cost_path)
    
    report = {
        "source": str(cost_path),
        "raster_shape": cost.shape,
        "crs": str(meta.get("crs", "unknown"))
    }
    
    # 1. Priority anchor
    logger.info("Finding priority anchor...")
    report["priority_anchor"] = find_priority_anchor(cost)
    
    # 2. Local minima
    logger.info("Finding local minima...")
    try:
        report["local_minima"] = find_local_minima(cost, neighborhood=10)[:10]  # Top 10
    except ImportError:
        logger.warning("scipy not available for local minima detection")
        report["local_minima"] = []
    
    # 3. High cost regions
    logger.info("Analyzing high cost regions...")
    try:
        report["high_cost_regions"] = find_high_cost_regions(cost, threshold_percentile=90)
    except ImportError:
        logger.warning("scipy not available for region detection")
        report["high_cost_regions"] = {"found": False}
    
    # 4. Priority zones
    logger.info("Computing priority zones...")
    zones_result = compute_priority_zones(cost, num_zones=5)
    report["priority_zones"] = {k: v for k, v in zones_result.items() if k != "zone_map"}
    
    # 5. Priority distribution
    logger.info("Analyzing priority distribution...")
    report["distribution"] = analyze_priority_distribution(cost)
    
    # 6. Optional: Slope and NDVI correlation
    if slope_path and Path(slope_path).exists():
        slope, _ = load_raster(slope_path)
        valid_mask = ~np.isnan(cost) & (cost > 0) & ~np.isnan(slope)
        if np.any(valid_mask):
            corr = np.corrcoef(cost[valid_mask], slope[valid_mask])[0, 1]
            report["slope_correlation"] = float(corr) if not np.isnan(corr) else 0.0
    
    if ndvi_path and Path(ndvi_path).exists():
        ndvi, _ = load_raster(ndvi_path)
        valid_mask = ~np.isnan(cost) & (cost > 0) & ~np.isnan(ndvi)
        if np.any(valid_mask):
            corr = np.corrcoef(cost[valid_mask], ndvi[valid_mask])[0, 1]
            report["ndvi_correlation"] = float(corr) if not np.isnan(corr) else 0.0
    
    return report


if __name__ == "__main__":
    import sys
    import json
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Default test paths
    cost_path = "out_demo_plan/rasters/cost.tif"
    slope_path = "out_demo_plan/rasters/slope.tif"
    ndvi_path = "out_demo_plan/rasters/ndvi.tif"
    
    if len(sys.argv) > 1:
        cost_path = sys.argv[1]
    
    report = generate_priority_report(
        cost_path=cost_path,
        slope_path=slope_path,
        ndvi_path=ndvi_path
    )
    
    print("\n=== Priority Analysis Report ===")
    print(json.dumps(report, indent=2, default=str))
