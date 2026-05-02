import { useEffect, useMemo, useRef, useState } from "react";

const blankGlobal = {
  output_base_path: "output",
  timeout_seconds: 300,
  jwt: {
    login_url: "",
    credentials: {
      email: "",
      password: "",
    },
    env_var: "",
    expiry_minutes: 1440,
  },
  maven: {
    executable: "",
    java_version: 17,
  },
};

const emptyRunStatus = {
  status: "idle",
  started_at: null,
  finished_at: null,
  returncode: null,
  selected_services: [],
  run_mode: "real_coverage",
  logs: [],
  result: {
    summary: {},
    artifacts: [],
  },
  is_running: false,
};

function withServiceUiId(service, index) {
  return {
    ...service,
    ui_id: service.ui_id || service.original_name || `service-${index}`,
  };
}

function getRunnableServices(services) {
  const namedServices = services.filter((service) => String(service.name || "").trim());
  const enabledServices = namedServices.filter((service) => service.enabled);
  return enabledServices.length ? enabledServices : namedServices;
}

function getResultTime(result) {
  const summary = result?.summary?.summary || result?.summary || {};
  const rawTime = result?.report_modified_at || summary.generated_at || result?.collected_at;
  const parsed = rawTime ? Date.parse(rawTime) : 0;
  return Number.isNaN(parsed) ? 0 : parsed;
}

function getBestResult(runResult, latestResult) {
  if (!runResult) {
    return latestResult || { summary: {}, artifacts: [] };
  }
  if (!latestResult) {
    return runResult;
  }
  return getResultTime(latestResult) >= getResultTime(runResult) ? latestResult : runResult;
}

const realCoverageCompletionMarkers = [
  "Done.",
  "XML:  output/jacoco/report/jacoco.xml",
  "HTML: output/jacoco/report/html/index.html",
  "Pipeline finished with exit code 0.",
];

const pipelineOnlyCompletionMarkers = [
  "WORKFLOW EXECUTION SUMMARY",
  "Status      : COMPLETED",
  "Status: completed",
  "CONSOLIDATED E2E PIPELINE COMPLETED",
  "End-to-end consolidated tests completed!",
  "Pipeline finished with exit code 0.",
];

const terminalFailureMarkers = [
  "Status      : FAILED",
  "Status: failed",
  "Pipeline execution failed unexpectedly:",
];

function hasNonZeroPipelineExit(messages) {
  return messages.some((message) => {
    const match = String(message || "").match(/Pipeline finished with exit code (\d+)\./);
    return match ? Number(match[1]) !== 0 : false;
  });
}

function hasTerminalFailure(messages, runMode) {
  if (runMode === "real_coverage") {
    return (
      hasNonZeroPipelineExit(messages) ||
      messages.some((message) => message.includes("Pipeline execution failed unexpectedly:"))
    );
  }

  return (
    hasNonZeroPipelineExit(messages) ||
    messages.some((message) =>
      terminalFailureMarkers.some((marker) => message.includes(marker))
    )
  );
}

const workflowStages = [
  {
    id: "scenario_designer",
    label: "Scenario Designer Agent",
    title: "Scenario Designer Agent",
    description: "Creates test scenarios.",
    patterns: ["agents.scenario_designer"],
  },
  {
    id: "gherkin_generator",
    label: "Gherkin Generator Agent",
    title: "Gherkin Generator Agent",
    description: "Writes feature files.",
    patterns: ["agents.gherkin_generator"],
  },
  {
    id: "gherkin_validator",
    label: "Gherkin Validator Agent",
    title: "Gherkin Validator Agent",
    description: "Validates scenarios.",
    patterns: ["agents.gherkin_validator"],
  },
  {
    id: "test_writer",
    label: "Test Writer Agent",
    title: "Test Writer Agent",
    description: "Generates test code.",
    patterns: ["agents.test_writer"],
  },
  {
    id: "test_executor",
    label: "Test Executor Agent",
    title: "Test Executor Agent",
    description: "Runs the test suite.",
    patterns: ["agents.test_executor"],
  },
  {
    id: "failure_analyst",
    label: "Failure Analyst Agent",
    title: "Failure Analyst Agent",
    description: "Analyzes failures and suggests retries.",
    patterns: ["agents.failure_analyst"],
  },
  {
    id: "coverage_analyst",
    label: "Coverage Analyst Agent",
    title: "Coverage Analyst Agent",
    description: "Builds coverage reports.",
    patterns: ["agents.coverage_analyst"],
  },
];

