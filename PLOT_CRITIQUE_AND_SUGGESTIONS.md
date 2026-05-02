# Plot Folder Critique & Visualization Suggestions

## Current Plot Inventory

### 1. `output/plots/agent_gherkin_generator_comparison.png`
**What it means:** Compares up to 3 LLMs on the **Gherkin Generator Agent** alone.
- **Duration (ms):** Generation speed
- **Scenarios:** Number of scenarios produced
- **Steps:** Total Gherkin steps produced
- **gherkin-lint issues:** Syntax/style violations (lower is better)

**Data insight:** `gptoss20b` generated 0 scenarios (empty output), while `llama31` and `llama33` generated 6-7 scenarios with 5-6 indentation lint issues.

### 2. `output/plots/agent_gherkin_generator_usage_comparison.png`
**What it means:** Same benchmark focused on **cost/efficiency**:
- Run Time, Prompt/Completion/Total Tokens

**Data insight:** `gptoss20b` consumed 4,750 tokens (2,000 completion) but produced nothing. `llama33` used ~3,000 tokens and produced 7 scenarios.

### 3. `output/eval_runs/plots/llm_eval_comparison.png`
**What it means:** End-to-end pipeline evaluation across 6 dimensions:

| Metric | Meaning |
|--------|---------|
| **SV** | Syntax Validity — % scenarios passing gherkin-lint |
| **SC** | Scenario Coverage — % of 45 reference scenarios matched |
| **TC** | Test Compilation — 100% if Surefire reports exist, 0% if compile failed |
| **ESR** | Execution Success Rate — % executed scenarios without runtime errors |
| **TPR** | Test Pass Rate — % executed scenarios that pass assertions |
| **RSR** | Repair Success Rate — whether the "healing" agent fixed broken tests |

**Data insight (llama33 run):** SV=100%, SC=17.8%, TC=100%, ESR=100%, TPR=76%. Syntax is perfect, but only ~18% of required scenarios were generated; of those that ran, 76% passed.

### 4. `output/eval_runs/plots/llm_coverage_comparison.png`
**What it means:** JaCoCo code coverage comparison:
- Instructions (Statements), Branches, Methods, Lines coverage %

### 5. `output/eval_runs/plots/metrics_latest.png` & `metrics_over_time.png`
**What it means:** Trend plots of the 6 metrics across benchmark runs.

**Issue:** Each run swaps the LLM, so the "trend" mixes model changes with system improvements, making it misleading.

---

## Critique of Current Visualizations

### Strengths
- **Consistent visual language:** Same colors, hatching for N/A, clean bar charts.
- **Handles missing data well:** Gray hatched bars for "no tests executed."
- **Separates concerns:** Agent quality, pipeline quality, and code coverage are in different plots.

### Weaknesses
1. **No multi-dimensional view.** You have 6+ metrics per model but no single chart showing trade-offs (e.g., a radar chart).
2. **No correlation insight.** Does higher token usage lead to better SC? Does better SC lead to higher TPR? No scatter plots reveal this.
3. **No breakdown by scenario category.** SC=17.8% is a black box—you cannot see if the model covers HAPPY_PATH but misses SECURITY_CASES.
4. **No pass/fail breakdown.** ESR and TPR are averages; a stacked bar showing passed/failed/skipped/runtime-error per model would be more actionable.
5. **No cost-efficiency metric.** `gptoss20b` burned 4,750 tokens for zero output—there is no "value per token" visualization.
6. **Metrics over time is misleading.** Because each run swaps the LLM, the trend line is not apples-to-apples.
7. **No per-service coverage split.** JaCoCo aggregates auth + leave services; you cannot see if the model over-covers one and under-covers the other.
8. **Static 2×2 grids waste space.** For only 3 models, a single row of 4 charts or a smaller figure would be more readable.

---

## Suggested Additional Diagrams

### 1. Radar / Spider Chart — "Model Capability Profile"
Plot SV, SC, TC, ESR, TPR, and Average Coverage on a single radar chart per model.
- **Why:** Instantly reveals whether a model is "balanced" or skewed (e.g., great syntax, terrible coverage).

### 2. Scatter Plot — "Efficiency Frontier" (Quality vs. Cost)
- **X-axis:** Total tokens consumed
- **Y-axis:** TPR or SC
- **Bubble size:** Code coverage %
- **Why:** Exposes models like `gptoss20b` as inefficient outliers and finds the Pareto-optimal model.

### 3. Heatmap — "Reference Scenario Coverage Matrix"
- **Rows:** 45 reference scenarios (grouped by `auth:HAPPY_PATH`, `leave:SECURITY_CASES`, etc.)
- **Columns:** LLM models
- **Color intensity:** Best fuzzy-match score (0.0–1.0)
- **Why:** Turns SC=17.8% into actionable detail—shows *exactly* which requirements are missing.

### 4. Stacked Bar Chart — "Test Outcome Breakdown per Model"
Per model, stack: `Passed` / `Failed (assertion)` / `Failed (runtime)` / `Skipped` / `Not Generated`
- **Why:** Reveals where the pipeline drops off. A waterfall from "Generated" → "Executed" → "Passed" is extremely useful.

### 5. Faceted Bar Chart — "Coverage by Service"
Split the 4 JaCoCo metrics into two groups: `auth-service` and `leave-service` (JaCoCo execs: `auth.exec`, `conge.exec`, `leave.exec` exist in `output/jacoco/`).
- **Why:** Prevents one service from masking poor coverage in the other.

### 6. Correlation Matrix Heatmap
Compute Pearson/Spearman correlation between SV, SC, TC, ESR, TPR, Coverage%, Token Count, Duration.
- **Why:** Answers questions like "Does lint cleanliness predict test pass rate?"

### 7. Funnel / Waterfall Chart — "Pipeline Conversion"
Stages: `Reference Scenarios` → `Generated Scenarios` → `Compiled` → `Executed` → `Passed`
Show the drop-off at each stage per model.
- **Why:** Pinpoints the bottleneck (generation vs. compilation vs. execution).

### 8. Box Plot / Violin Plot — "Metric Distribution Across Runs"
Once you have multiple runs of the same model, show the variance.
- **Why:** A single run can be lucky/unlucky; variance matters for production decisions.

### 9. Token Efficiency Bar Chart
Metric: `(SC × TPR × Coverage%) / Total Tokens` or simply `Passed Scenarios / 1000 Tokens`
- **Why:** Directly answers "which model gives the most correct tests per dollar/token?"

### 10. Gantt-style Timeline — "Generation & Execution Latency"
If you log per-step timestamps, visualize pipeline stages (RAG → Gherkin Gen → Test Writing → Compilation → Execution) per model.
- **Why:** Identifies which stage dominates latency.

---

## Quick Win Recommendation

Create a new script `tools/plot_advanced_benchmarks.py` that consumes the same benchmark manifests and metrics JSONs but generates the **Radar chart**, **Scatter plot (Quality vs. Cost)**, **Heatmap (Scenario coverage matrix)**, and **Stacked outcome bars**.

