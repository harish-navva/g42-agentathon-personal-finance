# G42 Agentathon - Pre-Push GitHub Safety Check
# Run this BEFORE the first git push. Fails fast if anything looks risky.

$failed = 0
function Step($t)  { Write-Host ""; Write-Host "===> $t" -ForegroundColor Cyan }
function Pass($m)  { Write-Host "  [+] $m" -ForegroundColor Green }
function Warn($m)  { Write-Host "  [!] $m" -ForegroundColor Yellow }
function Fail($m)  { Write-Host "  [X] $m" -ForegroundColor Red; $script:failed++ }

Step "1. Mandatory files & folders exist"
$files = @("run.py","requirements.txt","Dockerfile",".env.example","metadata.json","README.md","docs\architecture.md",".gitignore",".dockerignore")
foreach ($f in $files) { if (Test-Path $f) { Pass $f } else { Fail "MISSING: $f" } }

$folders = @("app","input_examples","output_examples","logs","scripts","data")
foreach ($d in $folders) {
    if (Test-Path $d) {
        $n = (Get-ChildItem $d -Force | Measure-Object).Count
        Pass "$d/ ($n items)"
    } else { Fail "MISSING: $d/" }
}

Step "2. Sample inputs and outputs (3 each required)"
$inp = (Get-ChildItem "input_examples\example_*.json" -ErrorAction SilentlyContinue | Measure-Object).Count
$out = (Get-ChildItem "output_examples\example_*_output.json" -ErrorAction SilentlyContinue | Measure-Object).Count
if ($inp -ge 3) { Pass "$inp input examples" } else { Fail "Need 3 input examples (have $inp)" }
if ($out -ge 3) { Pass "$out output examples" } else { Fail "Need 3 output examples (have $out)" }

Step "3. SECRETS scan — must find nothing"
# Look for API keys, tokens, etc. in tracked files only (skip .git, .venv)
$pattern = '(sk-[A-Za-z0-9_\-]{20,}|Bearer\s+[A-Za-z0-9_\-]{20,}|api[_-]?key\s*[=:]\s*["\047][A-Za-z0-9_\-]{20,}["\047]|BEGIN\s+RSA\s+PRIVATE\s+KEY|BEGIN\s+OPENSSH\s+PRIVATE\s+KEY)'
$exts = '*.py','*.json','*.md','*.txt','*.yml','*.yaml','*.ps1','*.sh','Dockerfile','*.example','*.html','*.css','*.js','*.toml','*.ini','*.env'
$hits = Get-ChildItem -Recurse -Include $exts -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\\.venv\\|\\node_modules\\|\\\.git\\|\\__pycache__\\|test\.wav$' } |
        Select-String -Pattern $pattern -ErrorAction SilentlyContinue
if ($hits) {
    Fail "Possible secrets found:"
    $hits | ForEach-Object { Write-Host "      $($_.Path):$($_.LineNumber) -> $($_.Line.Trim().Substring(0,[Math]::Min(80,$_.Line.Trim().Length)))..." -ForegroundColor Red }
} else { Pass "No exposed secrets" }

Step "4. .env / .gitignore protection"
if (Test-Path .env) {
    Pass ".env file exists locally (good - your working key)"
    if (Select-String -Path .gitignore -Pattern "^\.env\s*$" -Quiet) {
        Pass ".env is in .gitignore (will NOT be pushed)"
    } else { Fail ".env exists but is NOT in .gitignore — IT WILL BE PUSHED" }
} else { Warn ".env not found locally (will need to recreate to run)" }

if (Select-String -Path .gitignore -Pattern "^\.env\s*$" -Quiet) { Pass ".gitignore covers .env" }
if (Test-Path .dockerignore) {
    if (Select-String -Path .dockerignore -Pattern "^\.env" -Quiet) { Pass ".dockerignore covers .env" }
}

Step "5. README has 18 required sections"
$required = @("## 1. Problem Statement","## 2. Use Case ID","## 3. Solution Overview","## 4. Agent Architecture",
              "## 5. Agent Collaboration Flow","## 6. Tools, Frameworks, and Models Used","## 7. Data Sources",
              "## 8. Repository Structure","## 9. Environment Variables","## 10. Setup Instructions",
              "## 11. How to Run Locally","## 12. How to Run with Docker","## 13. API Usage",
              "## 14. Input and Output Examples","## 15. Logs and Traces","## 16. Demo Video",
              "## 17. Known Limitations","## 18. Future Improvements")
$readme = Get-Content README.md -Raw
$missing = $required | Where-Object { -not ($readme -like "*$_*") }
if ($missing.Count -eq 0) { Pass "All 18 required sections present" }
else {
    Fail "Missing $($missing.Count) required sections:"
    $missing | ForEach-Object { Write-Host "      $_" -ForegroundColor Red }
}

Step "6. metadata.json is valid + has required fields"
try {
    $meta = Get-Content metadata.json -Raw | ConvertFrom-Json
    Pass "Valid JSON"
    if ($meta.use_case_id) { Pass "use_case_id = $($meta.use_case_id)" } else { Fail "use_case_id missing" }
    if ($meta.agents -and $meta.agents.Count -ge 2) { Pass "$($meta.agents.Count) agents declared" } else { Fail "Need >= 2 agents" }
    if ($meta.tools_used) { Pass "tools_used present" } else { Fail "tools_used missing" }
} catch { Fail "metadata.json invalid: $($_.Exception.Message)" }

Step "7. run.py binds to 0.0.0.0:8000 + has POST /run"
$runpy = Get-Content run.py -Raw
if ($runpy -match '"0\.0\.0\.0"') { Pass "Binds to 0.0.0.0" } else { Fail "Does NOT bind 0.0.0.0" }
if ($runpy -match 'port\s*=\s*8000') { Pass "Uses port 8000" } else { Fail "Not on port 8000" }
if ($runpy -match '@app\.post\("/run"') { Pass "POST /run defined" } else { Fail "POST /run NOT defined" }

Step "8. Repository size sanity"
$total = (Get-ChildItem -Recurse -File -Force | Where-Object { $_.FullName -notmatch '\\\.git\\|\\\.venv\\|\\__pycache__\\' } | Measure-Object Length -Sum).Sum / 1MB
Pass "Repo size: $([math]::Round($total,2)) MB (limit: well under 500 MB)"

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor White
if ($failed -eq 0) {
    Write-Host "  ALL CHECKS PASSED — SAFE TO PUSH" -ForegroundColor Green
} else {
    Write-Host "  $failed CHECK(S) FAILED — FIX BEFORE PUSH" -ForegroundColor Red
}
Write-Host "==========================================" -ForegroundColor White
