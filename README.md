# Multi-Agent Test Automation + Local RAG (Windows-first)

This repository is a **test-automation pipeline** that generates and runs end-to-end API tests for a set of microservices.

It combines:

- **LangGraph multi-agent generation**: business requirements + OpenAPI → scenarios → Gherkin → Java/Maven tests
- **Execution + coverage**: runs tests and produces **JaCoCo** coverage reports
- **Optional local RAG (Chroma)**: indexes a local corpus so agents can retrieve real examples during generation
- **Optional local UI**: a small dashboard to edit config and run the pipeline

The repo is currently shaped around a leave-management example (e.g. `auth` on `9000`, `leave` on `9001`), but the runner is designed to handle **any number of services** declared in `config/services_matrix.yaml`.

## Key entry points

- `run_pipeline.py` – main end-to-end runner (service-aware)
- `run_pipeline_windows.py` – same runner, but forces UTF-8 output on Windows
- `main.py` – RAG CLI (`ingest`, `query`, plus a small `demo-gherkin` command)
- `app_server.py` – optional dashboard backend (serves a built frontend from `dist/`)

## Requirements

- Python 3.11+ (3.12 works well)
- Java 17
- Maven 3.9+
- Node.js + npm (used mainly for `gherkin-lint` and the optional UI)

You also need the **target microservices running** (or reachable) if you want the generated tests to execute.

## Setup

### 1) Python venv

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Node dependencies (optional but recommended)

```powershell
npm install
```

### 3) Create `.env`

Some agents require model credentials; `config/settings.py` will fail fast if `.env` is missing.

Minimal example:

```env
HUGGINGFACEHUB_API_TOKEN=...

# Service endpoints used by generated tests
AUTH_BASE_URL=http://localhost:9000
LEAVE_BASE_URL=http://localhost:9001

# Test auth (example)
TEST_JWT_TOKEN=...
```

Model selection is also configurable via `.env` (see `config/settings.py`).

## Configure services

Services live in `config/services_matrix.yaml`.

Useful commands:

```powershell
python run_pipeline.py --list
python run_pipeline.py --order
python run_pipeline.py --services auth,leave
```

OpenAPI is loaded per service from either:

- `swagger_spec` (local file path), or
- `swagger_url` (reachable OpenAPI endpoint)

## Run the pipeline

### Recommended (Windows)

```powershell
python run_pipeline_windows.py
```

### Other platforms

```bash
python run_pipeline.py
```

### Run a subset of services

```powershell
python run_pipeline_windows.py --services auth
python run_pipeline_windows.py --services auth,leave
```

The runner:

1) reads the story in `examples/comprehensive_user_story.md`
2) loads business constraints from `business_requirements.yaml`
3) loads OpenAPI specs for all configured services
4) runs the LangGraph workflow:
   `scenario_designer -> gherkin_generator -> gherkin_validator -> test_writer -> test_executor -> coverage_analyst`

## Outputs

Generated artifacts go under `output/`:

- `output/features/` – generated `.feature` files
- `output/tests/` – generated Java/Maven test project
- `output/reports/` – workflow summaries + coverage summaries (JSON/YAML)
- `output/jacoco/` – JaCoCo data + HTML reports (when produced by the pipeline)

The generated test project is additionally documented in:

- `output/tests/README.md`
- `output/tests/START_HERE.md`

## RAG (optional)

### Build the local index

Default corpus:

- `data/raw/GivenWhenThen.json`

Build the Chroma index:

```powershell
python main.py ingest
```

Query it:

```powershell
python main.py query "JWT authentication and leave approval"
```

RAG is auto-used when `chroma_db/` exists. You can control it via env vars:

```powershell
$env:RAG_ENABLE="1"        # or "0"
$env:RAG_PERSIST_DIR="chroma_db"
$env:RAG_COLLECTION="tier3_rag"
```

For a deeper explanation, see `RAG_STRUCTURE.md`.

## Coverage gates

Coverage thresholds can come from `business_requirements.yaml` (section `COVERAGE_TARGETS`) and can be overridden at runtime:

```powershell
$env:MIN_LINE_COVERAGE="60"
$env:MIN_BRANCH_COVERAGE="40"
$env:MIN_METHOD_COVERAGE="60"
python run_pipeline_windows.py
```

Relevant switches:

- `FAIL_ON_COVERAGE_QG=1` (default behavior): fail the workflow if thresholds are not met
- `ALLOW_COVERAGE_QG_FAILURE=1`: continue even if the gate fails
- `SKIP_TEST_EXECUTION=1`: generate tests but do not run them

## “Real backend coverage” (optional, advanced)

If you want **coverage of the running microservices** (instead of just the generated test project), you can start the backends with the JaCoCo agent and then run tests against them.

This repo contains helper scripts (e.g. `restart_services_with_jacoco.py`, `start_backend_with_jacoco.bat`, `collect_jacoco_coverage.py`).
Note: some of these were created for a specific machine and may contain **hard-coded paths**; treat them as templates.

High-level flow:

1) Start services with JaCoCo agent enabled
2) Run `python run_pipeline_windows.py`
3) Dump `.exec` files and generate the HTML report (`index.html`)

Related notes and context live in `REAL_BACKEND_COVERAGE_SOLUTION.md`.

## Optional UI dashboard

There is a small UI that can edit `config/services_matrix.yaml`, edit the story/requirements, and trigger a run.

Dev UI:

```powershell
npm run dev
```

Production-like (build + serve):

```powershell
npm run build
python app_server.py
```

Then open: `http://127.0.0.1:8000`.

## Metrics + plots (optional)

One command to run the pipeline and generate evaluation plots:

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_metrics_and_plots.ps1
```

If you already ran the pipeline:

```powershell
python tools/eval_metrics.py
python tools/plot_metrics.py
```

## Troubleshooting

- `.env` missing: create it at repo root (see Setup)
- Encoding errors on Windows: use `python run_pipeline_windows.py`
- Services unreachable: verify `config/services_matrix.yaml` ports/base URLs and that your services are running
- RAG returns nothing: run `python main.py ingest` and confirm `chroma_db/` exists

## Where to look next

- `run_pipeline.py` – main orchestrator
- `graph/workflow.py` + `graph/state.py` – workflow + state
- `agents/` – scenario design, Gherkin generation/validation, test writing, execution, coverage analysis
- `tools/` – swagger parsing, service registry, metrics, RAG scenario retrieval