function deriveEffectiveRunStatus(runStatus, latestResult) {
  const baseStatus = runStatus || emptyRunStatus;
  const logs = Array.isArray(baseStatus.logs) ? baseStatus.logs : [];
  const lastLogTimestamp = logs.length ? logs[logs.length - 1].timestamp || null : null;
  const messages = logs.map((entry) => String(entry.message || ""));
  const completionMarkers =
    baseStatus.run_mode === "real_coverage"
      ? realCoverageCompletionMarkers
      : pipelineOnlyCompletionMarkers;
  const hasCompletionMarker = messages.some((message) =>
    completionMarkers.some((marker) => message.includes(marker))
  );
  const hasFailureMarker = hasTerminalFailure(messages, baseStatus.run_mode);

  if (!baseStatus.is_running) {
    return baseStatus;
  }

  if (hasFailureMarker) {
    return {
      ...baseStatus,
      status: "failed",
      finished_at: baseStatus.finished_at || lastLogTimestamp,
      is_running: false,
      result: baseStatus.result || latestResult,
    };
  }

  if (hasCompletionMarker) {
    return {
      ...baseStatus,
      status: "completed",
      finished_at: baseStatus.finished_at || lastLogTimestamp,
      is_running: false,
      result: baseStatus.result || latestResult,
    };
  }

  return baseStatus;
}

function deriveWorkflowTracker(runStatus) {
  const baseStatus = runStatus || emptyRunStatus;
  const logs = Array.isArray(baseStatus.logs) ? baseStatus.logs : [];
  const messages = logs.map((entry) => String(entry.message || ""));
  const completionMarkers =
    baseStatus.run_mode === "real_coverage"
      ? realCoverageCompletionMarkers
      : pipelineOnlyCompletionMarkers;
  const hasCompletionMarker = messages.some((message) =>
    completionMarkers.some((marker) => message.includes(marker))
  );
  const hasFailureMarker = hasTerminalFailure(messages, baseStatus.run_mode);

  let currentStageId = null;
  let currentAttempt = 1;
  let maxAttempts = 1;
  const seenStages = new Set();

  logs.forEach((entry) => {
    const message = String(entry.message || "");

    workflowStages.forEach((stage) => {
      if (stage.patterns.some((pattern) => message.includes(pattern))) {
        seenStages.add(stage.id);
        currentStageId = stage.id;
      }
    });

    const retryMatch = message.match(/attempt\s+(\d+)\/(\d+)/i);
    if (retryMatch) {
      const attemptNumber = Number(retryMatch[1]);
      const attemptLimit = Number(retryMatch[2]);
      if (!Number.isNaN(attemptNumber)) {
        currentAttempt = Math.max(currentAttempt, attemptNumber + 1);
      }
      if (!Number.isNaN(attemptLimit)) {
        maxAttempts = Math.max(maxAttempts, attemptLimit + 1);
      }
    }
  });

  if (baseStatus.is_running && !currentStageId) {
    currentStageId = workflowStages[0].id;
  }

  const isFinished = !baseStatus.is_running || hasCompletionMarker || hasFailureMarker;
  const stages = workflowStages.map((stage) => {
    if (hasFailureMarker && currentStageId === stage.id) {
      return { ...stage, state: "failed" };
    }
    if (isFinished) {
      return { ...stage, state: seenStages.has(stage.id) ? "completed" : "pending" };
    }
    if (currentStageId === stage.id) {
      return { ...stage, state: "active" };
    }
    if (seenStages.has(stage.id)) {
      return { ...stage, state: "completed" };
    }
    return { ...stage, state: "pending" };
  });

  return {
    activeStage: stages.find((stage) => stage.state === "active") || null,
    completedCount: stages.filter((stage) => stage.state === "completed").length,
    currentAttempt,
    maxAttempts,
    stages,
  };
}

