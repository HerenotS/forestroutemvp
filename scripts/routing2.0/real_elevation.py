#!/usr/bin/env python
"""
Real Elevation Data Fetcher

Fetches real elevation/altitude data from Open Topo Data API (SRTM 30m dataset)
for GPS coordinates. Generates proper terrain rasters based on actual topography.

Usage:
    from real_elevation import generate_real_terrain
    result = generate_real_terrain(polygon_coords, output_dir, resolution_meters=10)
"""

import logging
import time
import json
import requests
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from shapely.geometry import Polygon, Point
from concurrent.futures import ThreadPoolExecutor
import math

logger = logging.getLogger("routing2.0.real_elevation")

# Constants
EARTH_RADIUS_M = 6371000  # Earth's radius in meters
OPEN_TOPO_API = "https://api.opentopodata.org/v1/srtm30m"
MAX_LOCATIONS_PER_REQUEST = 100
API_RATE_LIMIT_SECONDS = 1.1  # Slightly more than 1 second to be safe


def meters_to_degrees(meters: float, latitude: float) -> Tuple[float, float]:
    """
    Convert meters to degrees at a given latitude.
    
    Returns:
        (lon_degrees, lat_degrees) - the degree equivalents
    """
    # Latitude degrees are constant
    lat_deg = meters / 111320.0
    
    # Longitude degrees depend on latitude
    lon_deg = meters / (111320.0 * math.cos(math.radians(latitude)))
    
    return lon_deg, lat_deg


