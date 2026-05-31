# Cleanup report (what the system needs vs optional)

This repo contains a working **core pipeline**, plus many **one-off scripts**, **debug helpers**, and **generated artifacts** from experiments.

This document groups files into:

- **Core**: required to run the pipeline (`run_pipeline.py` / `run_pipeline_windows.py`) and optional RAG (`main.py ingest/query`).
- **Optional**: useful features (UI, real-backend coverage, benchmarks, plotting).
- **Generated / cache**: safe to delete and usually should not be committed.
- **Legacy / experiments**: not used by the core entrypoints; safe to remove *if you don’t rely on them*.

## Core (keep)

**Entrypoints**
- `run_pipeline.py`
- `run_pipeline_windows.py`
- `main.py`

**Pipeline packages**
- `agents/`
- `graph/`
- `tools/`
- `config/`
- `rag/` (only required if you use RAG)

**Inputs / config**
- `business_requirements.yaml`
- `config/services_matrix.yaml`
- `examples/` (user story + swagger specs)
- `.env.example` (template)
- `requirements.txt`

## Optional (keep only if you use the feature)

### UI dashboard (Vite + server)
If you want the dashboard (`python app_server.py`, `npm run dev/build`), keep:
- `app_server.py`
- `src/`, `index.html`, `vite.config.mjs`, `eslint.config.mjs`
- `package.json`, `package-lock.json`

If you don’t use the UI, none of the above is required for the Python pipeline.

### Real backend coverage mode (JaCoCo agent/CLI)
Used when you want coverage of **running Java microservices**, not just the generated test project.

Keep if you use it:
- `run_real_coverage.ps1`
- `restart_services_with_jacoco.ps1`, `restart_services_with_jacoco.py`, `restart-services-jacoco.ps1`, `restart-services-with-jacoco.ps1`
- `start_backend_with_jacoco.bat`
- `collect_jacoco_coverage.py`
- `jacocoagent.jar`, `jacococli.jar` (and any jacoco CLI/agent jars you rely on)

Notes:
- Several of these scripts contain **hard-coded paths** (machine-specific). Treat them as templates.

### Benchmarks / plots / metrics
Keep if you run the evaluation tooling:
- `tools/run_metrics_and_plots.ps1`
- `tools/eval_metrics.py`, `tools/plot_metrics.py`
- `tools/run_llm_benchmark.py`, `tools/plot_llm_comparison.py`, `tools/render_*.py`
- `generate_graph.py` (workflow diagram helper)

## Generated / cache (safe to delete)

These are outputs/caches and can be re-created:

- `.venv312/`
- `node_modules/`
- `__pycache__/` (anywhere)
- `dist/` (UI build output)
- `output/` (pipeline-generated artifacts)
- `chroma_db/` (RAG persisted index; delete if you want to rebuild)
- `test-results/`
- `pipeline_*.log`
- `LLM_RAW_OUTPUT.txt`, `LLM_RAW_OUTPUT_BEFORE_STRIP.txt`

## Legacy / experiments (not needed by core entrypoints)

These files are not required to run `run_pipeline.py` + `main.py ingest/query`.
Keep them only if you still use the specific workflow they implement.

**Debug / scratch**
- `debug_minimal_pipeline.py`
- `debug_state_serialization.py`
- `debug_swagger_loading.py`
- `scratch_check_executor_logic.py`

**Alternate runners / old pipelines**
- `run_pipeline_utf8.ps1` (mostly redundant with `run_pipeline_windows.py`)
- `run_complete_pipeline.ps1`
- `run_pipeline.py` is the canonical runner; the rest are convenience wrappers.

**Coverage experiments / helpers (often hard-coded)**
- `analyze_coverage_now.py`
- `collect_backend_coverage_now.py`
- `fast_backend_coverage.py`
- `fast_coverage_now.py`
- `quick_backend_coverage.py`
- `coverage_booster.py`
- `dump_service_coverage.py`
- `collect_coverage_and_report.ps1`
- `generate_coverage_report.ps1`

**Fix scripts / one-offs**
- `comprehensive_fix_all.py`
- `quick_fix.bat`
- `fix-and-run-tests.bat`
- `fix-and-run-tests.ps1`

**Misc / project-specific**
- `CorsConfig.java` (not used by the Python pipeline)
- `kk.js` (only relevant if referenced by the UI; otherwise remove)

## Suggested next step

If you tell me what you actually use:

1) **Pipeline only** (no UI, no real-backend coverage)
2) **Pipeline + RAG**
3) **Pipeline + UI**
4) **Pipeline + real backend JaCoCo coverage**

…I can propose a precise delete/move list and (if you want) apply the cleanup in the workspace.
