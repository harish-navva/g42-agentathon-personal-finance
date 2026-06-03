# Karim's Money — Personal Finance Agent

**G42 Agentathon · Use Case 24 · Personal Finance**
**Region:** UAE · **Currency:** AED · **Difficulty:** Medium

A multi-agent AI assistant that helps UAE residents make smarter financial decisions by analyzing their actual bank statements and answering real-life money questions.

---

## 1. Problem Statement

UAE residents — particularly the ~88% who are expats — face concentrated financial pressure that off-the-shelf budgeting apps do not address:

- **Visa dependency**: job loss triggers a 30-day visa cancellation window, making emergency runway a survival metric, not a vanity metric.
- **Heterogeneous cost structure**: high rent (25-40% of income), school fees, family remittance, vehicle financing, 8-12 active subscriptions per household.
- **Sharia-compliance optionality**: meaningful share of users need investment guidance respecting faith-based constraints.
- **Generic robo-advisors give wrong advice**: an Egyptian father of one in Dubai has structurally different risk tolerance than the same person in London. Standard 60/40 portfolios ignore the visa-runway constraint entirely.

The persona is **Karim Mansour**, 36, Egyptian expat in Dubai, married with one child, ADCB customer earning AED 22,556/month. His data is synthetic but representative.

## 2. Use Case ID

**Use Case 24 — Personal Finance**

From the official list of 25 G42 Agentathon problem statements.

## 3. Solution Overview

A 5-agent system that collaborates **non-linearly** to answer three categories of question:

1. **Goal feasibility** — *"Can I afford X in Y months?"*
2. **Timing & budgeting** — *"When and how should I do X?"*
3. **Optimization** — *"Where can I cut without hurting my family's lifestyle?"*

The system reads ADCB CSV bank statements, computes a real financial summary, builds a risk profile (including expat visa-runway risk), drafts a plan, has the plan critiqued by a separate agent, revises it, picks UAE-specific investment products, and produces a SCA-compliant final answer with disclaimers.

A live UI shows the agent activity in real time, including the critique → revision → approval loop between the Risk Profiler and Goal Planner.

## 4. Agent Architecture

| Agent | Compass Model | Responsibility |
|---|---|---|
| **Expense Analyzer** | `gpt-4.1` | Parses ADCB CSVs, categorizes spend by merchant rules, computes monthly financial summary |
| **Risk Profiler** | `gpt-5.1` | Builds risk band from income stability + dependents + buffer; critiques aggressive plans; flags expat visa-runway risk |
| **Goal Planner** | `gpt-5.1` | Classifies user query type; drafts a costed plan; revises in response to Risk Profiler's critique |
| **Investment Advisor** | `gpt-4.1` | Matches risk band to UAE products including Sharia-compliant options (ADCB Active Saver, DIB Sukuk, Sarwa) |
| **Compliance Recommender** | `gpt-5.1` | Synthesizes final user-facing answer; enforces SCA disclaimer; veto authority over plans breaching emergency-fund minimums |

See `docs/architecture.md` for the full Mermaid diagram and detailed phase breakdown.

## 5. Agent Collaboration Flow

The system is **not a linear pipeline**. The critical loop is between **Goal Planner** and **Risk Profiler**:

1. **Phase 1 (parallel)**: Expense Analyzer + Risk Profiler each read their data, compute independent findings, write to shared blackboard.
2. **Phase 2 (critique loop)**: Goal Planner drafts a plan. Risk Profiler critiques it against 3 concrete checks (buffer drop, debt-to-income, ignored fixed costs). If `REVISE`, the Goal Planner produces a revised plan; the cycle repeats up to 2 times until `APPROVED`.
3. **Phase 3 (conditional)**: Investment Advisor activates only when the plan involves capital deployment (not for pure cost-cutting queries).
4. **Phase 4 (veto)**: Compliance Recommender synthesizes the final answer and can veto plans that breach emergency-fund minimums.

All events are logged to `logs/<run_id>.jsonl`. The trace explicitly shows `action: "critique"` → `action: "plan_revised"` → `action: "plan_approved"` — proof of real bidirectional collaboration, not a fixed chain.

## 6. Tools, Frameworks, and Models Used

**Frameworks**
- CrewAI (multi-agent orchestration)
- FastAPI + Uvicorn (API server)
- Pydantic v2 (request/response validation)
- LiteLLM (Compass client, via CrewAI)

