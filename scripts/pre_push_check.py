"""
G42 Agentathon - Pre-Push GitHub Safety Check
Runs 8 safety checks before you push to GitHub.

Usage (from project root):
    python scripts/pre_push_check.py
"""
import json
import re
import sys
from pathlib import Path

failed = 0

def step(t):  print(f"\n===> {t}")
def passing(m):  print(f"  [+] {m}")
def warn(m):  print(f"  [!] {m}")
def fail(m):
    global failed
    print(f"  [X] {m}")
    failed += 1


# --------------------------------------------------------------------
# 1. Mandatory files & folders exist
# --------------------------------------------------------------------
step("1. Mandatory files & folders exist")
files = ["run.py", "requirements.txt", "Dockerfile", ".env.example",
         "metadata.json", "README.md", "docs/architecture.md",
         ".gitignore", ".dockerignore"]
for f in files:
    if Path(f).exists(): passing(f)
    else: fail(f"MISSING: {f}")

folders = ["app", "input_examples", "output_examples", "logs", "scripts", "data"]
for d in folders:
    p = Path(d)
    if p.exists():
        n = len(list(p.iterdir()))
        passing(f"{d}/ ({n} items)")
    else:
        fail(f"MISSING: {d}/")


# --------------------------------------------------------------------
# 2. 3 input + 3 output examples
# --------------------------------------------------------------------
step("2. Sample inputs and outputs (3 each required)")
inputs  = sorted(Path("input_examples").glob("example_*.json")) if Path("input_examples").exists() else []
outputs = sorted(Path("output_examples").glob("example_*_output.json")) if Path("output_examples").exists() else []
if len(inputs)  >= 3: passing(f"{len(inputs)} input examples")
else: fail(f"Need 3 input examples (have {len(inputs)})")
if len(outputs) >= 3: passing(f"{len(outputs)} output examples")
else: fail(f"Need 3 output examples (have {len(outputs)})")


# --------------------------------------------------------------------
# 3. SECRETS scan
# --------------------------------------------------------------------
step("3. SECRETS scan - must find nothing")

# Patterns to flag
PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "OpenAI/Compass-style API key (sk-...)"),
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-]{30,}"), "Bearer token"),
    (re.compile(r"""(?i)api[_-]?key\s*[=:]\s*['"][A-Za-z0-9_\-]{20,}['"]"""), "API key assignment"),
    (re.compile(r"BEGIN\s+RSA\s+PRIVATE\s+KEY"), "RSA private key"),
    (re.compile(r"BEGIN\s+OPENSSH\s+PRIVATE\s+KEY"), "SSH private key"),
    (re.compile(r"-----BEGIN\s+CERTIFICATE-----"), "Certificate"),
]

# File extensions to scan
EXTS = {".py", ".json", ".md", ".txt", ".yml", ".yaml", ".ps1", ".sh",
        ".example", ".html", ".css", ".js", ".toml", ".ini", ".env"}

# Folders to skip
SKIP = {".venv", "venv", "env", ".git", "__pycache__", "node_modules"}

# Files to skip (binary / generated)
SKIP_FILES = {"test.wav", "package-lock.json"}

hits = []
for path in Path(".").rglob("*"):
    if not path.is_file(): continue
    if any(part in SKIP for part in path.parts): continue
    if path.name in SKIP_FILES: continue
    if path.suffix not in EXTS and path.name not in {"Dockerfile", ".env.example", ".gitignore", ".dockerignore"}:
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for lineno, line in enumerate(text.splitlines(), 1):
        for pat, label in PATTERNS:
            if pat.search(line):
                # Truncate the line for display
                snippet = line.strip()[:80]
                hits.append((str(path), lineno, label, snippet))

if hits:
    fail("Possible secrets found:")
    for p, ln, lbl, snip in hits[:10]:
        print(f"      {p}:{ln} ({lbl})")
        print(f"        {snip}")
    if len(hits) > 10:
        print(f"      ... and {len(hits) - 10} more")
else:
    passing("No exposed secrets")


