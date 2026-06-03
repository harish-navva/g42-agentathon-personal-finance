# G42 Agentathon - Local Docker Build Verification
# Runs the exact steps the hackathon evaluator will run.
# Reports pass/fail for each step.

param(
    [string]$ImageTag = "g42-personal-finance-agent",
    [int]$Port = 8000,
    [int]$WaitSeconds = 30
)

$ErrorActionPreference = "Stop"
$failed = 0

function Step($label) { Write-Host ""; Write-Host "===> $label" -ForegroundColor Cyan }
function Pass($msg)   { Write-Host "  [+] $msg" -ForegroundColor Green }
function Fail($msg)   { Write-Host "  [X] $msg" -ForegroundColor Red; $script:failed++ }

# 0. Verify Docker is available
Step "0. Docker availability"
try {
    $dockerVersion = docker --version
    Pass $dockerVersion
} catch {
    Fail "Docker not installed or not in PATH"
    exit 1
}

# 1. Build the image
Step "1. docker build"
$buildStart = Get-Date
try {
    docker build -t $ImageTag . | Out-Host
    $buildSec = [math]::Round(((Get-Date) - $buildStart).TotalSeconds, 1)
    Pass "Build succeeded in ${buildSec}s"
} catch {
    Fail "Build failed: $($_.Exception.Message)"
    exit 1
}

# 2. Check image size (large = bad, > 2 GB = a red flag)
Step "2. Image size sanity check"
$size = docker image inspect $ImageTag --format '{{.Size}}' | ForEach-Object { [math]::Round($_ / 1MB, 1) }
if ($size -gt 2048) {
    Fail "Image is ${size} MB — investigate bloat"
} else {
    Pass "Image size: ${size} MB"
}

# 3. Run container in sample-mode (no real Compass key required for verification)
Step "3. docker run (SAMPLE_MODE=true for verification)"
$containerName = "$ImageTag-test-$(Get-Random -Maximum 9999)"
try {
    docker run --rm -d --name $containerName `
        -p ${Port}:${Port} `
        -e SAMPLE_MODE=true `
        $ImageTag | Out-Null
    Pass "Container started: $containerName"
} catch {
    Fail "Container failed to start: $($_.Exception.Message)"
    exit 1
}

# 4. Wait for healthcheck
Step "4. Wait for API to be ready (up to ${WaitSeconds}s)"
$ready = $false
for ($i = 1; $i -le $WaitSeconds; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:${Port}/health" -TimeoutSec 2 -UseBasicParsing
        if ($resp.status -eq "ok") {
            $ready = $true
            Pass "API ready after ${i}s. /health -> status=$($resp.status), sample_mode=$($resp.sample_mode)"
            break
        }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) { Fail "API never returned 200 OK on /health within ${WaitSeconds}s" }

# 5. Test POST /run
Step "5. POST /run with example_1.json"
try {
    $body = Get-Content -Raw .\input_examples\example_1.json
    $t0 = Get-Date
    $resp = Invoke-RestMethod -Uri "http://localhost:${Port}/run" `
        -Method Post -Body $body -ContentType "application/json" `
        -TimeoutSec 600 -UseBasicParsing
    $elapsed = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    Pass "POST /run returned 200 in ${elapsed}s"
    Pass "  agents involved: $($resp.agents_involved -join ', ')"
    Pass "  trace events: $($resp.trace_events.Count)"
    Pass "  use_case_id: $($resp.use_case_id)"
} catch {
    Fail "POST /run failed: $($_.Exception.Message)"
}

# 6. Cleanup
Step "6. Cleanup"
docker stop $containerName 2>$null | Out-Null
Pass "Container stopped"

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor White
if ($failed -eq 0) {
    Write-Host "  ALL DOCKER TESTS PASSED — NO DQ RISK" -ForegroundColor Green
} else {
    Write-Host "  $failed CHECK(S) FAILED — FIX BEFORE SUBMIT" -ForegroundColor Red
}
Write-Host "==========================================" -ForegroundColor White
