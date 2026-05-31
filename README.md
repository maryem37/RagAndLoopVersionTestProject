# 🚀 Multi-Agent Test Automation + Local RAG

An end-to-end **AI-assisted test automation pipeline** that reads business requirements and OpenAPI specs, designs test scenarios, generates Gherkin, writes Java/Maven Cucumber tests, executes them, analyzes failures, and reports coverage.

The project is Windows-first, but most Python and Node commands also work on Linux/macOS with small shell changes.

---

## 📌 What This Project Does

This repository automates API and end-to-end test creation for microservices.

It combines:

- 🤖 **LangGraph multi-agent workflow** for test design and generation
- 🧠 **LLM-powered agents** for scenarios, Gherkin, validation, test writing, failure analysis, and coverage analysis
- 🔎 **Local RAG with Chroma** to retrieve real-world BDD examples from local datasets
- 🧪 **Generated Java/Maven Cucumber tests**
- 📊 **JaCoCo coverage analysis**
- 🛠️ **Self-healing retry loops** for failing generated tests
- 🌐 **Optional React/Vite dashboard** to edit configuration and launch runs
- 📈 **Metrics and plotting tools** for evaluating pipeline behavior

The current sample domain is a leave-management system with:

- 🔐 `auth` service on port `9000`
- 📝 `leave` service on port `9001`

The architecture is service-aware, so you can add more services in `config/services_matrix.yaml`.

---

## 🧭 High-Level Architecture

```text
Business Requirements + User Story + OpenAPI Specs
                         │
                         ▼
              LangGraph Multi-Agent Workflow
                         │
     ┌───────────────────┼───────────────────┐
     ▼                   ▼                   ▼
Scenario Design    Gherkin Generation   Gherkin Validation
     │                   │                   │
     └───────────────────▼───────────────────┘
                  Java Test Writer
                         │
                         ▼
                  Maven Test Executor
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
   Failure Analyst                Coverage Analyst
          │                             │
          └──────── retry loops ────────┘
                         │
                         ▼
                Generated Reports + Tests
```

---

## 🧩 Agent Workflow

The pipeline is implemented in `graph/workflow.py` and passes a shared state object from `graph/state.py` through the agents.

| Step | Agent | File | Responsibility |
|---|---|---|---|
| 1️⃣ | Scenario Designer | `agents/scenario_designer.py` | Builds meaningful happy-path, error, edge, security, and integration scenarios |
| 2️⃣ | Gherkin Generator | `agents/gherkin_generator.py` | Converts scenarios into `.feature` files |
| 3️⃣ | Gherkin Validator | `agents/gherkin_validator.py` | Validates syntax, completeness, and scenario quality |
| 4️⃣ | Test Writer | `agents/test_writer.py` | Generates Java step definitions, runners, Maven config, and test project files |
| 5️⃣ | Test Executor | `agents/test_executor.py` | Runs Maven/Cucumber tests and captures execution results |
| 6️⃣ | Failure Analyst | `agents/failure_analyst.py` | Diagnoses failing tests and recommends repairs |
| 7️⃣ | Coverage Analyst | `agents/coverage_analyst.py` | Reads JaCoCo reports, checks thresholds, and suggests coverage improvements |

The workflow includes bounded retry loops:

- 🔁 Gherkin validation failures can route back to generation
- 🔁 Test failures can route through failure analysis and back to test writing
- 🔁 Low coverage can route back to scenario design

---

## 📁 Project Structure

```text
.
├── agents/                         # LangGraph agent implementations
├── graph/                          # Workflow graph and shared state models
├── config/                         # Runtime settings and service matrix
├── rag/                            # Local RAG ingestion and retrieval
├── tools/                          # Swagger parsing, service registry, metrics, plotting, RAG helpers
├── examples/                       # User stories and sample OpenAPI specs
├── data/raw/                       # Local datasets used by RAG
├── output/                         # Generated features, tests, reports, and coverage artifacts
├── src/                            # React/Vite dashboard source
├── dist/                           # Built dashboard assets
├── chroma_db/                      # Persisted Chroma vector database
├── run_pipeline.py                 # Main service-aware pipeline runner
├── run_pipeline_windows.py         # Windows UTF-8 wrapper
├── main.py                         # CLI for RAG and demo commands
├── app_server.py                   # Optional dashboard backend
├── business_requirements.yaml      # Business rules, scenarios, and coverage targets
├── requirements.txt                # Python dependencies
├── package.json                    # Node/Vite/gherkin-lint dependencies
└── README.md                       # This documentation
```

