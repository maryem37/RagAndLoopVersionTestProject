# Multi-Agent Test Automation + Local RAG

This project combines two related capabilities:

1. A LangGraph-based multi-agent pipeline that turns business requirements and Swagger/OpenAPI specs into Gherkin features, executable Java tests, test execution results, and coverage reports.
2. A local Retrieval-Augmented Generation (RAG) workflow that ingests local corpora into Chroma so the generation pipeline can retrieve domain examples and context.

The repository is currently shaped around a leave-request management system with two microservices:

- `auth` on port `9000`
- `leave` on port `9001`

The pipeline is configured to generate consolidated end-to-end test assets for those services, with outputs written under `output/`.

## What This Project Does

At a high level, the system:

- reads business requirements from [`business_requirements.yaml`](./business_requirements.yaml)
- loads service definitions from [`config/services_matrix.yaml`](./config/services_matrix.yaml)
- reads one or more Swagger specs from `examples/`
- designs test scenarios before Gherkin generation
- generates `.feature` files
- validates generated Gherkin
- writes Java/Maven-based test code
- executes tests against running services
- analyzes JaCoCo coverage and writes reports
- can optionally use a local Chroma RAG index to improve generation context

## Architecture

### LangGraph workflow

The current workflow is defined in [`graph/workflow.py`](./graph/workflow.py) and runs in this order:

`scenario_designer -> gherkin_generator -> gherkin_validator -> test_writer -> test_executor -> coverage_analyst`

Key pieces:

- [`agents/scenario_designer.py`](./agents/scenario_designer.py): uses an LLM to design structured scenarios from the user story, business requirements, and Swagger, with a deterministic fallback
- [`agents/gherkin_generator.py`](./agents/gherkin_generator.py): converts scenarios or story text into Gherkin features
- [`agents/gherkin_validator.py`](./agents/gherkin_validator.py): validates syntax and scenario quality
- [`agents/test_writer.py`](./agents/test_writer.py): generates Java test code and Maven assets
- [`agents/test_executor.py`](./agents/test_executor.py): runs generated tests
- [`agents/coverage_analyst.py`](./agents/coverage_analyst.py): reads JaCoCo output and applies quality gates
- [`graph/state.py`](./graph/state.py): shared workflow state passed between agents

### RAG workflow

The local RAG utilities live in [`rag/`](./rag):

- [`rag/ingest.py`](./rag/ingest.py): ingests the primary JSON corpus at `data/raw/GivenWhenThen.json` into Chroma
- [`rag/extract_e2egit.py`](./rag/extract_e2egit.py): legacy helper for converting `E2EGit.db` into CSV if you still want to ingest the older dataset
- [`rag/retriever.py`](./rag/retriever.py): queries the local Chroma index

The CLI entry point for both workflows is [`main.py`](./main.py).

## Repository Layout

```text
project_testRAG/
|-- agents/                 # LangGraph agents
|-- config/                 # settings + services matrix
|-- corpus/                 # optional legacy datasets for RAG
|-- data/                   # primary local datasets (GivenWhenThen JSON)
|-- examples/               # sample Swagger specs and user stories
|-- graph/                  # workflow and shared state
|-- output/                 # generated features, tests, reports, jacoco output
|-- rag/                    # RAG extraction, ingestion, retrieval
|-- tools/                  # swagger parsing, coverage helpers, service registry
|-- main.py                 # project CLI
|-- run_pipeline.py         # consolidated E2E pipeline runner
|-- requirements.txt        # Python dependencies
|-- package.json            # gherkin-lint / JS tooling
```

## Requirements

### Python

- Python `3.11+` is recommended
- A virtual environment is strongly recommended

### Runtime tools

- Java `17`
- Maven `3.9+`
- Node.js and npm
- Running target microservices for test execution

### External services and models

- A Hugging Face API token for the LLM-backed generation agents
- Optional local Chroma vector store for RAG

## Setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Install Node dependencies

```powershell
npm install
```

This project uses Node tooling mainly for Gherkin lint support.

### 4. Create a `.env` file

`config/settings.py` requires a root `.env` file. At minimum, define:

```env
HUGGINGFACEHUB_API_TOKEN=your_token_here
HF_MODEL_SCENARIO_DESIGNER=Qwen/Qwen2.5-Coder-32B-Instruct
HF_MODEL_GHERKIN_GENERATOR=Qwen/Qwen2.5-Coder-32B-Instruct
HF_MODEL_GHERKIN_VALIDATOR=mistralai/Mistral-7B-Instruct-v0.2
HF_MODEL_TESTWRITER_AGENT=Qwen/Qwen2.5-Coder-32B-Instruct
HF_TEMP_SCENARIO_DESIGNER=0.1
HF_TEMP_GHERKIN_GENERATOR=0.2
HF_TEMP_GHERKIN_VALIDATOR=0.0
HF_TEMP_TESTWRITER_AGENT=0.2
TEST_JWT_TOKEN=your_test_token_here
AUTH_BASE_URL=http://localhost:9000
LEAVE_BASE_URL=http://localhost:9001
```