**Compass Models**
- `gpt-4.1` — Expense Analyzer, Investment Advisor (pattern recognition, product matching)
- `gpt-5.1` — Risk Profiler, Goal Planner, Compliance Recommender (higher-stakes reasoning, critique synthesis)
- `whisper` — voice transcription via `/transcribe` endpoint (**multimodal bonus**)

**Custom Tools** (`app/tools/`)
- `csv_parser.py` — ADCB CSV format parser (handles 6-row header, DD/MM/YYYY dates)
- `expense_categorizer.py` — Rule-based UAE merchant categorization
- `goal_calculator.py` — Deterministic goal math
- `uae_context.py` — UAE product catalog (conventional + Sharia-compliant)

**Frontend** (`ui/`)
- Vanilla HTML / CSS / JS (no React build step)
- Web Audio API for browser-side WAV encoding (voice input)
- Real-time agent activity panel with per-agent SVG icons

## 7. Data Sources

- **Static synthetic CSVs** in `data/`:
  - `ADCB_Savings_KarimMansour.csv` — 92 transactions over 9 months
  - `ADCB_CreditCard_KarimMansour.csv` — 519 transactions, ~AED 6,553/month spend
- **User profile**: `data/user_profile.json` (static persona)
- **User-uploaded CSV** via `POST /upload-csv` (production data ingestion path)
- **Voice input** via `POST /transcribe` (Compass Whisper)

Total static data size: ~150KB (well under the 500MB hackathon limit).

All data is synthetic — generated programmatically by `scripts/generate_csvs.py` using realistic UAE merchant names (Carrefour, ADNOC, Talabat, Du, DEWA, Stepping Stones Nursery, etc.).

## 8. Repository Structure

```
.
├── app/                            # Core agent logic
│   ├── agents.py                   # 5 CrewAI agent definitions
│   ├── crew.py                     # Orchestrator with critique loop
│   ├── tasks.py                    # Prompt builders
│   ├── config.py                   # Compass config
│   ├── memory/blackboard.py        # Shared state + JSONL trace
│   ├── tools/                      # CSV parser, categorizer, UAE context
│   └── models/schemas.py           # Pydantic request/response
├── data/                           # Synthetic CSVs + profile + history
├── docs/architecture.md            # Full architecture document
├── input_examples/                 # 3 example /run inputs (mandatory)
├── output_examples/                # 3 example /run outputs (mandatory)
├── logs/                           # JSONL agent traces (auto-generated)
├── scripts/                        # generate_output_examples.{ps1,py}
├── ui/                             # Optional UI on port 8001
├── run.py                          # API entrypoint (port 8000)
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container build
├── .dockerignore
├── .env.example                    # Environment variable template
├── .gitignore
├── metadata.json                   # Submission metadata
└── README.md
```

## 9. Environment Variables

Copy `.env.example` to `.env` and fill in your Compass key:

```bash
# Compass (G42 LLM platform) - MANDATORY
OPENAI_API_KEY=your-compass-api-key-here
OPENAI_BASE_URL=https://compass.core42.ai/v1

# Models
AGENT_MODEL=gpt-4.1
REASONING_MODEL=gpt-5.1
EMBEDDING_MODEL=text-embedding-3-large

# Runtime
SAMPLE_MODE=false                  # set true to run without Compass key
LOG_LEVEL=INFO
CREWAI_TELEMETRY_OPT_OUT=true      # suppress CrewAI telemetry SSL warnings
```

`SAMPLE_MODE=true` produces deterministic responses from real CSV math (no Compass calls). Useful for development without a Compass key.

## 10. Setup Instructions

```bash
# 1. Clone the repository
git clone https://github.com/harish-navva/g42-agentathon-personal-finance.git
cd g42-personal-finance-agent

# 2. Create a Python 3.11+ virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # Mac / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Compass
copy .env.example .env          # Windows
# cp .env.example .env          # Mac / Linux
# Edit .env, paste your Compass API key
```

## 11. How to Run Locally

```bash
# Backend (port 8000)
python run.py
```

Optional UI in a second terminal:

```bash
python ui\server.py             # opens http://localhost:8001
```

Visit:
- `http://localhost:8000/` for API service info
- `http://localhost:8000/docs` for interactive Swagger UI
- `http://localhost:8001` for the demo UI

## 12. How to Run with Docker

```bash
# Build the image
docker build -t g42-personal-finance-agent .

# Run with Compass env vars
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_BASE_URL="https://compass.core42.ai/v1" \
  -e SAMPLE_MODE=false \
  g42-personal-finance-agent

# Or use the .env file
docker run --rm -p 8000:8000 --env-file .env g42-personal-finance-agent
```