---

## ✅ Requirements

Install these before running the full pipeline:

- 🐍 **Python 3.11+**  
  Python 3.12 is used successfully in this workspace.

- ☕ **Java 17**

- 📦 **Maven 3.9+**

- 🟢 **Node.js + npm**  
  Used for the UI and `gherkin-lint`.

- 🔌 **Target microservices running or reachable**  
  The generated API tests need live services unless you only generate files.

- 🔑 **LLM provider credentials**  
  The sample `.env.example` is configured for Groq, with optional Hugging Face support.

---

## ⚙️ Installation

### 1️⃣ Create and activate a Python virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2️⃣ Install Node dependencies

```powershell
npm install
```

### 3️⃣ Create your `.env`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Then fill in your real values:

```env
# LLM provider config
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here

# Optional Hugging Face token
HUGGINGFACEHUB_API_TOKEN=

# RAG config
RAG_ENABLE=true
RAG_PERSIST_DIR=chroma_db
RAG_COLLECTION=tier3_rag
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

⚠️ Never commit `.env`. It can contain API keys, JWTs, credentials, and service secrets.

---

## 🔧 Service Configuration

Services are declared in:

```text
config/services_matrix.yaml
```

Each service can define:

- ✅ whether it is enabled
- 🌍 base URL and port
- 📄 local Swagger/OpenAPI file path
- 🔗 remote Swagger/OpenAPI URL
- 🧪 Java package, runner class, step class, and Maven location
- 🗄️ database metadata
- 🧩 dependencies on other services
- 🧬 test data used by generated scenarios

Example service shape:

```yaml
services:
  auth:
    enabled: true
    port: 9000
    base_url: http://localhost:9000
    swagger_spec: ''
    swagger_url: http://localhost:9000/v3/api-docs
    role: authentication
    dependencies: []
```

Useful inspection commands:

```powershell
python run_pipeline.py --list
python run_pipeline.py --order
```

---

## 🧪 Running the Pipeline

### Recommended on Windows

```powershell
python run_pipeline_windows.py
```

### Standard runner

```powershell
python run_pipeline.py
```

### Run only selected services

```powershell
python run_pipeline.py --services auth
python run_pipeline.py --services leave
python run_pipeline.py --services auth,leave
```

The runner will:

1. 📖 Read `examples/comprehensive_user_story.md`
2. 📋 Load rules and coverage targets from `business_requirements.yaml`
3. 🧭 Load service definitions from `config/services_matrix.yaml`
4. 📡 Fetch OpenAPI specs from each configured `swagger_url` or `swagger_spec`
5. 🤖 Execute the LangGraph workflow
6. 🧪 Generate and run Java/Maven tests
7. 📊 Analyze JaCoCo coverage
8. 📦 Write results into `output/`

---

## 📝 Important Input Files

| File | Purpose |
|---|---|
| `examples/comprehensive_user_story.md` | Main user story used by the pipeline |
| `business_requirements.yaml` | Business rules, critical endpoints, test scenario categories, priorities, and coverage targets |
| `config/services_matrix.yaml` | Service registry and execution configuration |
| `.env` | Local secrets and runtime environment variables |
| `data/raw/GivenWhenThen.json` | Main BDD dataset used by RAG |

---

## 📦 Output Files

Generated artifacts are written under `output/`.

| Path | Contains |
|---|---|
| `output/features/` | Generated `.feature` files |
| `output/tests/` | Generated Java/Maven test project |
| `output/reports/` | Workflow summaries, execution summaries, and coverage JSON/YAML |
| `output/jacoco/` | JaCoCo execution data and HTML reports when produced |

Useful generated documentation:

- 📌 `output/tests/START_HERE.md`
- 📖 `output/tests/README.md`
- 🧪 `output/tests/TEST_EXECUTION_GUIDE.md`
- 📊 `output/tests/TEST_GENERATION_SUMMARY.md`
- ✅ `output/tests/VERIFICATION_REPORT.md`

---

## 🧠 Local RAG

RAG is optional, but it improves scenario quality by giving agents examples from real-world BDD test corpora.

### RAG sources

- 📚 `data/raw/GivenWhenThen.json`
- 🗃️ Optional E2EGit SQLite/CSV corpus
- 📝 Optional user story text corpora

### Build the Chroma index

```powershell
python main.py ingest
```

Custom example:

```powershell
python main.py ingest --givenwhenthen-json data/raw/GivenWhenThen.json --persist-dir chroma_db --collection tier3_rag
```

### Query the local index

```powershell
python main.py query "JWT authentication and leave approval"
python main.py query "invalid leave request boundary case" --k 3
```

### RAG environment variables

```powershell
$env:RAG_ENABLE="true"
$env:RAG_PERSIST_DIR="chroma_db"
$env:RAG_COLLECTION="tier3_rag"
$env:RAG_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
```

For more detail, see `RAG_STRUCTURE.md`.

---

## 📊 Coverage Gates

Coverage targets are configured in `business_requirements.yaml`:

```yaml
COVERAGE_TARGETS:
  LINE_COVERAGE: 50.0
  BRANCH_COVERAGE: 25.0
  METHOD_COVERAGE: 70.0