function VortexLogo() {
  return (
    <div
      aria-label="VORTEX"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.9rem",
      }}
    >
      <div
        style={{
          width: "3rem",
          height: "3rem",
          borderRadius: "1rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background:
            "linear-gradient(135deg, rgba(14, 165, 233, 1) 0%, rgba(34, 211, 238, 0.95) 52%, rgba(15, 23, 42, 1) 100%)",
          boxShadow: "0 14px 34px rgba(14, 165, 233, 0.28)",
        }}
      >
        <svg
          viewBox="0 0 64 64"
          width="28"
          height="28"
          role="img"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="vortex-mark" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f8fafc" />
              <stop offset="100%" stopColor="#dbeafe" />
            </linearGradient>
          </defs>
          <path
            d="M14 13h9.4L32 40.2 40.6 13H50L36.1 51H27.9L14 13Z"
            fill="url(#vortex-mark)"
          />
          <path
            d="M20 13 32 48 44 13"
            fill="none"
            stroke="#ffffff"
            strokeWidth="3.5"
            strokeLinejoin="round"
            opacity="0.58"
          />
        </svg>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.12rem" }}>
        <span
          style={{
            fontSize: "0.72rem",
            letterSpacing: "0.38em",
            fontWeight: 700,
            color: "#0f172a",
            textTransform: "uppercase",
          }}
        >
          VORTEX
        </span>
        <span
          style={{
            fontSize: "0.85rem",
            color: "#475569",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          Automation Hub
        </span>
      </div>
    </div>
  );
}

function getWorkflowLinkState(stage, nextStage) {
  if (!nextStage) {
    return "pending";
  }
  if (stage.state === "failed" || nextStage.state === "failed") {
    return "failed";
  }
  if (stage.state === "active" || nextStage.state === "active") {
    return "active";
  }
  if (stage.state === "completed" && nextStage.state !== "pending") {
    return "completed";
  }
  if (stage.state === "completed") {
    return "completed";
  }
  return "pending";
}

