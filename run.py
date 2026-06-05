"""
G42 Agentathon - Personal Finance Agent (Use Case 24)

MANDATORY entry point exposing POST /run on port 8000.

Endpoints:
    GET  /              Service info
    GET  /health        Health check
    POST /run           Main agent endpoint
    GET  /data-files    List current bank statement CSVs
    POST /upload-csv    Upload/replace a bank statement CSV
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from app.config import Config
from app.crew import run_crew
from app.models.schemas import RunRequest, RunResponse


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
log = logging.getLogger("g42-finance-agent")

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"
MAX_HISTORY = 25

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="G42 Agentathon - Personal Finance Agent",
    description=(
        "Use Case 24: Multi-agent personal finance assistant for UAE residents. "
        "Analyzes bank statements and answers real-life financial questions."
    ),
    version="0.1.0",
)

# CORS so the UI on port 8001 can call this API on port 8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "G42 Agentathon - Personal Finance Agent",
        "use_case_id": "24",
        "endpoints": ["POST /run", "GET /data-files", "POST /upload-csv"],
        "sample_mode": not Config.is_live(),
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "sample_mode": not Config.is_live()}


@app.post("/run", response_model=RunResponse)
async def run(request: RunRequest):
    log.info(f"Received query: {request.query[:100]}")
    try:
        ctx = request.context.model_dump() if request.context else None
        # Synchronous CrewAI workflow in a worker thread to avoid event-loop conflict
        result = await asyncio.to_thread(run_crew, request.query, ctx)

        return RunResponse(
            use_case_id="24",
            query=request.query,
            answer=result["answer"],
            agents_involved=result["agents_involved"],
            trace_path=result["trace_path"],
            elapsed_seconds=result["elapsed_seconds"],
            sample_mode=result["sample_mode"],
            findings=result["findings"],
            trace_events=result.get("trace_events", []),
        )
    except FileNotFoundError as exc:
        log.error(f"File not found: {exc}")
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        log.exception("Agent run failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(exc).__name__,
                "message": str(exc),
                "hint": "Check the trace file in /logs/ for the failure point.",
            },
        )


# ---------------------------------------------------------------------------
# Streaming run (NDJSON) - pushes each agent event live to the UI as it
# happens, instead of waiting for the full run to complete.
# Each line is one JSON object:
#   {"type": "event", "event": {...trace record...}}
#   {"type": "result", "data": {...full RunResponse payload...}}
#   {"type": "error",  "error": "...message..."}
# ---------------------------------------------------------------------------

@app.post("/run-stream")
async def run_stream(request: RunRequest):
    log.info(f"Received streaming query: {request.query[:100]}")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    SENTINEL = object()

    def on_event(record: dict) -> None:
        # Called from the worker thread. Hop back onto the event loop
        # to enqueue safely.
        loop.call_soon_threadsafe(queue.put_nowait,
                                  {"type": "event", "event": record})

    async def runner() -> None:
        try:
            ctx = request.context.model_dump() if request.context else None
            result = await asyncio.to_thread(
                run_crew, request.query, ctx, on_event,
            )
            payload = {
                "use_case_id": "24",
                "query": request.query,
                "answer": result["answer"],
                "agents_involved": result["agents_involved"],
                "trace_path": result["trace_path"],
                "elapsed_seconds": result["elapsed_seconds"],
                "sample_mode": result["sample_mode"],
                "findings": result["findings"],
                "trace_events": result.get("trace_events", []),
            }
            await queue.put({"type": "result", "data": payload})
        except FileNotFoundError as exc:
            await queue.put({"type": "error", "error": f"FileNotFound: {exc}"})
        except Exception as exc:  # noqa: BLE001
            log.exception("Streaming agent run failed")
            await queue.put({
                "type": "error",
                "error": f"{type(exc).__name__}: {exc}",
            })
        finally:
            await queue.put(SENTINEL)

    asyncio.create_task(runner())

    async def ndjson_stream():
        while True:
            item = await queue.get()
            if item is SENTINEL:
                break
            yield json.dumps(item, default=str) + "\n"

    return StreamingResponse(
        ndjson_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable proxy buffering
        },
    )


# ---------------------------------------------------------------------------
# Data file management (NEW)
# ---------------------------------------------------------------------------

@app.get("/data-files")
async def list_data_files():
    """List the CSV bank statement files currently in data/."""
    if not DATA_DIR.exists():
        return {"files": []}

    files = []
    for csv in sorted(DATA_DIR.glob("*.csv")):
        stat = csv.stat()
        kind = "credit_card" if ("CreditCard" in csv.name or "Credit_Card" in csv.name) \
               else "savings"
        files.append({
            "name": csv.name,
            "kind": kind,
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified_ts": stat.st_mtime,
        })
    return {"files": files, "data_dir": str(DATA_DIR)}


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload/replace a bank statement CSV. Saves to data/ using the original
    filename (so re-uploading 'ADCB_Savings_KarimMansour.csv' overwrites it).

    The frontend should send via multipart/form-data with field name 'file'.
    """
    # Basic validation
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")

    # Read content
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:   # 5 MB limit
        raise HTTPException(413, "File too large (max 5 MB)")
    if len(content) < 50:
        raise HTTPException(400, "File appears empty")

    # Save (sanitize filename - keep only the name part, no paths)
    safe_name = Path(file.filename).name
    target = DATA_DIR / safe_name
    DATA_DIR.mkdir(exist_ok=True)
    target.write_bytes(content)

    log.info(f"Uploaded CSV: {safe_name} ({len(content)} bytes)")
    return {
        "ok": True,
        "saved_as": safe_name,
        "size_bytes": len(content),
        "size_kb": round(len(content) / 1024, 1),
        "path": str(target.relative_to(PROJECT_ROOT)),
    }