```

You can override them at runtime:

```powershell
$env:MIN_LINE_COVERAGE="60"
$env:MIN_BRANCH_COVERAGE="40"
$env:MIN_METHOD_COVERAGE="60"
python run_pipeline_windows.py
```

Helpful flags:

| Variable | Effect |
|---|---|
| `SKIP_TEST_EXECUTION=1` | Generate tests without running Maven |
| `FAIL_ON_COVERAGE_QG=1` | Fail when coverage gates are not met |
| `ALLOW_COVERAGE_QG_FAILURE=1` | Continue even if quality gates fail |
| `ENABLE_COVERAGE_IMPROVEMENT=false` | Disable the coverage improvement loop |
| `MAX_HEALING_ATTEMPTS=3` | Control failure-healing retries |
| `MAX_GHERKIN_VALIDATION_RETRIES=2` | Control Gherkin regeneration retries |
| `MAX_COVERAGE_IMPROVEMENT_ATTEMPTS=1` | Control coverage improvement retries |

---

## 🏗️ Real Backend Coverage

By default, generated Maven tests can produce coverage for the generated test project. For coverage of the **actual running backend services**, start services with the JaCoCo Java agent and then run the pipeline.

Relevant helpers:

- `restart_services_with_jacoco.py`
- `restart_services_with_jacoco.ps1`
- `restart-services-with-jacoco.ps1`
- `start_backend_with_jacoco.bat`
- `collect_jacoco_coverage.py`
- `run_real_coverage.ps1`

High-level flow:

1. ☕ Start backend microservices with the JaCoCo agent
2. 🧪 Run generated tests against live services
3. 📥 Dump `.exec` coverage files
4. 📊 Generate JaCoCo HTML reports

⚠️ Some helper scripts may contain machine-specific paths. Review them before using them on another machine.

More notes are available in `REAL_BACKEND_COVERAGE_SOLUTION.md`.

---

## 🌐 Optional Dashboard

The project includes a React/Vite dashboard backed by `app_server.py`.

The dashboard can:

- 🧭 Load and edit `config/services_matrix.yaml`
- 📝 Edit the main user story
- 📋 Edit business requirements
- ▶️ Start pipeline runs
- 📡 Show run status and logs
- 📎 Link to latest output artifacts

### Development UI

```powershell
npm run dev
```

### Build and serve through Python

```powershell
npm run build
python app_server.py
```

Then open:

```text
http://127.0.0.1:8000
```

Backend API routes:

| Route | Method | Purpose |
|---|---|---|
| `/api/state` | `GET` | Load current UI/project state |
| `/api/save` | `POST` | Save edited config/story/requirements |
| `/api/run` | `POST` | Start a pipeline run |
| `/api/run-status` | `GET` | Poll run status |
| `/files/{path}` | `GET` | Serve safe project artifacts |

---

## 🧰 CLI Commands

### Pipeline

```powershell
python run_pipeline.py
python run_pipeline.py --list
python run_pipeline.py --order
python run_pipeline.py --services auth,leave
```

### RAG

```powershell
python main.py ingest
python main.py query "API validation error scenario"
python main.py demo-gherkin
```

### UI

```powershell
npm run dev
npm run build
python app_server.py
```

### Metrics and plots

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_metrics_and_plots.ps1
python tools/eval_metrics.py
python tools/plot_metrics.py
```

---

## 📈 Metrics and Evaluation Tools

The `tools/` folder includes scripts for inspecting generated outputs and comparing pipeline performance:

- 📊 `tools/eval_metrics.py`
- 📉 `tools/plot_metrics.py`
- 🤖 `tools/run_llm_benchmark.py`
- 🧮 `tools/recompute_benchmark_metrics.py`
- 🖼️ `tools/render_agent_benchmark_png.py`
- 🧭 `tools/render_pipeline_agents_png.py`
- 📌 `tools/plot_loop_vs_no_loop.py`
- 🔍 `tools/analyze_cucumber_failures.py`

