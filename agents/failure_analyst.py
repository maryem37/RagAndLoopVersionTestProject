"""
agents/failure_analyst.py
-------------------------
Agent: Failure Analyst

Reads the latest execution result plus any available Cucumber JSON report and
produces a structured failure analysis that downstream nodes can use for
bounded self-healing retries.
"""

from __future__ import annotations

import os
import re
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from config.settings import get_settings
from graph.state import AgentOutput, AgentStatus, TestAutomationState
from tools.analyze_cucumber_failures import analyze as analyze_cucumber_report


class FailureAnalystAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        logger.info("Failure Analyst initialized")

    def _max_healing_attempts(self, state: TestAutomationState) -> int:
        cfg = getattr(state, "config", {}) or {}
        raw = cfg.get("max_healing_attempts", os.getenv("MAX_HEALING_ATTEMPTS", "3"))
        try:
            value = int(raw)
        except Exception:
            value = 3
        return max(0, value)

    def _find_cucumber_json(self, state: TestAutomationState) -> Optional[Path]:
        execution = getattr(state, "execution_result", None) or {}
        report_path = execution.get("report_path")
        candidates: list[Path] = []

        if report_path:
            p = Path(report_path)
            if p.suffix.lower() == ".json":
                candidates.append(p)
            elif p.suffix.lower() == ".html":
                candidates.append(p.with_name("cucumber.json"))
            candidates.append(p.parent / "cucumber.json")

        tests_dir = Path(self.settings.paths.tests_dir)
        reports_root = tests_dir / "target" / "cucumber-reports"
        candidates.append(reports_root / "cucumber.json")
        candidates.extend(sorted(reports_root.glob("*/cucumber.json")))

        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate.resolve()) if candidate.exists() else str(candidate)
            if key in seen:
                continue
            seen.add(key)
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _classify_failure(
        self,
        execution_result: Dict[str, Any],
        cucumber_summary: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        raw_output = str(execution_result.get("raw_output_tail", "") or "")
        hints = [str(h) for h in execution_result.get("hints", []) or []]
        errors = [str(e) for e in execution_result.get("errors", []) or []]
        total = int(execution_result.get("total", 0) or 0)
        failed = int(execution_result.get("failed", 0) or 0)

        code_counts = {}
        if cucumber_summary and cucumber_summary.get("code_counts"):
            code_counts = {
                str(code): int(count)
                for code, count in cucumber_summary["code_counts"].items()
            }

        step_counts = cucumber_summary.get("step_counts") if cucumber_summary else {}
        top_step_names = [str(name).lower() for name, _ in step_counts.most_common(10)] if step_counts else []

        combined = "\n".join([raw_output, *hints, *errors, *top_step_names]).lower()

        auth_signals = any(
            token in combined
            for token in [
                "expired token",
                "jwt",
                "unauthorized",
                "forbidden",
                "without jwt",
                "without token",
                "authentication",
                "401 unauthorized",
                "403 forbidden",
            ]
        )
        business_flow_signals = any(
            token in combined
            for token in [
                "approve pending leave request",
                "reject pending leave request",
                "validation authority",
                "already been rejected",
                "leave request",
                "/approve",
                "/reject",
                "/create",
                "other user's leave request",
                "future dates",
            ]
        )
        server_signals = "500" in code_counts or "internal server error" in combined
        contract_signals = "404" in code_counts or "not found" in combined
        compile_signals = any(
            token in combined
            for token in [
                "compilation failure",
                "compilation error",
                "cannot find symbol",
                "classnotfoundexception",
                "noclassdeffounderror",
            ]
        )
        infrastructure_signals = any(
            token in combined
            for token in [
                "connection refused",
                "connectexception",
                "backend service",
                " port ",
                "timed out after 300s",
                "execution timeout exceeded",
            ]
        )

        category = "assertion_mismatch"
        retry_recommended = failed > 0
        retry_target = "test_writer"
        reason = "Failed scenarios should be regenerated with failure feedback."

        if total == 0:
            category = "no_tests_executed"
            retry_recommended = False
            retry_target = "none"
            reason = "No scenarios ran, so rerunning generated tests would likely repeat the same result."
        elif infrastructure_signals:
            category = "infrastructure"
            retry_recommended = False
            retry_target = "none"
            reason = "Backend/service availability issue detected; fix the environment before retrying."
        elif any(token in combined for token in ["undefined step", "pendingexception"]):
            category = "undefined_steps"
            reason = "Undefined Cucumber steps detected; regenerate step definitions with focused feedback."
        elif compile_signals:
            category = "java_generation"
            reason = "Generated Java test code failed to compile; regenerate test code with targeted repair context."
        elif business_flow_signals and (auth_signals or server_signals or contract_signals):
            category = "mixed_business_flow"
            reason = (
                "Business-flow failures were detected alongside auth/server issues; "
                "retry with failure-guided test regeneration."
            )
        elif business_flow_signals:
            category = "business_flow"
            reason = "Approval/rejection/create-flow failures detected; regenerate tests with targeted repair context."
        elif auth_signals and not (business_flow_signals or server_signals or contract_signals):
            category = "authentication"
            retry_recommended = False
            retry_target = "none"
            reason = "Authentication/authorization failure detected with no competing business-flow signals."
        elif contract_signals:
            category = "contract_mismatch"
            reason = "Endpoint or contract mismatch detected; regenerate tests against the observed failing paths."
        elif server_signals:
            category = "server_error"
            reason = "Server-side failures detected; try one repair pass in case the generated flow or test data is wrong."

        return {
            "failure_category": category,
            "retry_recommended": retry_recommended,
            "retry_target": retry_target,
            "reason": reason,
        }

    def analyze(self, state: TestAutomationState) -> TestAutomationState:
        start = time.time()
        logger.info(f"[START] Failure Analyst starting — service: {state.service_name}")

        try:
            execution = getattr(state, "execution_result", None) or {}
            cucumber_path = self._find_cucumber_json(state)
            cucumber_summary: Optional[Dict[str, Any]] = None
            if cucumber_path:
                try:
                    cucumber_summary = analyze_cucumber_report(cucumber_path)
                    logger.info(f"   Parsed Cucumber JSON for failure analysis: {cucumber_path}")
                except Exception as exc:
                    logger.warning(f"   Could not analyze Cucumber JSON {cucumber_path}: {exc}")

            classification = self._classify_failure(execution, cucumber_summary)
            step_counts = cucumber_summary.get("step_counts") if cucumber_summary else {}
            code_counts = cucumber_summary.get("code_counts") if cucumber_summary else {}

            top_failed_steps = [name for name, _ in step_counts.most_common(8)] if step_counts else []
            top_http_codes = [
                {"code": str(code), "count": int(count)}
                for code, count in code_counts.most_common()
            ] if code_counts else []

            max_attempts = self._max_healing_attempts(state)
            attempt_number = len(state.healing_attempts) + 1

            analysis: Dict[str, Any] = {
                "attempt_number": attempt_number,
                "max_attempts": max_attempts,
                "retry_recommended": classification["retry_recommended"],
                "retry_target": classification["retry_target"],
                "failure_category": classification["failure_category"],
                "reason": classification["reason"],
                "execution_summary": {
                    "total": int(execution.get("total", 0) or 0),
                    "passed": int(execution.get("passed", 0) or 0),
                    "failed": int(execution.get("failed", 0) or 0),
                    "skipped": int(execution.get("skipped", 0) or 0),
                    "pass_rate": float(execution.get("pass_rate", 0.0) or 0.0),
                },
                "top_failed_steps": top_failed_steps,
                "top_http_codes": top_http_codes,
                "cucumber_report": str(cucumber_path) if cucumber_path else None,
                "executor_hints": [str(h) for h in execution.get("hints", []) or []],
                "executor_errors": [str(e) for e in execution.get("errors", []) or []][:10],
                "raw_output_tail": str(execution.get("raw_output_tail", "") or "")[-1500:],
            }

            state.failure_analysis = analysis
            state.failed_tests = top_failed_steps
            state.healing_attempts.append(analysis)

            if analysis["retry_recommended"]:
                state.add_warning(
                    f"Failure analysis recommends retry via {analysis['retry_target']}: {analysis['failure_category']}"
                )
            else:
                state.add_warning(
                    f"Failure analysis stopped retry: {analysis['failure_category']} — {analysis['reason']}"
                )

            duration_ms = (time.time() - start) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="failure_analyst",
                status=AgentStatus.SUCCESS,
                duration_ms=duration_ms,
                output_data={
                    "failure_category": analysis["failure_category"],
                    "retry_recommended": analysis["retry_recommended"],
                    "retry_target": analysis["retry_target"],
                    "attempt_number": attempt_number,
                    "max_attempts": max_attempts,
                    "top_failed_steps": top_failed_steps[:5],
                    "top_http_codes": top_http_codes,
                    "cucumber_report": analysis["cucumber_report"],
                },
            ))
            logger.success(
                f"Failure Analyst finished in {duration_ms:.0f}ms "
                f"[category={analysis['failure_category']} retry={analysis['retry_recommended']}]"
            )

        except Exception:
            duration_ms = (time.time() - start) * 1000
            tb = traceback.format_exc()
            logger.error(f"[ERROR] Failure Analyst failed:\n{tb}")
            state.add_agent_output(AgentOutput(
                agent_name="failure_analyst",
                status=AgentStatus.FAILED,
                duration_ms=duration_ms,
                error_message=tb,
            ))
            state.add_error(f"Failure analysis failed: {tb}")

        return state


def failure_analyst_node(state: TestAutomationState) -> TestAutomationState:
    return FailureAnalystAgent().analyze(state)
