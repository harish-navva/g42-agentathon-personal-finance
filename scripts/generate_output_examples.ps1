# Run all input_examples/*.json against the /run endpoint and save outputs.
# Usage: From project root, with backend running on port 8000:
#   .\scripts\generate_output_examples.ps1

$ErrorActionPreference = "Stop"
$apiUrl = "http://localhost:8000/run"
$inputDir = ".\input_examples"
$outputDir = ".\output_examples"

# Verify backend is up
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "[+] Backend healthy. Sample mode: $($health.sample_mode)" -ForegroundColor Green
} catch {
    Write-Host "[X] Backend not reachable at localhost:8000. Start it first: python run.py" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

$files = Get-ChildItem -Path $inputDir -Filter "example_*.json" | Sort-Object Name
Write-Host "[+] Found $($files.Count) input examples"
Write-Host ""

foreach ($f in $files) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $outFile = Join-Path $outputDir "$($base)_output.json"

    Write-Host "===> $($f.Name)" -ForegroundColor Cyan
    $body = Get-Content $f.FullName -Raw

    try {
        $t0 = Get-Date
        $resp = Invoke-RestMethod -Uri $apiUrl -Method Post -Body $body `
            -ContentType "application/json" -UseBasicParsing -TimeoutSec 600
        $elapsed = ((Get-Date) - $t0).TotalSeconds

        $resp | ConvertTo-Json -Depth 30 | Out-File -FilePath $outFile -Encoding UTF8
        Write-Host "     OK in ${elapsed}s -> $outFile" -ForegroundColor Green
        Write-Host "     agents: $($resp.agents_involved -join ', ')"
        Write-Host "     events: $($resp.trace_events.Count), mode: $(if ($resp.sample_mode) { 'Sample' } else { 'Compass' })"
    } catch {
        Write-Host "     [X] Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "[+] Done. Output files:" -ForegroundColor Green
Get-ChildItem $outputDir -Filter "*.json" | ForEach-Object { Write-Host "    $($_.FullName)" }