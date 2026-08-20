# Tilda Agent Demo — Fraud Detection Requirements Pipeline

A four-agent Python prototype for drafting fraud-detection requirements, designing tests, triaging defects, and producing traceability reports. Phase 1 uses hand-written mock LLM fixtures so orchestration, Pydantic schemas, and guardrails can be proven without an API key.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Full happy path (auto-approves human gates)
python main.py --mode mock_clean --auto-approve

# Stop at the first guardrail violation (requirements agent)
python main.py --mode mock_violation

# Exercise each agent's violation fixture independently
python main.py --mode mock_violation --violation-case requirements
python main.py --mode mock_violation --violation-case test_design
python main.py --mode mock_violation --violation-case defect_analysis
python main.py --mode mock_violation --violation-case documentation
```

Interactive runs omit `--auto-approve`; human gates prompt with `[y/n]`.

## Phase 2 (live requirements agent)

```bash
cp .env.example .env   # set ANTHROPIC_API_KEY
python main.py --mode live --intake seed/ato_incident.json --auto-approve
python main.py --mode live --intake seed/app_incident.json --auto-approve
```

The same `guardrails/requirements_guardrails.py` validates live model output.

## Web UI

Terminal 1 — API server:

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 — frontend dev server:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Use **Run (clean)** to walk the full pipeline, or **Run (violation)** at any gated stage to see which specific guardrail check fails.

## Architecture

| Agent | Output store | Human gate |
|-------|-------------|------------|
| Requirements | `data/requirements.json` | Yes — must resolve open questions |
| Test design | `data/tests.json` | Yes |
| Execution | `data/executions.json` | Canned fixture |
| Defect analysis | `data/defects.json` | Yes |
| Documentation | (report only) | No |

**Deterministic orchestrator:** `orchestrator.py` runs agents in a fixed sequence (`requirements → test_design → execution → defect_analysis → documentation`). No LLM chooses routing — each agent only reasons within its own task. Guardrails run after every agent call; failures print specific checks and halt the pipeline.

## Project layout

```
models/schemas.py       Shared Pydantic models
agents/                 One agent module per pipeline stage
guardrails/             One validator module per agent
mocks/                  Clean + violating LLM fixtures
data/                   JSON stores mutated during runs
seed/                   Raw intake incidents
orchestrator.py         Fixed pipeline + human gates
main.py                 CLI demo runner
```
