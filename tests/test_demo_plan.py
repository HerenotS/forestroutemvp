from pathlib import Path

from frp.utils import make_demo_data
from frp.aoi import load_aoi
from frp.cli import run_pipeline


def test_demo_then_plan(tmp_path):
    demo_out = tmp_path / "demo_out"
    plan_out = tmp_path / "plan_out"
    demo_out = str(demo_out)
    plan_out = str(plan_out)

    # Create demo inputs programmatically
    demo_paths = make_demo_data(demo_out)
    aoi_path = demo_paths["aoi"]
    nir_path = demo_paths["nir"]
    red_path = demo_paths["red"]

    assert Path(aoi_path).exists() and Path(aoi_path).stat().st_size > 0
    assert Path(nir_path).exists() and Path(nir_path).stat().st_size > 0
    assert Path(red_path).exists() and Path(red_path).stat().st_size > 0

    # Run plan using run_pipeline directly to avoid subprocess issues in CI
    aoi_geom = load_aoi(aoi_path, None)
    weights = {"slope": 0.5, "ndvi": 0.5}
    run_pipeline(
        aoi_geom,
        nir_path,
        red_path,
        None,
        10.0,
        512,
        weights,
        plan_out,
        run_astar=True,
        mode="plan",
        node_area_ha=2.0,
        time_limit_s=1.0,
        sweep_spacing_m=None,
        waypoint_spacing_m=10.0,
        simplify_m=0.0,
        geojson_geometry="linestring",
        max_waypoints=2000,
    )

    # Check expected outputs
    rasters = Path(plan_out) / "rasters"
    routes = Path(plan_out) / "routes"
    report = Path(plan_out) / "report.json"

    ndvi = rasters / "ndvi.tif"
    cost = rasters / "cost.tif"
    geojson = routes / "route.geojson"
    kml = routes / "route.kml"

    assert ndvi.exists() and ndvi.stat().st_size > 0
    assert cost.exists() and cost.stat().st_size > 0
    assert geojson.exists() and geojson.stat().st_size > 0
    assert kml.exists() and kml.stat().st_size > 0
    assert report.exists() and report.stat().st_size > 0