def generate_grid_points(
    polygon_coords: List[Tuple[float, float]],
    resolution_meters: float = 10.0
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Generate a grid of points covering the polygon bounding box at specified resolution.
    
    Args:
        polygon_coords: List of (lon, lat) tuples defining the polygon
        resolution_meters: Distance between grid points in meters
        
    Returns:
        (lon_grid, lat_grid, metadata)
    """
    # Extract bounds
    lons = [c[0] for c in polygon_coords]
    lats = [c[1] for c in polygon_coords]
    
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    
    # Calculate center latitude for degree conversion
    center_lat = (min_lat + max_lat) / 2
    
    # Convert resolution to degrees
    lon_res, lat_res = meters_to_degrees(resolution_meters, center_lat)
    
    logger.info(f"Resolution: {resolution_meters}m = ({lon_res:.6f}° lon, {lat_res:.6f}° lat)")
    
    # Generate grid axes
    lon_axis = np.arange(min_lon, max_lon + lon_res, lon_res)
    lat_axis = np.arange(max_lat, min_lat - lat_res, -lat_res)  # Top to bottom
    
    # Create meshgrid
    lon_grid, lat_grid = np.meshgrid(lon_axis, lat_axis)
    
    logger.info(f"Grid size: {lon_grid.shape[1]} x {lon_grid.shape[0]} = {lon_grid.size} points")
    
    metadata = {
        "bounds": (min_lon, min_lat, max_lon, max_lat),
        "resolution_meters": resolution_meters,
        "resolution_degrees": (lon_res, lat_res),
        "width": lon_grid.shape[1],
        "height": lon_grid.shape[0],
        "center_lat": center_lat,
        "transform": from_bounds(min_lon, min_lat, max_lon, max_lat, 
                                  lon_grid.shape[1], lon_grid.shape[0])
    }
    
    return lon_grid, lat_grid, metadata


def fetch_elevations_batch(
    locations: List[Tuple[float, float]],
    dataset: str = "srtm30m"
) -> List[Optional[float]]:
    """
    Fetch elevations for a batch of locations from Open Topo Data API.
    
    Args:
        locations: List of (lat, lon) tuples (note: API expects lat,lon order)
        dataset: Dataset to use (srtm30m, mapzen, aster30m, etc.)
        
    Returns:
        List of elevation values (or None for failed lookups)
    """
    if not locations:
        return []
    
    # Format locations for API
    locations_str = "|".join([f"{lat},{lon}" for lat, lon in locations])
    
    url = f"https://api.opentopodata.org/v1/{dataset}"
    params = {"locations": locations_str}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "OK":
            logger.warning(f"API returned status: {data.get('status')}")
            return [None] * len(locations)
        
        elevations = []
        for result in data.get("results", []):
            elev = result.get("elevation")
            elevations.append(float(elev) if elev is not None else None)
        
        return elevations
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return [None] * len(locations)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse API response: {e}")
        return [None] * len(locations)


def fetch_all_elevations(
    lon_grid: np.ndarray,
    lat_grid: np.ndarray,
    polygon: Optional[Polygon] = None,
    dataset: str = "srtm30m"
) -> np.ndarray:
    """
    Fetch elevations for entire grid, respecting API rate limits.
    
    Args:
        lon_grid: 2D array of longitudes
        lat_grid: 2D array of latitudes
        polygon: Optional polygon to mask points outside
        dataset: Elevation dataset to use
        
    Returns:
        2D array of elevations matching input grid shape
    """
    height, width = lon_grid.shape
    elevations = np.full((height, width), np.nan)
    
    # Flatten grids for batch processing
    all_points = []
    point_indices = []
    
    for i in range(height):
        for j in range(width):
            lon, lat = lon_grid[i, j], lat_grid[i, j]
            
            # Skip if outside polygon
            if polygon is not None:
                if not polygon.contains(Point(lon, lat)):
                    continue
            
            # API expects (lat, lon) order
            all_points.append((lat, lon))
            point_indices.append((i, j))
    
    total_points = len(all_points)
    logger.info(f"Fetching elevation for {total_points} points inside polygon...")
    
    if total_points == 0:
        logger.warning("No points inside polygon!")
        return elevations
    
    # Process in batches
    num_batches = (total_points + MAX_LOCATIONS_PER_REQUEST - 1) // MAX_LOCATIONS_PER_REQUEST
    logger.info(f"Will make {num_batches} API calls (max {MAX_LOCATIONS_PER_REQUEST} per call)")
    
    fetched = 0
    for batch_idx in range(num_batches):
        start_idx = batch_idx * MAX_LOCATIONS_PER_REQUEST
        end_idx = min(start_idx + MAX_LOCATIONS_PER_REQUEST, total_points)
        
        batch_points = all_points[start_idx:end_idx]
        batch_indices = point_indices[start_idx:end_idx]
        
        # Fetch batch
        batch_elevations = fetch_elevations_batch(batch_points, dataset)
        
        # Store results
        for (i, j), elev in zip(batch_indices, batch_elevations):
            if elev is not None:
                elevations[i, j] = elev
                fetched += 1
        
        # Progress
        progress = (batch_idx + 1) / num_batches * 100
        logger.info(f"Progress: {progress:.1f}% ({fetched}/{total_points} points fetched)")
        
        # Rate limit
        if batch_idx < num_batches - 1:
            time.sleep(API_RATE_LIMIT_SECONDS)
    
    # Fill NaN values with interpolation
    nan_count = np.sum(np.isnan(elevations))
    if nan_count > 0:
        logger.info(f"Interpolating {nan_count} missing elevation values...")
        elevations = interpolate_missing(elevations)
    
    return elevations


def interpolate_missing(data: np.ndarray) -> np.ndarray:
    """Interpolate NaN values using nearby values."""
    from scipy import ndimage
    
    mask = np.isnan(data)
    if not np.any(mask):
        return data
    
    # Get valid data mean for fallback
    valid_mean = np.nanmean(data) if np.any(~mask) else 0.0
    
    # Simple nearest-neighbor interpolation
    indices = ndimage.distance_transform_edt(
        mask, return_distances=False, return_indices=True
    )
    
    result = data[tuple(indices)]
    
    # Handle edge case where all values are NaN
    if np.all(np.isnan(result)):
        result = np.full_like(data, valid_mean)
    
    return result


def compute_slope(elevation: np.ndarray, resolution_meters: float) -> np.ndarray:
    """
    Compute slope in degrees from elevation grid.
    
    Args:
        elevation: 2D elevation array in meters
        resolution_meters: Grid cell size in meters
        
    Returns:
        2D array of slope in degrees
    """
    # Compute gradients
    dy, dx = np.gradient(elevation, resolution_meters)
    
    # Slope magnitude
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    
    return slope_deg


def compute_cost(slope: np.ndarray, max_slope: float = 45.0) -> np.ndarray:
    """
    Compute traversal cost from slope.
    
    Cost is normalized 0-1 based on slope.
    Higher slope = higher cost.
    
    Args:
        slope: 2D slope array in degrees
        max_slope: Maximum expected slope (for normalization)
        
    Returns:
        2D cost array (0-1)
    """
    # Normalize slope to 0-1
    cost = np.clip(slope / max_slope, 0, 1)
    
    # Add small base cost (even flat terrain has some traversal cost)
    cost = 0.1 + 0.9 * cost
    
    return cost


def generate_real_terrain(
    polygon_coords: List[Tuple[float, float]],
    output_dir: Path,
    resolution_meters: float = 10.0,
    dataset: str = "srtm30m"
) -> Dict[str, Any]:
    """
    Generate terrain rasters from real elevation data.
    
    Args:
        polygon_coords: List of (lon, lat) tuples defining the AOI polygon
        output_dir: Directory to save output rasters
        resolution_meters: Grid resolution in meters (default 10m)
        dataset: Elevation dataset to use (srtm30m, mapzen, aster30m)
        
    Returns:
        Dictionary with paths to generated rasters and metadata
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("="*60)
    logger.info("Generating Real Terrain Data from OpenTopoData API")
    logger.info("="*60)
    
    # Create polygon for masking
    polygon = Polygon(polygon_coords) if len(polygon_coords) > 2 else None
    
    # Generate grid
    logger.info(f"Creating grid at {resolution_meters}m resolution...")
    lon_grid, lat_grid, meta = generate_grid_points(polygon_coords, resolution_meters)
    
    # Fetch real elevation data
    logger.info(f"Fetching elevation from {dataset} dataset...")
    elevation = fetch_all_elevations(lon_grid, lat_grid, polygon, dataset)
    
    # Compute derived layers
    logger.info("Computing slope...")
    slope = compute_slope(elevation, resolution_meters)
    
    logger.info("Computing cost...")
    cost = compute_cost(slope)
    
    # Create raster metadata
    raster_meta = {
        'driver': 'GTiff',
        'height': meta['height'],
        'width': meta['width'],
        'count': 1,
        'dtype': 'float32',
        'crs': 'EPSG:4326',
        'transform': meta['transform']
    }
    
    # Save rasters
    paths = {}
    
    # Elevation
    elev_path = output_dir / "elevation.tif"
    with rasterio.open(elev_path, 'w', **raster_meta) as dst:
        dst.write(elevation.astype(np.float32), 1)
    paths['elevation'] = elev_path
    logger.info(f"Saved: {elev_path}")
    
    # Slope
    slope_path = output_dir / "slope.tif"
    with rasterio.open(slope_path, 'w', **raster_meta) as dst:
        dst.write(slope.astype(np.float32), 1)
    paths['slope'] = slope_path
    logger.info(f"Saved: {slope_path}")
    
    # Cost
    cost_path = output_dir / "cost.tif"
    with rasterio.open(cost_path, 'w', **raster_meta) as dst:
        dst.write(cost.astype(np.float32), 1)
    paths['cost'] = cost_path
    logger.info(f"Saved: {cost_path}")
    
    # NDVI placeholder (would need satellite imagery)
    ndvi = np.full_like(elevation, 0.5)  # Default vegetation index
    ndvi_path = output_dir / "ndvi.tif"
    with rasterio.open(ndvi_path, 'w', **raster_meta) as dst:
        dst.write(ndvi.astype(np.float32), 1)
    paths['ndvi'] = ndvi_path
    logger.info(f"Saved: {ndvi_path}")
    
    # Summary
    logger.info("="*60)
    logger.info("Terrain Generation Complete")
    logger.info(f"  Grid size: {meta['width']} x {meta['height']}")
    logger.info(f"  Elevation range: {np.nanmin(elevation):.1f}m - {np.nanmax(elevation):.1f}m")
    logger.info(f"  Slope range: {np.nanmin(slope):.1f}° - {np.nanmax(slope):.1f}°")
    logger.info("="*60)
    
    return {
        'elevation': paths['elevation'],
        'slope': paths['slope'],
        'cost': paths['cost'],
        'ndvi': paths['ndvi'],
        'meta': raster_meta,
        'grid_meta': meta,
        'data': {
            'elevation': elevation,
            'slope': slope,
            'cost': cost,
            'lon_grid': lon_grid,
            'lat_grid': lat_grid
        }
    }


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Test with user's Mexico coordinates
    test_coords = [
        (-99.48102480900964, 19.33092754657079),
        (-99.45615992746475, 19.174421321106877),
        (-99.19438553686399, 19.238597791679112),
        (-99.28224730285173, 19.31677622590452),
        (-99.42147679874869, 19.372813645373085),
        (-99.48102480900964, 19.33092754657079)  # Close the polygon
    ]
    
    output = Path("test_real_elevation/rasters")
    
    # Use 100m resolution for testing (10m would be many API calls)
    result = generate_real_terrain(test_coords, output, resolution_meters=100)
    
    print("\n✓ Test complete!")
    print(f"  Files saved to: {output}")