function App() {
  const [services, setServices] = useState([]);
  const [globalConfig, setGlobalConfig] = useState(blankGlobal);
  const [userStoryText, setUserStoryText] = useState("");
  const [businessRequirementsText, setBusinessRequirementsText] = useState("");
  const [runStatus, setRunStatus] = useState(emptyRunStatus);
  const [latestResult, setLatestResult] = useState({ summary: {}, artifacts: [] });
  const [runMode, setRunMode] = useState("real_coverage");
  const [selectedServiceCount, setSelectedServiceCount] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const wasRunInProgress = useRef(false);
  const effectiveRunStatus = useMemo(
    () => deriveEffectiveRunStatus(runStatus, latestResult),
    [runStatus, latestResult]
  );
  const workflowTracker = useMemo(
    () => deriveWorkflowTracker(effectiveRunStatus),
    [effectiveRunStatus]
  );

  useEffect(() => {
    loadState();
  }, []);

  useEffect(() => {
    if (!effectiveRunStatus.is_running) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      fetchRunStatus();
    }, 2000);

    return () => window.clearInterval(timer);
  }, [effectiveRunStatus.is_running]);

  useEffect(() => {
    if (effectiveRunStatus.is_running) {
      wasRunInProgress.current = true;
      return;
    }

    if (!wasRunInProgress.current) {
      return;
    }

    wasRunInProgress.current = false;

    if (effectiveRunStatus.status === "completed") {
      setMessage("Execution completed.");
      return;
    }

    if (effectiveRunStatus.status === "failed") {
      setError("Execution completed with failures. Check the latest summary and logs.");
    }
  }, [effectiveRunStatus.is_running, effectiveRunStatus.status]);

  useEffect(() => {
    const runnable = getRunnableServices(services);
    if (!runnable.length) {
      setSelectedServiceCount(0);
      return;
    }

    setSelectedServiceCount((current) => {
      if (current < 1) {
        return 1;
      }
      if (current > runnable.length) {
        return runnable.length;
      }
      return current;
    });
  }, [services]);

  async function loadState() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/state");
      if (!response.ok) {
        throw new Error("Unable to load frontend state.");
      }

      const data = await response.json();
      hydrateFromResponse(data);
    } catch (loadError) {
      setError(loadError.message || "Failed to load state.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchRunStatus() {
    try {
      const response = await fetch("/api/run-status");
      if (!response.ok) {
        throw new Error("Failed to fetch run status.");
      }
      const data = await response.json();
      setRunStatus(data);
      setRunMode(data.run_mode || "real_coverage");
      if (data.latest_result) {
        setLatestResult(data.latest_result);
      } else if (data.result) {
        setLatestResult((current) => getBestResult(data.result, current));
      }
      setError("");
      return data;
    } catch (statusError) {
      setError(statusError.message || "Failed to fetch run status.");
      return null;
    }
  }

  function hydrateFromResponse(data) {
    const incomingServices = Array.isArray(data.services)
      ? data.services.map((service, index) => withServiceUiId(service, index))
      : [];
    setServices(incomingServices);
    setGlobalConfig({
      ...blankGlobal,
      ...(data.global || {}),
      jwt: {
        ...blankGlobal.jwt,
        ...((data.global || {}).jwt || {}),
        credentials: {
          ...blankGlobal.jwt.credentials,
          ...(((data.global || {}).jwt || {}).credentials || {}),
        },
      },
      maven: {
        ...blankGlobal.maven,
        ...((data.global || {}).maven || {}),
      },
    });
    setUserStoryText(data.user_story_text || "");
    setBusinessRequirementsText(data.business_requirements_text || "");
    setRunStatus(data.run_status || emptyRunStatus);
    setRunMode((data.run_status && data.run_status.run_mode) || "real_coverage");
    setLatestResult(data.latest_result || { summary: {}, artifacts: [] });

    const enabledCount = incomingServices.filter((service) => service.enabled).length;
    setSelectedServiceCount(enabledCount ? enabledCount : 0);
  }

  function buildPayload() {
    return {
      services,
      global: globalConfig,
      user_story_text: userStoryText,
      business_requirements_text: businessRequirementsText,
    };
  }

  async function saveConfig() {
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to save configuration.");
      }

      hydrateFromResponse(data);
      setMessage("Configuration saved.");
    } catch (saveError) {
      setError(saveError.message || "Failed to save configuration.");
    } finally {
      setSaving(false);
    }
  }

  async function runPipeline() {
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const runnableServices = getRunnableServices(services).map((service) => service.name);
      const selectedServices = runnableServices.slice(0, selectedServiceCount || runnableServices.length);

      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...buildPayload(),
          selected_services: selectedServices,
          run_mode: runMode,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        if (response.status === 409) {
          const refreshedStatus = await fetchRunStatus();
          if (refreshedStatus && !refreshedStatus.is_running) {
            setMessage("The previous run just finished. You can launch a new run now.");
            return;
          }
        }
        throw new Error(data.error || "Failed to start pipeline.");
      }

      setRunStatus(data);
      setRunMode(data.run_mode || runMode);
      setMessage("Execution started.");
    } catch (runError) {
      setError(runError.message || "Failed to start pipeline.");
    } finally {
      setSaving(false);
    }
  }

  function updateService(index, field, value) {
    setServices((current) =>
      current.map((service, currentIndex) =>
        currentIndex === index ? { ...service, [field]: value } : service
      )
    );
  }

  function addService() {
    const nextNumber = services.length + 1;
    setServices((current) => [
      ...current,
      {
        ui_id: `service-${Date.now()}-${nextNumber}`,
        original_name: "",
        name: `service_${nextNumber}`,
        enabled: true,
        port: 9000 + nextNumber,
        base_url: `http://localhost:${9000 + nextNumber}`,
        swagger_spec: "",
        swagger_url: "",
        role: "custom_service",
        dependencies: [],
      },
    ]);
  }

  function removeService(index) {
    setServices((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  function updateGlobal(section, field, value) {
    setGlobalConfig((current) => {
      if (!section) {
        return { ...current, [field]: value };
      }

      if (section === "jwt.credentials") {
        return {
          ...current,
          jwt: {
            ...current.jwt,
            credentials: {
              ...current.jwt.credentials,
              [field]: value,
            },
          },
        };
      }

      return {
        ...current,
        [section]: {
          ...current[section],
          [field]: value,
        },
      };
    });
  }

  const runnableServices = useMemo(
    () => getRunnableServices(services),
    [services]
  );

  const selectedServicesForRun = useMemo(() => {
    if (!runnableServices.length) {
      return [];
    }
    return runnableServices.slice(0, selectedServiceCount || runnableServices.length).map((service) => service.name);
  }, [runnableServices, selectedServiceCount]);

  const activeRunStatus = effectiveRunStatus;
  const isRunInProgress = activeRunStatus.is_running;
  const hasCompletedRun =
    activeRunStatus.status === "completed" || activeRunStatus.status === "failed";
  const displayResult = hasCompletedRun && !isRunInProgress
    ? getBestResult(activeRunStatus.result, latestResult)
    : null;
  const hasDisplayResult = Boolean(displayResult?.summary && Object.keys(displayResult.summary).length);
  const activeSummarySource = !hasDisplayResult
    ? {}
    : displayResult.summary || {};
  const summary = activeSummarySource.summary || activeSummarySource;
  const aggregate = summary.aggregate || {};
  const testExecution = summary.test_execution || {};
  const qualityGate = summary.quality_gate || {};
  const artifacts = !hasDisplayResult
    ? []
    : displayResult.artifacts || [];
  const currentStatus = activeRunStatus.status || "idle";
  const currentStatusTone = error
    ? "danger"
    : activeRunStatus.is_running
      ? "info"
      : currentStatus === "completed"
        ? "success"
        : "neutral";
  const lineCoverageValue = !hasDisplayResult
    ? "--"
    : `${aggregate.lines?.["rate_%"] ?? 0}%`;

  if (loading) {
    return (
      <div className="mx-auto flex min-h-screen max-w-7xl items-center justify-center px-6 py-12">
        <div className="glass-panel panel-pad w-full max-w-2xl text-center">
          <p className="eyebrow">Loading</p>
          <h1 className="hero-title mt-4">Preparing the sky-blue dashboard</h1>
          <p className="hero-copy mt-4">
            We are loading your saved services, run settings, and the latest execution snapshot.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-shell mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <section className="glass-panel overflow-hidden">
        <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1.25fr_0.95fr] lg:px-8">
          <div>
            <VortexLogo />
            <h1 className="hero-title mt-4 sm:text-5xl">
              Multi-agent test automation and coverage dashboard
            </h1>
            <p className="hero-copy mt-4 max-w-3xl">
              Manage your microservices test matrix, launch end-to-end and real coverage runs,
              monitor live execution logs, and review generated reports and artifacts in one place.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <span className="tag-chip">Coverage orchestration</span>
              <span className="tag-chip">Run mode: {runMode}</span>
              <span className="tag-chip">Available services: {runnableServices.length}</span>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <MetricCard label="Available Services" value={runnableServices.length} />
            <MetricCard
              label="Selected For Run"
              value={selectedServicesForRun.length}
              tone="sky"
            />
            <MetricCard
              label="Pipeline Status"
              value={currentStatus}
              tone={activeRunStatus.is_running ? "sky" : "neutral"}
            />
            <MetricCard
              label="Line Coverage"
              value={lineCoverageValue}
              tone="neutral"
            />
          </div>
        </div>
      </section>

      {(message || error) && (
        <section className={`status-banner mt-6 ${currentStatusTone}`}>
          <strong>{error ? error : message}</strong>
        </section>
      )}

      <section className="mt-6 glass-panel panel-pad">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="eyebrow">Workflow Tracker</p>
            <h2 className="section-title mt-2">Agent Progression</h2>
            <p className="hero-copy mt-3 max-w-3xl">
              {workflowTracker.activeStage
                ? `${workflowTracker.activeStage.label} is currently active.`
                : currentStatus === "completed"
                  ? "The workflow finished and the completed stages are highlighted below."
                  : currentStatus === "failed"
                    ? "The workflow stopped on a failed stage."
                    : "Start a run to watch the agents progress live."}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <span className="tag-chip">
              Completed: {workflowTracker.completedCount}/{workflowTracker.stages.length}
            </span>
            <span className="tag-chip">
              Coverage loop: {workflowTracker.currentAttempt}/{workflowTracker.maxAttempts}
            </span>
          </div>
        </div>

        <div className="workflow-chain mt-6">
          {workflowTracker.stages.map((stage, index) => {
            const nextStage = workflowTracker.stages[index + 1];

            return (
              <div key={stage.id} className="workflow-chain-node">
                <WorkflowStageCard index={index} stage={stage} />
                {nextStage ? (
                  <div
                    className={`workflow-chain-link ${getWorkflowLinkState(stage, nextStage)}`}
                    aria-hidden="true"
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <article className="glass-panel panel-pad">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="eyebrow">Services Matrix</p>
              <h2 className="section-title mt-2">Microservices</h2>
            </div>

            <div className="flex flex-wrap gap-3">
              <button className="secondary-button" type="button" onClick={addService}>
                Add Service
              </button>
              <button className="secondary-button" type="button" onClick={saveConfig} disabled={saving}>
                Save Inputs
              </button>
              <button
                className="primary-button"
                type="button"
                onClick={runPipeline}
                disabled={saving || activeRunStatus.is_running || !selectedServicesForRun.length}
              >
                {activeRunStatus.is_running ? "Running..." : "Execute Tests"}
              </button>
            </div>
          </div>

          <div className="mt-6 grid gap-5 md:grid-cols-2">
            {services.map((service, index) => (
              <ServiceCard
                key={service.ui_id || service.original_name || `service-${index}`}
                service={service}
                index={index}
                allServices={services}
                onChange={updateService}
                onRemove={removeService}
              />
            ))}
          </div>
        </article>

        <article className="glass-panel panel-pad">
          <p className="eyebrow">Execution Inputs</p>
          <h2 className="section-title mt-2">Run Settings</h2>

          <div className="mt-5 space-y-4">
            <Field label="How Many Microservices To Test">
              <select
                className="field-input"
                value={selectedServiceCount}
                onChange={(event) => setSelectedServiceCount(Number(event.target.value))}
                disabled={!runnableServices.length}
              >
                {!runnableServices.length ? <option value={0}>0 services configured</option> : null}
                {Array.from({ length: runnableServices.length }, (_, index) => index + 1).map((count) => (
                  <option key={count} value={count}>
                    {count}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Services Included In This Run">
              <div className="soft-panel text-sm">
                {selectedServicesForRun.length ? selectedServicesForRun.join(", ") : "No services configured."}
              </div>
            </Field>

            <Field label="JWT Login URL">
              <input
                className="field-input"
                value={globalConfig.jwt.login_url}
                onChange={(event) => updateGlobal("jwt", "login_url", event.target.value)}
              />
            </Field>

            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Login Email">
                <input
                  className="field-input"
                  value={globalConfig.jwt.credentials.email}
                  onChange={(event) => updateGlobal("jwt.credentials", "email", event.target.value)}
                />
              </Field>

              <Field label="Login Password">
                <input
                  className="field-input"
                  value={globalConfig.jwt.credentials.password}
                  onChange={(event) => updateGlobal("jwt.credentials", "password", event.target.value)}
                />
              </Field>
            </div>

            <Field label="JWT Token">
              <textarea
                className="field-input min-h-28"
                value={globalConfig.jwt.env_var}
                onChange={(event) => updateGlobal("jwt", "env_var", event.target.value)}
              />
            </Field>

          </div>
        </article>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.2fr_1fr]">
        <article className="glass-panel panel-pad">
          <p className="eyebrow">Requirements</p>
          <h2 className="section-title mt-2">Input Documents</h2>

          <div className="mt-5 space-y-5">
            <Field label="User Story">
              <textarea
                className="field-input min-h-52"
                value={userStoryText}
                onChange={(event) => setUserStoryText(event.target.value)}
              />
            </Field>

            <Field label="Business Requirements YAML">
              <textarea
                className="field-input min-h-80"
                value={businessRequirementsText}
                onChange={(event) => setBusinessRequirementsText(event.target.value)}
              />
            </Field>
          </div>
        </article>

        <article className="glass-panel panel-pad">
          <p className="eyebrow">Execution Result</p>
          <h2 className="section-title mt-2">Latest Summary</h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <SummaryTile label="Bundle" value={!hasDisplayResult ? "--" : summary.service || "n/a"} />
            <SummaryTile label="Generated At" value={!hasDisplayResult ? "--" : summary.generated_at || "n/a"} />
            <SummaryTile label="Failures" value={!hasDisplayResult ? "--" : testExecution.failures ?? 0} />
            <SummaryTile
              label="Quality Gate"
              value={!hasDisplayResult ? "--" : qualityGate.passed ? "passed" : "failed"}
            />
          </div>

          <div className="mt-6 space-y-4">
            <CoverageBar label="Line Coverage" value={!hasDisplayResult ? 0 : aggregate.lines?.["rate_%"] ?? 0} />
            <CoverageBar label="Branch Coverage" value={!hasDisplayResult ? 0 : aggregate.branches?.["rate_%"] ?? 0} />
            <CoverageBar label="Method Coverage" value={!hasDisplayResult ? 0 : aggregate.methods?.["rate_%"] ?? 0} />
          </div>

          <div className="mt-6">
            <p className="eyebrow">Artifacts</p>
            {artifacts.length ? (
              <ul className="mt-3 space-y-3 text-sm text-slate-700">
                {artifacts.map((artifact) => (
                  <li key={artifact.path}>
                    <a className="artifact-link" href={artifact.url} target="_blank" rel="noreferrer">
                      {artifact.path}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="soft-panel mt-3 text-sm">
                {isRunInProgress
                  ? "Results will appear after the current run finishes."
                  : "No results for the current session yet."}
              </div>
            )}
          </div>
        </article>
      </section>

      <section className="mt-6">
        <article className="glass-panel panel-pad">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="eyebrow">Live Logs</p>
              <h2 className="section-title mt-2">Pipeline Console</h2>
            </div>
            <span className={`status-pill ${currentStatusTone}`}>
              {currentStatus}
            </span>
          </div>

          <div className="console-panel mt-5 h-[32rem] overflow-auto p-4 font-mono text-sm">
            {activeRunStatus.logs.length ? (
              activeRunStatus.logs.map((entry, index) => (
                <div key={`${entry.timestamp}-${index}`} className="mb-2 whitespace-pre-wrap break-words">
                  <span
                    className={
                      entry.source === "stderr"
                        ? "text-red-300"
                        : entry.source === "system"
                          ? "text-sky-700"
                          : "text-slate-800"
                    }
                  >
                    [{entry.source}]
                  </span>{" "}
                  {entry.message}
                </div>
              ))
            ) : (
              <div>No pipeline logs yet.</div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}

function WorkflowStageCard({ stage, index }) {
  const isActive = stage.state === "active";
  const isCompleted = stage.state === "completed";
  const isFailed = stage.state === "failed";

  return (
    <article className={`workflow-stage-card ${stage.state}`} aria-current={isActive ? "step" : undefined}>
      <div className="workflow-stage-header">
        <span className={`workflow-stage-dot ${stage.state} ${isActive ? "animate-pulse" : ""}`}>
          {isCompleted ? "OK" : isFailed ? "!" : index + 1}
        </span>

        <div className="workflow-stage-copy">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
            Step {index + 1}
          </p>
          <h3 className="workflow-stage-title">{stage.title}</h3>
          <p className="workflow-stage-label">{stage.label}</p>
        </div>
      </div>

      <p className="workflow-stage-description">{stage.description}</p>

      <div className="workflow-stage-footer">
        <span className={`workflow-stage-badge ${stage.state}`}>
          {isActive ? "Active now" : isCompleted ? "Completed" : isFailed ? "Failed" : "Pending"}
        </span>
      </div>
    </article>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>
      {children}
    </label>
  );
}

function MetricCard({ label, value, tone = "neutral" }) {
  const accent =
    tone === "sky"
      ? "text-sky-700"
      : "text-slate-900";

  return (
    <div className="metric-card">
      <p className="text-sm text-slate-600">{label}</p>
      <p className={`mt-3 text-3xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function SummaryTile({ label, value }) {
  return (
    <div className="summary-card">
      <p className="text-sm text-slate-600">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function CoverageBar({ label, value }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm text-slate-700">
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <div className="h-3 rounded-full bg-sky-100/80">
        <div
          className="h-3 rounded-full bg-linear-to-r from-sky-400 via-cyan-300 to-sky-200"
          style={{ width: `${Math.max(4, value)}%` }}
        />
      </div>
    </div>
  );
}

function ServiceCard({ service, allServices, onChange, onRemove, index }) {
  const dependencyOptions = allServices
    .map((entry) => entry.name)
    .filter((name) => name && name !== service.name);

  return (
    <div className="service-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">{service.name || "Unnamed service"}</h3>
          <p className="mt-1 text-sm text-slate-600">{service.role || "custom role"}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-white/70 px-4 py-2 text-sm text-sky-900 shadow-sm">
            <input
              type="checkbox"
              checked={service.enabled}
              onChange={(event) => onChange(index, "enabled", event.target.checked)}
            />
            <span>{service.enabled ? "Enabled" : "Disabled"}</span>
          </label>
          <button className="danger-button" type="button" onClick={() => onRemove(index)}>
            Remove
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <Field label="Service Name">
          <input className="field-input" value={service.name} onChange={(event) => onChange(index, "name", event.target.value)} />
        </Field>

        <Field label="Port">
          <input
            className="field-input"
            type="number"
            value={service.port}
            onChange={(event) => onChange(index, "port", Number(event.target.value))}
          />
        </Field>

        <div className="md:col-span-2">
          <Field label="Base URL">
            <input
              className="field-input"
              value={service.base_url}
              onChange={(event) => onChange(index, "base_url", event.target.value)}
            />
          </Field>
        </div>

        <div className="md:col-span-2">
          <Field label="Swagger URL">
            <input
              className="field-input"
              value={service.swagger_url}
              onChange={(event) => onChange(index, "swagger_url", event.target.value)}
            />
          </Field>
        </div>

        <div className="md:col-span-2">
          <Field label="Role">
            <input className="field-input" value={service.role} onChange={(event) => onChange(index, "role", event.target.value)} />
          </Field>
        </div>

        <div className="md:col-span-2">
          <Field label="Dependencies">
            <select
              className="field-input min-h-32"
              multiple
              value={service.dependencies || []}
              onChange={(event) => {
                const values = Array.from(event.target.selectedOptions, (option) => option.value);
                onChange(index, "dependencies", values);
              }}
            >
              {dependencyOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </div>
    </div>
  );
}

export default App;
