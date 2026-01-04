# PowerShell smoke test for Forestroute Planner
# Usage: .\smoketest.ps1

Write-Host "=== Forestroute Planner Smoke Test ===" -ForegroundColor Cyan

# 1. Run pytest
Write-Host "`n[1/4] Running pytest..." -ForegroundColor Yellow
python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: pytest did not pass" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: pytest" -ForegroundColor Green

# 2. Test demo command
Write-Host "`n[2/4] Testing demo command..." -ForegroundColor Yellow
python -m frp demo --output-dir smoketest_demo | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: demo command" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "smoketest_demo/routes/route.geojson")) {
    Write-Host "FAILED: demo did not create route.geojson" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: demo command" -ForegroundColor Green

# 3. Test plan command
Write-Host "`n[3/4] Testing plan command with --node-area-ha..." -ForegroundColor Yellow
python -m frp plan `
  --aoi smoketest_demo/inputs/aoi.geojson `
  --nir smoketest_demo/inputs/nir.tif `
  --red smoketest_demo/inputs/red.tif `
  --resolution 10 `
  --tile-size 128 `
  --weights "slope=0.5,ndvi=0.5" `
  --node-area-ha 2 `
  --max-waypoints 200 `
  --output-dir smoketest_plan | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: plan command" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "smoketest_plan/routes/route.geojson")) {
    Write-Host "FAILED: plan did not create route.geojson" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: plan command" -ForegroundColor Green

# 4. Test graph script
Write-Host "`n[4/4] Testing graph scripts..." -ForegroundColor Yellow
python scripts/build_route_graph.py --route smoketest_demo/routes/route.geojson --out smoketest_graphs | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: build_route_graph.py" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "smoketest_graphs/route_graph.graphml")) {
    Write-Host "FAILED: build_route_graph did not create graphml" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: graph scripts" -ForegroundColor Green

# Cleanup
Write-Host "`n[Cleanup] Removing test outputs..." -ForegroundColor Yellow
Remove-Item -Recurse -Force smoketest_demo, smoketest_plan, smoketest_graphs -ErrorAction SilentlyContinue

Write-Host "`n=== ALL TESTS PASSED ===" -ForegroundColor Green
exit 0
