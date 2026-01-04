import os
import time
import json
import sys
import subprocess

# ensure repo root is importable for direct imports
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)

from frp.utils import ensure_dir


def run_cmd(py, argv):
    # run python -c with repo on sys.path so `from frp.cli import main` works
    repo = REPO_ROOT
    code = (
        "import sys; sys.path.insert(0, r'" + repo + "'); from frp.cli import main; sys.argv = "
        + repr(argv)
        + "; main()"
    )
    p = subprocess.run([py, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # forward logs for test visibility
    if p.stdout:
        print(p.stdout.decode(), end="")
    if p.stderr:
        print(p.stderr.decode(), end="", file=sys.stderr)
    return p.returncode


def test_demo_and_plan(tmp_path):
    py = sys.executable
    out_demo = str(tmp_path / "out_demo_2ha")
    out_plan = str(tmp_path / "out_demo_2ha_plan")

    # Run demo to create inputs
    ensure_dir(out_demo)
    rc = run_cmd(py, ['frp', 'demo', '--output-dir', out_demo])
    assert rc == 0

    # Run plan using the demo inputs and node-area-ha=2
    argv = [
        'frp', 'plan',
        '--aoi', os.path.join(out_demo, 'inputs', 'aoi.geojson'),
        '--nir', os.path.join(out_demo, 'inputs', 'nir.tif'),
        '--red', os.path.join(out_demo, 'inputs', 'red.tif'),
        '--resolution', '10',
        '--tile-size', '128',
        '--weights', 'slope=0.5,ndvi=0.5',
        '--node-area-ha', '2',
        '--max-waypoints', '200',
        '--output-dir', out_plan,
    ]

    t0 = time.time()
    rc = run_cmd(py, argv)
    elapsed = time.time() - t0
    # Log elapsed but don't fail on time
    print(f"plan elapsed: {elapsed:.2f}s")
    assert rc == 0

    # Assertions: files exist and are non-empty
    assert os.path.exists(os.path.join(out_plan, 'routes', 'route.geojson'))
    assert os.path.getsize(os.path.join(out_plan, 'routes', 'route.geojson')) > 20
    assert os.path.exists(os.path.join(out_plan, 'routes', 'route.kml'))
    assert os.path.exists(os.path.join(out_plan, 'report.json'))
    # rasters
    assert os.path.exists(os.path.join(out_plan, 'rasters', 'ndvi.tif'))
    assert os.path.exists(os.path.join(out_plan, 'rasters', 'cost.tif'))