# --------------------------------------------------------------------
# 4. .env / .gitignore protection
# --------------------------------------------------------------------
step("4. .env / .gitignore protection")
env_path = Path(".env")
gitignore_text = Path(".gitignore").read_text(encoding="utf-8") if Path(".gitignore").exists() else ""
dockerignore_text = Path(".dockerignore").read_text(encoding="utf-8") if Path(".dockerignore").exists() else ""

if env_path.exists():
    passing(".env file exists locally (good - your working key)")
    if re.search(r"^\.env\s*$", gitignore_text, re.MULTILINE):
        passing(".env is in .gitignore (will NOT be pushed)")
    else:
        fail(".env exists but is NOT in .gitignore - IT WILL BE PUSHED")
else:
    warn(".env not found locally (you'll need to recreate to run)")

if re.search(r"^\.env\s*$", gitignore_text, re.MULTILINE):
    passing(".gitignore covers .env")
if re.search(r"^\.env", dockerignore_text, re.MULTILINE):
    passing(".dockerignore covers .env")


# --------------------------------------------------------------------
# 5. README has 18 required sections
# --------------------------------------------------------------------
step("5. README has 18 required sections")
required = [
    "## 1. Problem Statement",
    "## 2. Use Case ID",
    "## 3. Solution Overview",
    "## 4. Agent Architecture",
    "## 5. Agent Collaboration Flow",
    "## 6. Tools, Frameworks, and Models Used",
    "## 7. Data Sources",
    "## 8. Repository Structure",
    "## 9. Environment Variables",
    "## 10. Setup Instructions",
    "## 11. How to Run Locally",
    "## 12. How to Run with Docker",
    "## 13. API Usage",
    "## 14. Input and Output Examples",
    "## 15. Logs and Traces",
    "## 16. Demo Video",
    "## 17. Known Limitations",
    "## 18. Future Improvements",
]
readme = Path("README.md").read_text(encoding="utf-8") if Path("README.md").exists() else ""
missing = [r for r in required if r not in readme]
if not missing:
    passing("All 18 required sections present")
else:
    fail(f"Missing {len(missing)} required section(s):")
    for m in missing: print(f"      {m}")


# --------------------------------------------------------------------
# 6. metadata.json valid + has required fields
# --------------------------------------------------------------------
step("6. metadata.json is valid + has required fields")
try:
    meta = json.loads(Path("metadata.json").read_text(encoding="utf-8"))
    passing("Valid JSON")
    if meta.get("use_case_id"):
        passing(f"use_case_id = {meta['use_case_id']}")
    else:
        fail("use_case_id missing")
    if meta.get("agents") and len(meta["agents"]) >= 2:
        passing(f"{len(meta['agents'])} agents declared")
    else:
        fail("Need >= 2 agents")
    if meta.get("tools_used"):
        passing("tools_used present")
    else:
        fail("tools_used missing")
except Exception as exc:
    fail(f"metadata.json invalid: {exc}")


# --------------------------------------------------------------------
# 7. run.py binds 0.0.0.0:8000 + has POST /run
# --------------------------------------------------------------------
step("7. run.py binds to 0.0.0.0:8000 + has POST /run")
runpy = Path("run.py").read_text(encoding="utf-8")
if '"0.0.0.0"' in runpy: passing("Binds to 0.0.0.0")
else: fail("Does NOT bind 0.0.0.0")
if re.search(r"port\s*=\s*8000", runpy): passing("Uses port 8000")
else: fail("Not on port 8000")
if '@app.post("/run"' in runpy: passing("POST /run defined")
else: fail("POST /run NOT defined")


# --------------------------------------------------------------------
# 8. Repo size sanity
# --------------------------------------------------------------------
step("8. Repository size sanity")
total = 0
for f in Path(".").rglob("*"):
    if not f.is_file(): continue
    if any(part in SKIP for part in f.parts): continue
    try: total += f.stat().st_size
    except: pass
total_mb = total / (1024 * 1024)
passing(f"Repo size: {total_mb:.2f} MB (limit: well under 500 MB)")


# --------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------
print()
print("=" * 50)
if failed == 0:
    print("  ALL CHECKS PASSED - SAFE TO PUSH")
else:
    print(f"  {failed} CHECK(S) FAILED - FIX BEFORE PUSH")
print("=" * 50)
sys.exit(0 if failed == 0 else 1)