Notes:

- Do not commit real tokens or JWTs.
- `get_settings()` will fail fast if `.env` is missing.
- Service configuration is validated from `config/services_matrix.yaml`.

## Service Configuration

Microservices are defined in [`config/services_matrix.yaml`](./config/services_matrix.yaml). Each service entry can define:

- whether the service is enabled
- port and base URL
- Swagger spec path
- Swagger docs URL
- database metadata
- test runner class
- service dependencies

Current default execution order is dependency-aware, so `auth` runs before `leave`.

Useful service commands:

```powershell
python run_pipeline.py --list
python run_pipeline.py --order
python run_pipeline.py --services auth,leave
```

## RAG Quick Start

The RAG flow is useful when you want the generation pipeline to retrieve examples from local corpora.

### Step 1. Prepare the corpus

Primary default input:

- `data/raw/GivenWhenThen.json`

This project now uses that JSON corpus as the default RAG dataset. Each record contributes feature text, step definitions, and linked code files to the index.

Legacy optional inputs still supported:

- `corpus/tier3_zenodo/z13880060_user_stories/raw/*.txt`
- `corpus/tier3_zenodo/z14234731_e2egit/gui_java_junit.csv`

### Step 2. Build the Chroma index

```powershell
python main.py ingest
```

Useful options:

```powershell
python main.py ingest --givenwhenthen-json data/raw/GivenWhenThen.json
python main.py ingest --persist-dir chroma_db --collection tier3_rag
python main.py ingest --chunk-size 1200 --chunk-overlap 150 --batch-size 256
```

Legacy helper if you still want to ingest the old SQLite dataset:

```powershell
python main.py extract-e2egit
python main.py extract-e2egit --db path\to\E2EGit.db --out path\to\gui_java_junit.csv
```

### Step 3. Query the local index

```powershell
python main.py query "leave request approval workflow"
```

The multi-agent pipeline now auto-uses the RAG index when `chroma_db/` exists. You can still control it explicitly:

```powershell
$env:RAG_ENABLE="1"
$env:RAG_PERSIST_DIR="chroma_db"
$env:RAG_COLLECTION="tier3_rag"
```

Disable it explicitly if needed:

```powershell
$env:RAG_ENABLE="0"
```

## Test Automation Quick Start

### Option 1. Run the consolidated E2E pipeline

```powershell
python run_pipeline.py
```

This runner:

- loads enabled services from `services_matrix.yaml`
- loads Swagger specs from `examples/`
- reads the story in `examples/comprehensive_user_story.md`
- executes the LangGraph pipeline
- writes artifacts into `output/`

### Option 2. Run the original demo Gherkin generator

```powershell
python main.py demo-gherkin --user-story-file examples/comprehensive_user_story.md
```

This preserves the older single-command Gherkin demo behavior behind an explicit subcommand.

## Generated Artifacts

The project writes generated files under `output/`.

Important locations:

- [`output/features/`](./output/features): generated `.feature` files
- [`output/tests/`](./output/tests): generated Java tests, Maven project, helper scripts, and test docs
- [`output/reports/`](./output/reports): workflow and coverage reports
- [`output/jacoco/`](./output/jacoco): JaCoCo execution data and HTML/XML/CSV coverage output

Notable generated documents already present in this repo:

- [`output/tests/README.md`](./output/tests/README.md)
- [`output/tests/TEST_SUITE_README.md`](./output/tests/TEST_SUITE_README.md)
- [`output/tests/VERIFICATION_REPORT.md`](./output/tests/VERIFICATION_REPORT.md)
- [`output/tests/START_HERE.md`](./output/tests/START_HERE.md)

## Evaluation Metrics + Diagrams

This repo includes lightweight tooling to compute and plot the evaluation metrics (SV, SC, TC, ESR, TPR, RSR, GT) from the artifacts already produced under `output/`.

### One command (run pipeline + compute metrics + generate PNGs)

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_metrics_and_plots.ps1
```

Outputs:

- `output/eval_runs/metrics/metrics_<run_id>.json`
- `output/eval_runs/plots/metrics_latest.png`
- `output/eval_runs/plots/metrics_over_time.png`

### If you already ran the pipeline

Compute metrics from existing `output/` artifacts:

```powershell
python tools/eval_metrics.py
python tools/plot_metrics.py
```

Skip re-running the pipeline but still log a run ID:

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_metrics_and_plots.ps1 -SkipPipeline
```

Notes:

- SV uses `gherkin-lint` (install Node deps with `npm install`). If it isn't available, SV is left as `null`.
- GT is tracked as wall-clock seconds for the pipeline run (`GT_seconds`) when using the PowerShell runner.

### Compare 3 LLMs and generate graph images

