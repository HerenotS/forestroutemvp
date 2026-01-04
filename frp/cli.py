import argparse
import logging
import json
import os
from typing import Optional

from frp.aoi import load_aoi
from frp.preprocess import reproject_and_clip
from frp.derived import compute_ndvi, compute_slope
from frp.costmap import build_cost_map
from frp.coverage import plan_coverage
from frp.waypoints import lines_to_waypoints
from frp.astar import optimize_route_segments
from frp.export import export_route
from frp.utils import ensure_dir, write_raster, parse_weights
import numpy as np

logger = logging.getLogger("frp.cli")


def run_pipeline(
    aoi_geom,
    nir_path: str,
    red_path: str,
    dem_path: Optional[str],
    resolution: float,
    tile_size: int,
    weights: dict,
    out_dir: str,
    run_astar: bool = True,
    sweep_spacing_m: Optional[float] = None,
    waypoint_spacing_m: float = 10.0,
    simplify_m: float = 0.0,
    geojson_geometry: str = "linestring",
    max_waypoints: int = 2000,
):
    out_rasters = os.path.join(out_dir, "rasters")
    out_routes = os.path.join(out_dir, "routes")
    ensure_dir(out_rasters)
    ensure_dir(out_routes)

    # Preprocess NIR and RED
    nir_arr, nir_meta, utm_crs = reproject_and_clip(nir_path, aoi_geom, resolution)
    red_arr, red_meta, _ = reproject_and_clip(red_path, aoi_geom, resolution)

    # DEM
    if dem_path:
        dem_arr, dem_meta, _ = reproject_and_clip(dem_path, aoi_geom, resolution)
    else:
        dem_arr = None
        dem_meta = nir_meta

    ndvi = compute_ndvi(nir_arr, red_arr)
    ndvi_meta = nir_meta.copy()
    ndvi_meta.update({"dtype": "float32", "count": 1})
    ndvi_path = os.path.join(out_rasters, "ndvi.tif")
    write_raster(ndvi_path, ndvi, ndvi_meta)

    if dem_arr is not None:
        slope = compute_slope(dem_arr, resolution)
    else:
        slope = np.zeros_like(ndvi, dtype="float32")
    slope_meta = nir_meta.copy()
    slope_meta.update({"dtype": "float32", "count": 1})
    slope_path = os.path.join(out_rasters, "slope.tif")
    write_raster(slope_path, slope, slope_meta)

    cost, cost_meta = build_cost_map(ndvi, slope, ndvi_meta)
    cost_path = os.path.join(out_rasters, "cost.tif")
    write_raster(cost_path, cost, cost_meta)

    # Coverage plan (UTM coords)
    sweep_lines = plan_coverage(aoi_geom, utm_crs, resolution, tile_size, sweep_spacing_m)
    logger.info("Sweep lines planned: %d", len(sweep_lines))

    raw_waypoints = []
    for ln in sweep_lines:
        # collect line endpoints as raw
        try:
            raw_waypoints.extend(list(ln.coords))
        except Exception:
            pass
    logger.info("Raw sweep endpoints: %d", len(raw_waypoints))

    # Resample sweeps into waypoints at waypoint_spacing_m
    waypoints_utm = lines_to_waypoints(sweep_lines, spacing=waypoint_spacing_m)
    logger.info("Waypoints after resample (requested spacing %.2fm): %d", waypoint_spacing_m, len(waypoints_utm))

    # Automatic cap: if too many waypoints, increase spacing proportionally to reduce count
    effective_spacing = waypoint_spacing_m
    if max_waypoints and len(waypoints_utm) > max_waypoints:
        factor = float(len(waypoints_utm)) / float(max_waypoints)
        # increase spacing proportionally
        effective_spacing = waypoint_spacing_m * factor
        # recompute waypoints with increased spacing
        waypoints_utm = lines_to_waypoints(sweep_lines, spacing=effective_spacing)
        logger.info("Exceeded max_waypoints=%d, increased spacing to %.2fm -> final waypoints: %d", max_waypoints, effective_spacing, len(waypoints_utm))
    else:
        logger.info("Effective waypoint spacing: %.2fm", effective_spacing)

    # Simplify waypoints by creating a LineString in UTM, simplifying then extracting coords
    from shapely.geometry import LineString
    if simplify_m and simplify_m > 0 and len(waypoints_utm) >= 2:
        ls = LineString(waypoints_utm)
        ls_s = ls.simplify(simplify_m)
        # ensure it's a LineString after simplify
        if ls_s.is_empty:
            simplified = waypoints_utm
        elif ls_s.geom_type == 'LineString':
            simplified = list(ls_s.coords)
        else:
            simplified = []
            for part in ls_s:
                try:
                    simplified.extend(list(part.coords))
                except Exception:
                    pass
        logger.info("Waypoints after simplify: %d", len(simplified))
        final_waypoints_utm = simplified
    else:
        final_waypoints_utm = waypoints_utm
        logger.info("Waypoints after simplify: %d", len(final_waypoints_utm))

    # Optimize between waypoints (optional)
    if run_astar:
        optimized_points = optimize_route_segments(final_waypoints_utm, cost, cost_meta)
    else:
        logging.getLogger("frp.cli").info("DEMO: skipping A* optimization")
        optimized_points = final_waypoints_utm

    # Export route
    geojson_path = os.path.join(out_routes, "route.geojson")
    kml_path = os.path.join(out_routes, "route.kml")
    export_route(optimized_points, utm_crs, geojson_path, kml_path, geojson_geometry=geojson_geometry)

    report = {
        "inputs": {"nir": nir_path, "red": red_path, "dem": dem_path},
        "params": {"resolution": resolution, "tile_size": tile_size, "weights": weights},
        "outputs": {"ndvi": ndvi_path, "slope": slope_path, "cost": cost_path, "geojson": geojson_path, "kml": kml_path},
    }
    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    logger.info("Pipeline finished. Outputs written to %s", out_dir)


