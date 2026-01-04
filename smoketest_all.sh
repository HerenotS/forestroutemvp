# pytest cache directory #

This directory contains data from the pytest's cache plugin,
which provides the `--lf` and `--ff` options, as well as the `cache` fixture.

**Do not** commit this to version control.

See [the docs](https://docs.pytest.org/en/stable/how-to/cache.html) for more information.

Graph

Build a coarse AOI graph (nodes ~ 2 ha):
python -m frp graph --aoi inputs/aoi.geojson --node-area-ha 2 --out out_graph --show

Outputs:
- out_graph/aoi_graph.graphml
- out_graph/nodes.geojson
- out_graph/edges.geojson

### Smoketest

Quick local smoke test (run from repository root).

- macOS / Linux:
  $ ./smoketest.sh

- Windows PowerShell:
  PS> .\smoketest.ps1

What the scripts do (summary):
1. Create a virtual environment (.venv).
2. Install requirements-dev.txt or requirements.txt if present.
3. Run pytest (if configured).
4. Try importing common package names and print results.
5. Exit with non-zero code only on clear failures (so you can inspect logs).

If you prefer to run commands manually, a minimal sequence:
$ python3 -m venv .venv
$ source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
$ pip install --upgrade pip
$ if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; elif [ -f requirements.txt ]; then pip install -r requirements.txt; fi
$ python -m pytest -q || echo "pytest failed or no tests"
$ python -c "import importlib,sys; candidates=['frp','forestroutemvp','forest_route_mvp']; \
for n in candidates: \
 try: importlib.import_module(n); print(n+' import OK'); break \
 except Exception as e: print(n+' import failed:', e, file=sys.stderr)"

### Smoketest every file

Run a repository-wide quick-check that performs lightweight, non-destructive checks per file type:

- POSIX/macOS/Linux:
  $ ./smoketest_all.sh

- Windows PowerShell:
  PS> .\smoketest_all.ps1

The scripts try py_compile for .py, JSON parsing for .json, YAML parsing if PyYAML is available, and a UTF-8 read for common text files. They skip binary or unsupported types and report failures at the end.

### smoketest_all.sh

Create the full-file smoketest script in repo root.