If you want a graph like the example image, but based on this project's real outputs, you can benchmark up to 3 LLMs and then render comparison PNGs.

Run 3 models:

```powershell
python tools/run_llm_benchmark.py `
  --model "llama33=llama-3.3-70b-versatile" `
  --model "mixtral=mixtral-8x7b-32768" `
  --model "qwen=qwen/qwen-2.5-coder-32b-instruct"
```

Optional service filter:

```powershell
python tools/run_llm_benchmark.py `
  --services auth,leave `
  --model "llama33=llama-3.3-70b-versatile" `
  --model "mixtral=mixtral-8x7b-32768" `
  --model "qwen=qwen/qwen-2.5-coder-32b-instruct"
```

Outputs:

- `output/eval_runs/llm_benchmark/<benchmark_id>/benchmark_manifest.json`
- `output/eval_runs/plots/llm_coverage_comparison.png`
- `output/eval_runs/plots/llm_eval_comparison.png`

If you already have metrics and coverage JSON files, you can generate the graphs directly without rerunning the pipeline:

```powershell
python tools/plot_llm_comparison.py `
  --entry "run1|llama-3.3-70b-versatile|output/eval_runs/metrics/metrics_20260426_234203.json|output/reports/coverage_report_auth-leave_20260427_001514.json" `
  --entry "run2|mixtral-8x7b-32768|path\to\metrics_run2.json|path\to\coverage_run2.json" `
  --entry "run3|qwen-2.5-coder-32b-instruct|path\to\metrics_run3.json|path\to\coverage_run3.json"
```

The coverage image uses the project's real JaCoCo aggregates:

- `instructions` as statement coverage
- `branches` as branch coverage
- `methods` as function coverage
- `lines` as line coverage

## Coverage and Quality Gates

Coverage is analyzed after test execution. The workflow can fail if the coverage quality gate fails.

Relevant environment switches in the current implementation:

- `FAIL_ON_COVERAGE_QG=1` or unset: fail the workflow when coverage thresholds are not met
- `ALLOW_COVERAGE_QG_FAILURE=1`: allow the workflow to continue even if the gate fails
- `SKIP_TEST_EXECUTION=1`: stop after writing tests without executing them

Thresholds can also be overridden when running `run_pipeline.py`:

```powershell
$env:MIN_LINE_COVERAGE="60"
$env:MIN_BRANCH_COVERAGE="40"
$env:MIN_METHOD_COVERAGE="60"
python run_pipeline.py
```

## Typical Workflow

For a fresh local run:

1. Start the target microservices locally on the configured ports.
2. Create `.env` with your Hugging Face token and test settings.
3. Install Python and Node dependencies.
4. Confirm service configuration with `python run_pipeline.py --list`.
5. Run `python run_pipeline.py`.
6. Review generated files under `output/features`, `output/tests`, and `output/jacoco/report/html`.

If you also want retrieval support:

1. Put `GivenWhenThen.json` under `data/raw/`.
2. Run `python main.py ingest`.
3. Run the pipeline again.

## Example Commands

```powershell
python run_pipeline.py --list
python run_pipeline.py --order
python run_pipeline.py --services auth
python run_pipeline.py --services auth,leave
python main.py demo-gherkin --user-story-file examples/comprehensive_user_story.md
python main.py ingest
python main.py ingest --givenwhenthen-json data/raw/GivenWhenThen.json
python main.py query "JWT authentication and leave approval"
```

## Troubleshooting

### `.env file not found`

Create a root `.env` file. The settings loader raises an error if it is missing.

### `HUGGINGFACEHUB_API_TOKEN not set`

Add the token to `.env` and restart the process.

### Services not reachable during test execution

Make sure the microservices are running on the ports defined in `config/services_matrix.yaml`.

### No RAG results returned

Check that:

- `data/raw/GivenWhenThen.json` exists
- `ingest` created `chroma_db/`
- `RAG_ENABLE` is not set to `0` if you expect retrieval during generation

### Coverage gate fails

Review the JaCoCo output under `output/jacoco/report/` and either improve tests or temporarily relax thresholds through environment variables.

## Current Project Notes

- The repository contains generated artifacts and historical helper scripts from multiple iterations of the project.
- `README.md` now reflects the current working entry points: `main.py` for CLI tasks and `run_pipeline.py` for consolidated workflow execution.
- The generated test suite under `output/tests/` is documented separately and can be used as a downstream deliverable.

## Main Files to Start With

- [`main.py`](./main.py): core CLI
- [`run_pipeline.py`](./run_pipeline.py): main end-to-end runner
- [`graph/workflow.py`](./graph/workflow.py): workflow orchestration
- [`config/services_matrix.yaml`](./config/services_matrix.yaml): service definitions
- [`business_requirements.yaml`](./business_requirements.yaml): business rules and scenarios
- [`examples/comprehensive_user_story.md`](./examples/comprehensive_user_story.md): input story used by the pipeline