def main():
    parser = argparse.ArgumentParser(description="Forestroute Planner (MVP)")
    sub = parser.add_subparsers(dest="cmd")
    plan_p = sub.add_parser("plan")
    group = plan_p.add_mutually_exclusive_group(required=True)
    group.add_argument("--aoi", help="AOI GeoJSON file path")
    group.add_argument("--bbox", help='bbox string "minLon,minLat,maxLon,maxLat"')
    plan_p.add_argument("--nir", required=True)
    plan_p.add_argument("--red", required=True)
    plan_p.add_argument("--dem", required=False)
    plan_p.add_argument("--resolution", type=float, required=True)
    plan_p.add_argument("--tile-size", type=int, default=512)
    plan_p.add_argument("--weights", default="slope=0.5,ndvi=0.5")
    plan_p.add_argument("--sweep-spacing-m", type=float, default=None, help="Sweep line spacing in meters")
    plan_p.add_argument("--waypoint-spacing-m", type=float, default=10.0, help="Waypoint spacing in meters")
    plan_p.add_argument("--simplify-m", type=float, default=0.0, help="Simplify tolerance in meters (Douglas-Peucker)")
    plan_p.add_argument("--geojson-geometry", choices=["points","linestring"], default="linestring", help="GeoJSON geometry type for route")
    plan_p.add_argument("--output-dir", default="out")
    plan_p.add_argument("--max-waypoints", type=int, default=2000, help="Maximum allowed waypoints (auto-increase spacing to respect)")

    demo_p = sub.add_parser("demo")
    demo_p.add_argument("--output-dir", default="out_demo")
    demo_p.add_argument("--sweep-spacing-m", type=float, default=None)
    demo_p.add_argument("--waypoint-spacing-m", type=float, default=10.0)
    demo_p.add_argument("--simplify-m", type=float, default=0.0)
    demo_p.add_argument("--geojson-geometry", choices=["points","linestring"], default="linestring")
    demo_p.add_argument("--max-waypoints", type=int, default=2000)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.cmd == "plan":
        aoi = load_aoi(args.aoi, args.bbox)
        weights = parse_weights(args.weights)
        run_pipeline(
            aoi,
            args.nir,
            args.red,
            args.dem,
            args.resolution,
            args.tile_size,
            weights,
            args.output_dir,
            run_astar=True,
            sweep_spacing_m=args.sweep_spacing_m,
            waypoint_spacing_m=args.waypoint_spacing_m,
            simplify_m=args.simplify_m,
            geojson_geometry=args.geojson_geometry,
        )
    elif args.cmd == "demo":
        # lazy import to avoid heavy deps when not running demo
        from frp.utils import make_demo_data

        ensure_dir(args.output_dir)
        demo_paths = make_demo_data(args.output_dir)
        aoi = load_aoi(demo_paths["aoi"], None)
        weights = {"slope": 0.5, "ndvi": 0.5}
        run_pipeline(
            aoi,
            demo_paths["nir"],
            demo_paths["red"],
            demo_paths.get("dem"),
            10.0,
            512,
            weights,
            args.output_dir,
            run_astar=False,
            sweep_spacing_m=args.sweep_spacing_m,
            waypoint_spacing_m=args.waypoint_spacing_m,
            simplify_m=args.simplify_m,
            geojson_geometry=args.geojson_geometry,
            max_waypoints=args.max_waypoints,
        )
    else:
        parser.print_help()
