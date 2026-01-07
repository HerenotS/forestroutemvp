#!/usr/bin/env python
"""
Routing 2.0 - Main Pipeline Script

Orchestrates the complete 3D visualization and multi-dimensional graph generation:
1. Load configuration and polygon data
2. Build 3D cost terrain model
3. Generate multi-dimensional NetworkX graph
4. Analyze priorities and terrain factors
5. Optimize sample route with A*
6. Create all visualizations
7. Generate summary report

Usage:
    python pipeline.py [--config CONFIG_PATH] [--polygon POLYGON_PATH] [--raster-dir RASTER_DIR] [--output-dir OUTPUT_DIR]

Example:
    python pipeline.py --raster-dir out_demo_plan/rasters --output-dir scripts/routing2.0/output
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent paths for imports
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(script_dir))

# Import routing 2.0 modules
from cost_3d_model import build_3d_model
from multidim_graph import build_multidim_graph, save_graph, get_graph_statistics, find_min_cost_node
from priority_analyzer import generate_priority_report
from route_optimizer import optimize_route_demo, compare_weight_strategies, path_to_coordinates, generate_spiral_path
from graph_visualizer import (
    visualize_2d_priority_map,
    visualize_3d_network,
    visualize_route_comparison,
    create_priority_heatmap
)
from report_generator import generate_summary_report, save_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("routing2.0.pipeline")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def load_polygon_bounds(polygon_path: str) -> Dict[str, Any]:
    """Load polygon from GeoJSON and extract bounds."""
    with open(polygon_path, 'r') as f:
        geojson = json.load(f)
    
    # Extract coordinates from first feature
    if geojson.get("type") == "FeatureCollection":
        features = geojson.get("features", [])
        if features:
            geometry = features[0].get("geometry", {})
            coords = geometry.get("coordinates", [[]])
            if geometry.get("type") == "Polygon":
                coords = coords[0]
            
            # Compute bounds
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            
            return {
                "name": features[0].get("properties", {}).get("name", "AOI"),
                "bounds": {
                    "min_lon": min(lons),
                    "max_lon": max(lons),
                    "min_lat": min(lats),
                    "max_lat": max(lats)
                },
                "coordinates": coords
            }
    
    return {"name": "Unknown", "bounds": None, "coordinates": []}


def find_raster_files(raster_dir: str) -> Dict[str, str]:
    """Find raster files in directory."""
    raster_dir = Path(raster_dir)
    
    rasters = {}
    
    for name in ["cost", "slope", "ndvi", "elevation"]:
        for ext in [".tif", ".tiff"]:
            path = raster_dir / f"{name}{ext}"
            if path.exists():
                rasters[name] = str(path)
                break
    
    return rasters


def run_pipeline(
    config_path: Optional[str] = None,
    polygon_path: Optional[str] = None,
    raster_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    node_spacing: int = 10,
    subsample_3d: int = 2
) -> Dict[str, Any]:
    """Run the complete Routing 2.0 pipeline.
    
    Args:
        config_path: Path to config.json (optional)
        polygon_path: Path to polygon GeoJSON (optional)
        raster_dir: Directory containing cost.tif, slope.tif, ndvi.tif
        output_dir: Output directory for all generated files
        node_spacing: Spacing between graph nodes (in pixels)
        subsample_3d: Subsampling factor for 3D visualization
        
    Returns:
        Dictionary with all results and output paths
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("ROUTING 2.0 PIPELINE - Starting")
    logger.info("=" * 60)
    
    # Default paths
    if raster_dir is None:
        raster_dir = str(project_root / "out_demo_plan" / "rasters")
    if output_dir is None:
        output_dir = str(script_dir / "output")
    if config_path is None:
        config_path = str(project_root / "config.json")
    if polygon_path is None:
        polygon_path = str(project_root / "inputs" / "map.geojson")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "timestamp": start_time.isoformat(),
        "inputs": {
            "config": config_path,
            "polygon": polygon_path,
            "raster_dir": raster_dir,
            "output_dir": str(output_dir)
        },
        "outputs": {},
        "errors": []
    }
    
    # Step 1: Load configuration
    logger.info("\n[1/7] Loading configuration...")
    try:
        if Path(config_path).exists():
            config = load_config(config_path)
            results["config"] = config
            logger.info(f"  Loaded config: {config_path}")
        else:
            logger.warning(f"  Config not found: {config_path}")
            config = {}
    except Exception as e:
        logger.error(f"  Error loading config: {e}")
        config = {}
        results["errors"].append(f"Config load error: {e}")
    
    # Step 2: Load polygon
    logger.info("\n[2/7] Loading polygon data...")
    try:
        if Path(polygon_path).exists():
            polygon_data = load_polygon_bounds(polygon_path)
            results["polygon"] = polygon_data
            logger.info(f"  Loaded polygon: {polygon_data.get('name', 'Unknown')}")
            if polygon_data.get("bounds"):
                bounds = polygon_data["bounds"]
                logger.info(f"  Bounds: ({bounds['min_lon']:.4f}, {bounds['min_lat']:.4f}) to ({bounds['max_lon']:.4f}, {bounds['max_lat']:.4f})")
        else:
            logger.warning(f"  Polygon not found: {polygon_path}")
    except Exception as e:
        logger.error(f"  Error loading polygon: {e}")
        results["errors"].append(f"Polygon load error: {e}")
    
    # Find raster files
    rasters = find_raster_files(raster_dir)
    if "cost" not in rasters and "elevation" not in rasters:
        logger.info("[Auto-Gen] Rasters specific to this AOI not found. generating synthetic terrain data specific to these coordinates...")
        # Add local helper or direct logic
        try:
           from pipeline_full import generate_synthetic_terrain
           
           # Get bounds tuple
           poly_bounds = polygon_data["bounds"]
           bounds_tuple = (
               poly_bounds["min_lon"], 
               poly_bounds["min_lat"],
               poly_bounds["max_lon"],
               poly_bounds["max_lat"]
           )
           
           gen_out = Path(raster_dir)
           gen_out.mkdir(parents=True, exist_ok=True)
           
           gen_res = generate_synthetic_terrain(bounds_tuple, gen_out)
           logger.info(f"  Generated synthetic rasters in {raster_dir}")
           
           # Refresh find
           rasters = find_raster_files(raster_dir)
           
        except ImportError:
            logger.warning("Could not import generate_synthetic_terrain. Continuing with existing files if any.")
        except Exception as e:
             logger.error(f"Failed to generate terrain: {e}")
             
    if "cost" not in rasters:
        logger.error(f"  Cost raster not found in: {raster_dir}")
        results["errors"].append("Cost raster not found")
        return results
    
    logger.info(f"  Found rasters: {list(rasters.keys())}")
    results["rasters"] = rasters
    
    # Step 3: Build 3D model
    logger.info("\n[3/7] Building 3D cost terrain model...")
    try:
        model_output_file = output_dir / "3d_model" / "cost_terrain_3d.html"
        model_results = build_3d_model(
            cost_path=rasters["cost"],
            output_path=str(model_output_file),
            slope_path=rasters.get("slope"),
            ndvi_path=rasters.get("ndvi"),
            subsample=subsample_3d,
            use_plotly=True
        )
        results["model_results"] = model_results
        results["outputs"]["3d_model"] = model_results.get("html_3d") or model_results.get("png_3d")
        logger.info(f"  3D model saved to: {model_output_file}")
    except Exception as e:
        logger.error(f"  Error building 3D model: {e}")
        results["errors"].append(f"3D model error: {e}")
        model_results = None
    
    # Step 4: Build multi-dimensional graph
    logger.info("\n[4/7] Building multi-dimensional graph...")
    try:
        G, graph_meta = build_multidim_graph(
            cost_path=rasters["cost"],
            slope_path=rasters.get("slope"),
            ndvi_path=rasters.get("ndvi"),
            elevation_path=rasters.get("elevation"),
            node_spacing=node_spacing,
            connectivity=8,
            polygon_coords=polygon_data.get("coordinates")
        )
        
        # Save graph in multiple formats
        graph_output = output_dir / "graph"
        graph_output.mkdir(parents=True, exist_ok=True)
        
        graphml_path = save_graph(G, str(graph_output / "multidim_graph.graphml"), format="graphml")
        json_path = save_graph(G, str(graph_output / "multidim_graph.json"), format="json")
        
        results["graph_meta"] = graph_meta
        results["graph_stats"] = get_graph_statistics(G)
        results["outputs"]["graph_graphml"] = graphml_path
        results["outputs"]["graph_json"] = json_path
        
        logger.info(f"  Graph: {graph_meta['nodes']} nodes, {graph_meta['edges']} edges")
    except Exception as e:
        logger.error(f"  Error building graph: {e}")
        results["errors"].append(f"Graph building error: {e}")
        G = None
        graph_meta = None
    
    # Step 5: Analyze priorities
    logger.info("\n[5/7] Analyzing priorities...")
    try:
        priority_report = generate_priority_report(
            cost_path=rasters["cost"],
            slope_path=rasters.get("slope"),
            ndvi_path=rasters.get("ndvi")
        )
        results["priority_report"] = priority_report
        
        anchor = priority_report.get("priority_anchor", {})
        if anchor.get("found"):
            logger.info(f"  Priority anchor: ({anchor['row']}, {anchor['col']}) = {anchor['cost']:.6f}")
    except Exception as e:
        logger.error(f"  Error analyzing priorities: {e}")
        results["errors"].append(f"Priority analysis error: {e}")
        priority_report = None
    
    # Step 6: Optimize route and create visualizations
    logger.info("\n[6/7] Optimizing route and creating visualizations...")
    route_result = None
    strategy_comparison = None
    
    if G is not None:
        try:
            # Run route optimization
            route_result = optimize_route_demo(G)
            results["route_result"] = {k: v for k, v in route_result.items() if k != "path_details"}
            
            # Generate Drone Spiral
            logger.info("Generating drone spiral coverage...")
            spiral_path, _, spiral_stats = generate_spiral_path(G)
            results["spiral_route"] = {
                "path": spiral_path,
                "stats": spiral_stats
            }
            logger.info(f"  Spiral Route: {len(spiral_path)} waypoints")

            if "path" in route_result and len(route_result["path"]) > 1:
                logger.info(f"  Route: {len(route_result['path'])} nodes, cost={route_result['total_cost']:.4f}")
                
                # Compare strategies
                strategy_comparison = compare_weight_strategies(
                    G, route_result["start_node"], route_result["goal_node"]
                )
                results["strategy_comparison"] = strategy_comparison
            
            # Create visualizations
            viz_output = output_dir / "visualizations"
            viz_output.mkdir(parents=True, exist_ok=True)
            
            # Use Spiral path for visualization if available, else A*
            route_path = spiral_path if spiral_path else route_result.get("path", [])
            
            # 2D priority map with route
            try:
                map_path = visualize_2d_priority_map(
                    G, str(viz_output / "priority_map_2d.png"),
                    route_path=route_path
                )
                results["outputs"]["priority_map_2d"] = map_path
            except Exception as e:
                logger.warning(f"  Could not create 2D map: {e}")
            
            # Priority heatmap
            try:
                heatmap_path = create_priority_heatmap(
                    G, str(viz_output / "priority_heatmap.png")
                )
                results["outputs"]["priority_heatmap"] = heatmap_path
            except Exception as e:
                logger.warning(f"  Could not create heatmap: {e}")
            
            # 3D network visualization
            try:
                # Use altitude/elevation if available, otherwise cost
                z_attr = "altitude" if rasters.get("elevation") else "cost"
                network_path = visualize_3d_network(
                    G, str(viz_output / "network_3d.html"),
                    route_path=route_path,
                    z_attribute=z_attr
                )
                results["outputs"]["network_3d"] = network_path
            except ImportError:
                logger.warning("  Plotly not available for 3D network")
            except Exception as e:
                logger.warning(f"  Could not create 3D network: {e}")
            
            # Strategy comparison visualization
            if strategy_comparison and "strategies" in strategy_comparison:
                try:
                    # Get paths for each strategy
                    routes = {}
                    from route_optimizer import astar_multifactor
                    for name, data in strategy_comparison["strategies"].items():
                        path, _, _ = astar_multifactor(
                            G, route_result["start_node"], route_result["goal_node"],
                            data["weights"]
                        )
                        if path:
                            routes[name] = path
                    
                    if routes:
                        comparison_path = visualize_route_comparison(
                            G, routes, str(viz_output / "strategy_comparison.png")
                        )
                        results["outputs"]["strategy_comparison"] = comparison_path
                except Exception as e:
                    logger.warning(f"  Could not create comparison: {e}")
            
            logger.info(f"  Visualizations saved to: {viz_output}")
            
        except Exception as e:
            logger.error(f"  Error in optimization/visualization: {e}")
            results["errors"].append(f"Optimization error: {e}")
    
    # Step 7: Generate report
    logger.info("\n[7/7] Generating summary report...")
    try:
        report = generate_summary_report(
            model_results=model_results,
            graph_meta=graph_meta,
            priority_report=priority_report,
            route_result=route_result,
            strategy_comparison=strategy_comparison,
            output_paths=results.get("outputs", {})
        )
        
        report_paths = save_report(
            report,
            str(output_dir / "routing2_report.md"),
            also_save_json=True,
            report_data=results
        )
        results["outputs"]["report_md"] = report_paths.get("markdown")
        results["outputs"]["report_json"] = report_paths.get("json")
        
        logger.info(f"  Report saved to: {output_dir / 'routing2_report.md'}")
    except Exception as e:
        logger.error(f"  Error generating report: {e}")
        results["errors"].append(f"Report generation error: {e}")
    
    # Summary
    elapsed = datetime.now() - start_time
    results["elapsed_seconds"] = elapsed.total_seconds()
    
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Time elapsed: {elapsed}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Errors: {len(results.get('errors', []))}")
    
    if results.get("outputs"):
        logger.info("\nGenerated files:")
        for name, path in results["outputs"].items():
            if path:
                logger.info(f"  - {name}: {path}")
    
    return results


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Routing 2.0 - 3D Visualization and Multi-dimensional Graph Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use default paths
    python pipeline.py

    # Specify raster directory
    python pipeline.py --raster-dir out_demo_plan/rasters

    # Full custom paths
    python pipeline.py --config config.json --polygon inputs/map.geojson \\
                       --raster-dir out_demo_plan/rasters --output-dir output

    # Adjust processing parameters
    python pipeline.py --node-spacing 5 --subsample 1
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Path to config.json file",
        default=None
    )
    parser.add_argument(
        "--polygon", "-p",
        help="Path to polygon GeoJSON file",
        default=None
    )
    parser.add_argument(
        "--raster-dir", "-r",
        help="Directory containing cost.tif, slope.tif, ndvi.tif",
        default=None
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for generated files",
        default=None
    )
    parser.add_argument(
        "--node-spacing", "-n",
        type=int,
        help="Graph node spacing in pixels (default: 10)",
        default=10
    )
    parser.add_argument(
        "--subsample", "-s",
        type=int,
        help="3D model subsampling factor (default: 2)",
        default=2
    )
    
    args = parser.parse_args()
    
    results = run_pipeline(
        config_path=args.config,
        polygon_path=args.polygon,
        raster_dir=args.raster_dir,
        output_dir=args.output_dir,
        node_spacing=args.node_spacing,
        subsample_3d=args.subsample
    )
    
    # Exit with error code if there were errors
    if results.get("errors"):
        sys.exit(1)
    
    return results


if __name__ == "__main__":
    main()