# ---------------------------------------------------------------------------
# Question history (NEW) - stored in data/history.json
# ---------------------------------------------------------------------------

def _load_history() -> list:
    """Load history entries from data/history.json. Returns [] if missing or bad."""
    if not HISTORY_FILE.exists():
        return []
    try:
        content = HISTORY_FILE.read_text(encoding="utf-8")
        if not content.strip():
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        log.warning(f"Could not parse history file: {exc}")
        return []


def _save_history(entries: list) -> None:
    """Atomically write history to disk (write-temp-then-rename)."""
    DATA_DIR.mkdir(exist_ok=True)
    tmp = HISTORY_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    tmp.replace(HISTORY_FILE)


@app.get("/history")
async def get_history():
    """List question history (newest first)."""
    entries = _load_history()
    return {
        "entries": entries,
        "count": len(entries),
        "file": str(HISTORY_FILE.relative_to(PROJECT_ROOT)),
        "max_entries": MAX_HISTORY,
    }


@app.post("/history")
async def add_history(entry: dict = Body(...)):
    """
    Append a new entry to question history. Auto-fills id + timestamp if missing.
    Caps at MAX_HISTORY (newest kept).
    """
    if not isinstance(entry, dict) or "query" not in entry:
        raise HTTPException(400, "Entry must be a dict with at least a 'query' field")

    entry.setdefault("id", f"h_{uuid.uuid4().hex[:8]}")
    entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    entries = _load_history()
    entries.insert(0, entry)           # newest first
    entries = entries[:MAX_HISTORY]    # cap
    _save_history(entries)

    log.info(f"Saved history entry: {entry['id']} ({entry['query'][:60]})")
    return {"ok": True, "saved_id": entry["id"], "count": len(entries), "entries": entries}


@app.delete("/history")
async def clear_history():
    """Clear all question history."""
    _save_history([])
    log.info("Cleared question history")
    return {"ok": True, "cleared": True}


# ---------------------------------------------------------------------------
# Voice transcription (Compass Whisper) - accepts WAV from browser
# ---------------------------------------------------------------------------

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe an audio file via Compass Whisper.
    Frontend should send a WAV file (browser converts mic → WAV via Web Audio API).
    """
    if not Config.is_live():
        raise HTTPException(
            503,
            "Voice transcription requires Compass API key. Set OPENAI_API_KEY and "
            "SAMPLE_MODE=false in .env."
        )

    if not file.filename:
        raise HTTPException(400, "No audio file provided")

    audio_bytes = await file.read()
    if len(audio_bytes) < 500:
        raise HTTPException(400, "Audio too short or empty")
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio file too large (max 25 MB)")

    # Determine suffix (default wav since frontend sends wav)
    suffix = ".wav"
    name_lower = (file.filename or "").lower()
    for ext in (".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg"):
        if name_lower.endswith(ext):
            suffix = ext
            break

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        from openai import OpenAI
        client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL,
        )
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper",
                file=audio_file,
            )

        text = (transcript.text if hasattr(transcript, "text") else str(transcript)).strip()
        log.info(f"Transcribed audio ({len(audio_bytes)} bytes) -> {len(text)} chars: {text[:80]}")
        return {
            "ok": True,
            "text": text,
            "audio_bytes": len(audio_bytes),
            "model": "whisper",
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Transcription failed")
        raise HTTPException(500, f"Transcription failed: {type(exc).__name__}: {exc}")
    finally:
        if tmp_path:
            try: os.unlink(tmp_path)
            except OSError: pass


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info(f"Starting on port 8000. Sample mode: {not Config.is_live()}")
    if not Config.is_live():
        log.warning(
            "Running in SAMPLE_MODE - LLM calls are mocked. "
            "Set OPENAI_API_KEY (Compass) and SAMPLE_MODE=false in .env to use real LLMs."
        )
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=Config.LOG_LEVEL.lower(),
    )