The container has a built-in `HEALTHCHECK` on `/health`. Docker will report `(healthy)` once the API is ready.

## 13. API Usage

### `POST /run` — Mandatory submission endpoint

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json
```

Request body schema:
```json
{
  "query": "Can I buy a 60,000 AED car in 3 months?",
  "context": {
    "user_id": "karim_mansour_001",
    "csv_files": ["data/ADCB_Savings_KarimMansour.csv",
                  "data/ADCB_CreditCard_KarimMansour.csv"],
    "profile_file": "data/user_profile.json"
  }
}
```

### Other endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service info |
| GET | `/health` | Health check (used by Docker HEALTHCHECK) |
| GET | `/data-files` | List current bank statement CSVs |
| POST | `/upload-csv` | Upload / replace a CSV (production simulation) |
| POST | `/transcribe` | Voice → text via Compass Whisper |
| GET / POST / DELETE | `/history` | Persistent question history (data/history.json) |

## 14. Input and Output Examples

Three reproducible examples are provided:

| File | Query |
|---|---|
| `input_examples/example_1.json` | *"Can I buy a 60,000 AED car in 3 months?"* |
| `input_examples/example_2.json` | *"When is the best time to take a family vacation and what's a realistic budget?"* |
| `input_examples/example_3.json` | *"Where can I cut my monthly expenses without hurting my family's lifestyle?"* |

Corresponding outputs (one per input) are in `output_examples/example_N_output.json`. Each output contains:
- The final answer text (structured)
- `agents_involved` (5 agent names)
- `trace_events` (~25 events showing the full collaboration including critique loop)
- `findings` (financial_summary, risk_profile, plan, investment_recommendations)
- `elapsed_seconds`, `sample_mode`, `trace_path`

To regenerate outputs from inputs after code changes:

```bash
python scripts/generate_output_examples.py    # or .ps1 on Windows
```

## 15. Logs and Traces

Every `POST /run` invocation produces a JSONL trace in `logs/<run_id>.jsonl`.

Example events:
```json
{"agent_name": "Goal Planner", "action": "initial_plan_drafted", "target_agent": "Risk Profiler", ...}
{"agent_name": "Risk Profiler", "action": "critique", "target_agent": "Goal Planner", "severity": "high", ...}
{"agent_name": "Goal Planner", "action": "plan_revised", "target_agent": "Risk Profiler", ...}
{"agent_name": "Risk Profiler", "action": "plan_approved", "target_agent": "Goal Planner", ...}
```

The UI exposes the full trace via a **"View full agent trace"** modal with a **"Copy JSON"** button.

## 16. Demo Video

Demo video: [Insert viewable link here]
Backup demo video: [Insert backup link here]

The video shows the problem, the 5-agent flow with live critique loop, a `/run` invocation, the structured output, and the production deployment path.

## 17. Known Limitations

1. **Synthetic data only** — never tested against real bank statements
2. **English-only agent prompts** — Whisper transcribes Arabic but agents respond in English
3. **Single user / no auth** — would need multi-tenant + per-user data isolation in production
4. **No real-time bank sync** — uploads are manual; production would integrate with Open Banking UAE
5. **Critique loop capped at 2 rounds** — guard against runaway iteration; may bail before optimal plan in edge cases
6. **No tax or zakat optimization** — out of scope but commonly requested
7. **Limited product catalog** — 9 UAE products; real product would integrate ADCB / Emirates NBD / Sarwa APIs

See `docs/architecture.md` §8 for full details.

## 18. Future Improvements

**Short term (weeks)**
- Bilingual support (Arabic + English) via Compass
- Open Banking UAE integration for real-time bank sync
- Per-user authentication and data isolation
- RAG over UAE financial guidance corpus (SCA, ADCB, DIB educational content) using `text-embedding-3-large`

**Medium term (months)**
- Push notifications for upcoming fixed-cost events (rent, school fees) and unusual spending
- Goal milestone tracking with progress nudges
- UAE Pass integration for identity-verified onboarding
- Household mode (shared profile, individual privacy)

**Long term (productionization)**
- Move from JSON-file persistence to managed datastore (DynamoDB in AWS Middle East)
- LangGraph migration if scaling demands
- SOC 2 / ISO 27001 readiness
- SCA-licensed robo-advisory registration before real money flows

See `docs/architecture.md` §9-10 for full deployment notes.

---

## License

MIT

---

*Submitted to G42 Agentathon · Use Case 24 · Personal Finance · 7 June 2026*