These are useful for research-style evaluation, debugging, and comparing LLM behavior.

---

## 🧪 Generated Test Project

The generated test project lives in:

```text
output/tests/
```

Typical commands:

```powershell
cd output/tests
mvn clean test
mvn test
mvn jacoco:report
```

On Windows, generated helper scripts may also be available:

```powershell
.\run_tests.bat
```

Generated test docs usually include:

- 🎯 quick start
- 🧪 execution guide
- 📁 file index
- ✅ verification report
- 📊 generation summary

---

## 🔐 Security Notes

- 🚫 Do not commit `.env`
- 🚫 Do not commit real JWT tokens, passwords, database credentials, or API keys
- 🔎 Review `config/services_matrix.yaml` before sharing because it can contain local credentials or tokens
- 🧼 Treat generated tests as code that must be reviewed before production use
- 🔒 Prefer environment variables for secrets instead of hard-coding them into YAML or scripts

---

## 🐞 Troubleshooting

### `.env` is missing

Create it from the example:

```powershell
Copy-Item .env.example .env
```

### Windows encoding problems

Use:

```powershell
python run_pipeline_windows.py
```

### Services are unreachable

Check:

- the service is running
- the port matches `config/services_matrix.yaml`
- `swagger_url` returns JSON
- firewalls or proxies are not blocking localhost

### Swagger cannot be loaded

Either set:

```yaml
swagger_spec: path/to/openapi.json
```

or:

```yaml
swagger_url: http://localhost:9000/v3/api-docs
```

### RAG returns no results

Run ingestion:

```powershell
python main.py ingest
```

Then confirm `chroma_db/` exists.

### Maven is not found

Check Java and Maven:

```powershell
java -version
mvn -version
```

If your Maven path is custom, update:

```text
config/services_matrix.yaml
```

### Tests fail because authentication expired

Refresh the JWT/login test data and verify:

- login endpoint
- credentials
- token expiry
- authorization headers generated by the test writer

### Coverage gates fail

Lower thresholds temporarily or allow failure while debugging:

```powershell
$env:ALLOW_COVERAGE_QG_FAILURE="1"
python run_pipeline_windows.py
```

---

## 🗺️ Key Files to Read First

| File | Why it matters |
|---|---|
| `run_pipeline.py` | Main pipeline entry point |
| `graph/workflow.py` | LangGraph node order and retry routing |
| `graph/state.py` | Shared workflow state passed between agents |
| `agents/scenario_designer.py` | Scenario planning logic |
| `agents/test_writer.py` | Java/Maven test generation logic |
| `agents/test_executor.py` | Maven execution logic |
| `agents/coverage_analyst.py` | Coverage parsing and quality gates |
| `tools/service_registry.py` | Reads and normalizes configured services |
| `tools/swagger_parser.py` | OpenAPI parsing helpers |
| `tools/rag_scenario_retriever.py` | RAG examples injected into prompts |
| `main.py` | RAG CLI commands |
| `app_server.py` | Optional dashboard backend |

---

## 🚦 Recommended Workflow

For a clean run:

1. ✅ Start your backend services
2. ✅ Verify Swagger endpoints in the browser
3. ✅ Activate Python venv
4. ✅ Install Python and Node dependencies
5. ✅ Fill `.env`
6. ✅ Review `config/services_matrix.yaml`
7. ✅ Optionally run `python main.py ingest`
8. ✅ Run `python run_pipeline_windows.py`
9. ✅ Inspect `output/tests/START_HERE.md`
10. ✅ Review generated tests before using them in CI

---

## 🧾 Current Domain Example

The included business requirements describe:

- 🔐 authentication and user management
- 🏢 department and role management
- 📝 leave request creation
- ✅ approval and rejection workflows
- 🛡️ JWT and role-based access rules
- 📆 date validation, overlap detection, and leave balance constraints
- 🔗 integration between the auth and leave services

The project is not limited to that domain. Add or edit services and requirements to generate tests for other APIs.

---

## ✨ Summary

This project is a complete AI-assisted QA pipeline:

- 🧠 It understands requirements
- 📡 It reads OpenAPI specs
- 🧪 It generates executable tests
- 🔁 It retries and improves when things fail
- 📊 It checks coverage
- 🌐 It can be controlled from a local dashboard
- 🔎 It can use local RAG to ground generation in real test examples

Use it as a test-generation accelerator, a research prototype, or a foundation for automated API QA across multiple microservices.
