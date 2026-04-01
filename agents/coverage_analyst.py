"""
agents/coverage_analyst.py
------------------------------
Agent 6 — Coverage Analyst (JaCoCo + Structured Report)

ROLE:
  After test execution (Agent 5), this agent:
    1. Locates JaCoCo XML/CSV reports produced by Maven (surefire + jacoco plugin)
    2. Parses line coverage, branch coverage, method coverage per class
    3. Computes aggregate project-level metrics
    4. Emits a structured YAML + JSON report ready for a quality dashboard
    5. Optionally flags classes below configurable coverage thresholds

DESIGN PRINCIPLES (consistent with the rest of the pipeline):
  - Zero hardcoded class/package names — everything is read from JaCoCo output
  - Works for ANY microservice — auth, leave, or any future service
  - Graceful degradation: if JaCoCo XML is absent, falls back to Surefire XML
    then to raw Maven console output (regex-based heuristic)
  - No LLM involved — coverage numbers are deterministic facts, not generated text
  - All file I/O uses explicit encoding="utf-8"

OUTPUT FILES (written to settings.paths.reports_dir):
  coverage_report_<service>_<timestamp>.yaml   ← human-readable quality dashboard
  coverage_report_<service>_<timestamp>.json   ← machine-readable for CI pipelines

PIPELINE POSITION:
  test_executor -> coverage_analyst -> END
"""

from __future__ import annotations

import json
import os
import re
import time
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger

from config.settings import get_settings
from graph.state import AgentOutput, AgentStatus, TestAutomationState


# ------------------------------
# Data models (plain dataclasses — no Pydantic dependency added)
# ------------------------------

class ClassCoverage:
    """Coverage metrics for a single Java class."""

    __slots__ = (
        "class_name", "package", "source_file",
        "line_covered", "line_missed",
        "branch_covered", "branch_missed",
        "method_covered", "method_missed",
        "complexity",
    )

    def __init__(
        self,
        class_name:     str,
        package:        str  = "",
        source_file:    str  = "",
        line_covered:   int  = 0,
        line_missed:    int  = 0,
        branch_covered: int  = 0,
        branch_missed:  int  = 0,
        method_covered: int  = 0,
        method_missed:  int  = 0,
        complexity:     int  = 0,
    ) -> None:
        self.class_name     = class_name
        self.package        = package
        self.source_file    = source_file
        self.line_covered   = line_covered
        self.line_missed    = line_missed
        self.branch_covered = branch_covered
        self.branch_missed  = branch_missed
        self.method_covered = method_covered
        self.method_missed  = method_missed
        self.complexity     = complexity

    @property
    def line_rate(self) -> float:
        total = self.line_covered + self.line_missed
        return round(self.line_covered / total * 100, 2) if total else 0.0

    @property
    def branch_rate(self) -> float:
        total = self.branch_covered + self.branch_missed
        return round(self.branch_covered / total * 100, 2) if total else 0.0

    @property
    def method_rate(self) -> float:
        total = self.method_covered + self.method_missed
        return round(self.method_covered / total * 100, 2) if total else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class":          self.class_name,
            "package":        self.package,
            "source_file":    self.source_file,
            "lines": {
                "covered": self.line_covered,
                "missed":  self.line_missed,
                "rate_%":  self.line_rate,
            },
            "branches": {
                "covered": self.branch_covered,
                "missed":  self.branch_missed,
                "rate_%":  self.branch_rate,
            },
            "methods": {
                "covered": self.method_covered,
                "missed":  self.method_missed,
                "rate_%":  self.method_rate,
            },
            "complexity": self.complexity,
        }


class PackageCoverage:
    """Aggregated coverage for a Java package."""

    def __init__(self, name: str) -> None:
        self.name    = name
        self.classes: List[ClassCoverage] = []

    def add(self, cls: ClassCoverage) -> None:
        self.classes.append(cls)

    def _sum(self, attr: str) -> int:
        return sum(getattr(c, attr) for c in self.classes)

    @property
    def line_covered(self)   -> int: return self._sum("line_covered")
    @property
    def line_missed(self)    -> int: return self._sum("line_missed")
    @property
    def branch_covered(self) -> int: return self._sum("branch_covered")
    @property
    def branch_missed(self)  -> int: return self._sum("branch_missed")
    @property
    def method_covered(self) -> int: return self._sum("method_covered")
    @property
    def method_missed(self)  -> int: return self._sum("method_missed")

    def _rate(self, covered: int, missed: int) -> float:
        total = covered + missed
        return round(covered / total * 100, 2) if total else 0.0

    @property
    def line_rate(self)   -> float: return self._rate(self.line_covered,   self.line_missed)
    @property
    def branch_rate(self) -> float: return self._rate(self.branch_covered, self.branch_missed)
    @property
    def method_rate(self) -> float: return self._rate(self.method_covered, self.method_missed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package": self.name,
            "class_count": len(self.classes),
            "lines":    {"covered": self.line_covered,   "missed": self.line_missed,   "rate_%": self.line_rate},
            "branches": {"covered": self.branch_covered, "missed": self.branch_missed, "rate_%": self.branch_rate},
            "methods":  {"covered": self.method_covered, "missed": self.method_missed, "rate_%": self.method_rate},
            "classes":  [c.to_dict() for c in sorted(self.classes, key=lambda x: x.class_name)],
        }


class CoverageReport:
    """Top-level coverage report for the entire project."""

    def __init__(self, service_name: str, source: str = "jacoco-xml") -> None:
        self.service_name = service_name
        self.source       = source          # jacoco-xml | jacoco-csv | surefire | heuristic
        self.packages:    List[PackageCoverage] = []
        self.generated_at = datetime.now().isoformat(timespec="seconds")
        self.thresholds:  Dict[str, float] = {}
        self.threshold_violations: List[str] = []
        self.warnings:    List[str] = []
        self.test_summary: Dict[str, Any] = {}

    # ── Aggregate across all packages ------------------------------

    def _total(self, attr: str) -> int:
        return sum(getattr(p, attr) for p in self.packages)

    @property
    def total_line_covered(self)   -> int: return self._total("line_covered")
    @property
    def total_line_missed(self)    -> int: return self._total("line_missed")
    @property
    def total_branch_covered(self) -> int: return self._total("branch_covered")
    @property
    def total_branch_missed(self)  -> int: return self._total("branch_missed")
    @property
    def total_method_covered(self) -> int: return self._total("method_covered")
    @property
    def total_method_missed(self)  -> int: return self._total("method_missed")
    @property
    def total_classes(self)        -> int: return sum(len(p.classes) for p in self.packages)

    def _rate(self, covered: int, missed: int) -> float:
        total = covered + missed
        return round(covered / total * 100, 2) if total else 0.0

    @property
    def line_rate(self)   -> float: return self._rate(self.total_line_covered,   self.total_line_missed)
    @property
    def branch_rate(self) -> float: return self._rate(self.total_branch_covered, self.total_branch_missed)
    @property
    def method_rate(self) -> float: return self._rate(self.total_method_covered, self.total_method_missed)

    # ── Quality gate ------------------------------

    def apply_thresholds(self, thresholds: Dict[str, float]) -> None:
        self.thresholds = thresholds
        self.threshold_violations = []
        checks = {
            "line_coverage_%":   self.line_rate,
            "branch_coverage_%": self.branch_rate,
            "method_coverage_%": self.method_rate,
        }
        for key, actual in checks.items():
            minimum = thresholds.get(key, 0.0)
            if actual < minimum:
                self.threshold_violations.append(
                    f"{key}: {actual}% < threshold {minimum}%"
                )

    @property
    def quality_gate_passed(self) -> bool:
        return len(self.threshold_violations) == 0

    # ── Serialisation ------------------------------

    def to_dict(self) -> Dict[str, Any]:
        summary = {
            "service":      self.service_name,
            "generated_at": self.generated_at,
            "data_source":  self.source,
            "aggregate": {
                "total_classes":  self.total_classes,
                "total_packages": len(self.packages),
                "lines": {
                    "covered": self.total_line_covered,
                    "missed":  self.total_line_missed,
                    "rate_%":  self.line_rate,
                },
                "branches": {
                    "covered": self.total_branch_covered,
                    "missed":  self.total_branch_missed,
                    "rate_%":  self.branch_rate,
                },
                "methods": {
                    "covered": self.total_method_covered,
                    "missed":  self.total_method_missed,
                    "rate_%":  self.method_rate,
                },
            },
            "quality_gate": {
                "passed":     self.quality_gate_passed,
                "thresholds": self.thresholds,
                "violations": self.threshold_violations,
            },
        }
        if self.test_summary:
            summary["test_execution"] = self.test_summary
        if self.warnings:
            summary["warnings"] = self.warnings

        detail = [p.to_dict() for p in sorted(self.packages, key=lambda x: x.name)]
        return {"summary": summary, "packages": detail}

    def to_yaml(self) -> str:
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ------------------------------
# JaCoCo XML parser
# ------------------------------

def _counter(element: ET.Element, counter_type: str) -> Tuple[int, int]:
    """Extract (covered, missed) from a <counter type="X"> child element."""
    for child in element:
        if child.tag == "counter" and child.attrib.get("type", "").upper() == counter_type.upper():
            return int(child.attrib.get("covered", 0)), int(child.attrib.get("missed", 0))
    return 0, 0


def _parse_jacoco_xml(xml_path: Path) -> Optional[CoverageReport]:
    """
    Parse a JaCoCo XML report (jacoco.xml produced by jacoco-maven-plugin).

    Structure:
      <report>
        <package name="com/example/auth/steps">
          <class name="..." sourcefilename="...">
            <counter type="LINE" covered="N" missed="M"/>
            <counter type="BRANCH" .../>
            <counter type="METHOD" .../>
            <counter type="COMPLEXITY" .../>
          </class>
        </package>
        <counter type="LINE" .../>   ← project-level aggregate (we recompute)
      </report>
    """
    logger.info(f"   Parsing JaCoCo XML: {xml_path}")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        logger.warning(f"   XML parse error in {xml_path}: {exc}")
        return None

    # Infer service name from report name attribute
    service_name = root.attrib.get("name", xml_path.parent.parent.name)
    report = CoverageReport(service_name=service_name, source="jacoco-xml")

    for pkg_elem in root.iter("package"):
        pkg_name = pkg_elem.attrib.get("name", "").replace("/", ".")
        pkg      = PackageCoverage(name=pkg_name)

        for cls_elem in pkg_elem.iter("class"):
            raw_name     = cls_elem.attrib.get("name", "")
            source_file  = cls_elem.attrib.get("sourcefilename", "")
            # Strip package path prefix from class name
            simple_name  = raw_name.split("/")[-1] if "/" in raw_name else raw_name

            lc, lm = _counter(cls_elem, "LINE")
            bc, bm = _counter(cls_elem, "BRANCH")
            mc, mm = _counter(cls_elem, "METHOD")
            cc, _  = _counter(cls_elem, "COMPLEXITY")

            cls = ClassCoverage(
                class_name     = simple_name,
                package        = pkg_name,
                source_file    = source_file,
                line_covered   = lc,
                line_missed    = lm,
                branch_covered = bc,
                branch_missed  = bm,
                method_covered = mc,
                method_missed  = mm,
                complexity     = cc,
            )
            pkg.add(cls)

        if pkg.classes:
            report.packages.append(pkg)

    logger.info(
        f"   JaCoCo XML parsed: {report.total_classes} classes "
        f"across {len(report.packages)} packages"
    )
    return report if report.packages else None


# ------------------------------
# JaCoCo CSV parser (fallback if XML absent)
# ------------------------------

def _parse_jacoco_csv(csv_path: Path) -> Optional[CoverageReport]:
    """
    Parse jacoco.csv produced by jacoco-maven-plugin.

    CSV columns (standard JaCoCo):
      GROUP,PACKAGE,CLASS,INSTRUCTION_MISSED,INSTRUCTION_COVERED,
      BRANCH_MISSED,BRANCH_COVERED,LINE_MISSED,LINE_COVERED,
      COMPLEXITY_MISSED,COMPLEXITY_COVERED,METHOD_MISSED,METHOD_COVERED
    """
    logger.info(f"   Parsing JaCoCo CSV: {csv_path}")
    try:
        lines = csv_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning(f"   Cannot read CSV {csv_path}: {exc}")
        return None

    if not lines:
        return None

    header = [h.strip().upper() for h in lines[0].split(",")]

    def col(row: List[str], name: str) -> int:
        try:
            return int(row[header.index(name)].strip())
        except (ValueError, IndexError):
            return 0

    service_name = csv_path.parent.parent.name
    report  = CoverageReport(service_name=service_name, source="jacoco-csv")
    pkg_map: Dict[str, PackageCoverage] = {}

    for raw in lines[1:]:
        if not raw.strip():
            continue
        row = raw.split(",")
        if len(row) < len(header):
            continue

        pkg_name  = row[header.index("PACKAGE")].strip().replace("/", ".") if "PACKAGE" in header else "unknown"
        cls_name  = row[header.index("CLASS")].strip()  if "CLASS"   in header else "unknown"

        cls = ClassCoverage(
            class_name     = cls_name,
            package        = pkg_name,
            line_covered   = col(row, "LINE_COVERED"),
            line_missed    = col(row, "LINE_MISSED"),
            branch_covered = col(row, "BRANCH_COVERED"),
            branch_missed  = col(row, "BRANCH_MISSED"),
            method_covered = col(row, "METHOD_COVERED"),
            method_missed  = col(row, "METHOD_MISSED"),
            complexity     = col(row, "COMPLEXITY_COVERED") + col(row, "COMPLEXITY_MISSED"),
        )

        if pkg_name not in pkg_map:
            pkg_map[pkg_name] = PackageCoverage(name=pkg_name)
        pkg_map[pkg_name].add(cls)

    report.packages = list(pkg_map.values())
    logger.info(
        f"   JaCoCo CSV parsed: {report.total_classes} classes "
        f"across {len(report.packages)} packages"
    )
    return report if report.packages else None


# ------------------------------
# Surefire XML fallback
# ------------------------------

def _parse_surefire_xml(surefire_dir: Path) -> Dict[str, Any]:
    """
    Extract test counts from Surefire XML reports.
    Returns a dict suitable for report.test_summary.
    """
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time_s": 0.0}
    if not surefire_dir.exists():
        return totals
    for xml_file in surefire_dir.glob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            totals["tests"]    += int(root.attrib.get("tests",    0))
            totals["failures"] += int(root.attrib.get("failures", 0))
            totals["errors"]   += int(root.attrib.get("errors",   0))
            totals["skipped"]  += int(root.attrib.get("skipped",  0))
            totals["time_s"]   += float(root.attrib.get("time",   0))
        except Exception:
            pass
    totals["passed"]   = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    totals["time_s"]   = round(totals["time_s"], 3)
    return totals


# ------------------------------
# Heuristic fallback — parse Maven console output
# ------------------------------

_RE_SUREFIRE_LINE = re.compile(
    r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)",
    re.IGNORECASE,
)

def _heuristic_from_console(raw_output: str, service_name: str) -> CoverageReport:
    """
    When no JaCoCo reports exist, build a minimal coverage report from
    the Maven console output stored in state.execution_result.
    Coverage rates will be None (we cannot infer them without instrumentation).
    """
    report = CoverageReport(service_name=service_name, source="heuristic-console")
    report.warnings.append(
        "JaCoCo XML/CSV reports not found. "
        "Coverage metrics are unavailable — add jacoco-maven-plugin to pom.xml. "
        "Test execution counts derived from Maven console output."
    )

    tests = failures = errors = skipped = 0
    for m in _RE_SUREFIRE_LINE.finditer(raw_output):
        tests    += int(m.group(1))
        failures += int(m.group(2))
        errors   += int(m.group(3))
        skipped  += int(m.group(4))

    report.test_summary = {
        "tests":    tests,
        "passed":   max(0, tests - failures - errors - skipped),
        "failures": failures,
        "errors":   errors,
        "skipped":  skipped,
        "source":   "maven-console-regex",
    }
    return report


# ------------------------------
# Report locator — searches all known JaCoCo output paths
# ------------------------------

def _locate_jacoco_reports(tests_dir: Path) -> Dict[str, Optional[Path]]:
    """
    JaCoCo reports can land in several places depending on pom.xml config.
    Search all common locations, including safe backup location outside target/.
    """
    target = tests_dir / "target"
    output_dir = tests_dir.parent  # output/
    candidates_xml: List[Path] = [
        output_dir / "jacoco" / "report" / "jacoco.xml",  # Microservice coverage (checked FIRST)
        target / "site"    / "jacoco"         / "jacoco.xml",  # Maven test project coverage
        target / "site"    / "jacoco-it"      / "jacoco.xml",
        target / "jacoco"                     / "jacoco.xml",
        target / "jacoco-ut"                  / "jacoco.xml",
        target / "jacoco-aggregate"           / "jacoco.xml",
        target / "coverage-reports"           / "jacoco.xml",
    ]
    candidates_csv: List[Path] = [
        output_dir / "jacoco" / "report" / "jacoco.csv",  # Microservice coverage (checked FIRST)
        target / "site"    / "jacoco"         / "jacoco.csv",  # Maven test project coverage
        target / "jacoco"                     / "jacoco.csv",
        target / "jacoco-ut"                  / "jacoco.csv",
    ]

    # Also search recursively for any jacoco.xml under target/
    for p in target.rglob("jacoco.xml"):
        if p not in candidates_xml:
            candidates_xml.append(p)
    for p in target.rglob("jacoco.csv"):
        if p not in candidates_csv:
            candidates_csv.append(p)

    found_xml = next((p for p in candidates_xml if p.exists()), None)
    found_csv = next((p for p in candidates_csv if p.exists()), None)

    if found_xml:
        logger.info(f"   Found JaCoCo XML: {found_xml}")
    else:
        logger.info("   No JaCoCo XML report found")
    if found_csv:
        logger.info(f"   Found JaCoCo CSV: {found_csv}")

    return {"xml": found_xml, "csv": found_csv}


# ------------------------------
# Pom.xml JaCoCo injection helper
# ------------------------------

_JACOCO_PLUGIN_SNIPPET = """
<!--
  +==========================================================+
  |  JaCoCo plugin — add this to your pom.xml <build>       |
  |  <plugins> section to enable coverage reports.           |
  +==========================================================+
-->
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.11</version>
    <executions>
        <execution>
            <id>prepare-agent</id>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>verify</phase>
            <goals><goal>report</goal></goals>
        </execution>
    </executions>
</plugin>
"""


def _check_pom_for_jacoco(tests_dir: Path) -> bool:
    """Return True if pom.xml already references jacoco-maven-plugin."""
    pom = tests_dir / "pom.xml"
    if not pom.exists():
        return False
    try:
        content = pom.read_text(encoding="utf-8")
        return "jacoco" in content.lower()
    except OSError:
        return False


# ------------------------------
# Report persistence
# ------------------------------

def _save_reports(
    report:       CoverageReport,
    service_name: str,
    reports_dir:  Path,
) -> Tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Clean up old reports for this service
    safe_svc = re.sub(r"[^a-z0-9]+", "-", service_name.lower()).strip("-")
    for old_report in reports_dir.glob(f"coverage_report_{safe_svc}_*.yaml"):
        old_report.unlink()
    for old_report in reports_dir.glob(f"coverage_report_{safe_svc}_*.json"):
        old_report.unlink()

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")

    yaml_path = reports_dir / f"coverage_report_{safe_svc}_{ts}.yaml"
    json_path = reports_dir / f"coverage_report_{safe_svc}_{ts}.json"

    yaml_path.write_text(report.to_yaml(), encoding="utf-8")
    json_path.write_text(report.to_json(),  encoding="utf-8")

    logger.success(f"   📄 YAML report -> {yaml_path}")
    logger.success(f"   📄 JSON report -> {json_path}")
    return yaml_path, json_path


# ------------------------------
# Agent
# ------------------------------

# Default quality-gate thresholds (can be overridden via state.config)
# NOTE: Auto-generated tests from Swagger specs are stubs = low coverage expected
# These thresholds are for INITIAL pipeline run with generated tests.
# For production, increase to line: 70%, branch: 50%, method: 70%
_DEFAULT_THRESHOLDS: Dict[str, float] = {
    "line_coverage_%":   20.0,    # Auto-generated tests typically 15-25%
    "branch_coverage_%": 5.0,     # Stubs don't test branches
    "method_coverage_%": 20.0,    # Only entry methods covered
}


class CoverageAnalystAgent:
    """
    Agent 6 — Coverage Analyst.

    Reads JaCoCo XML/CSV produced by Maven, builds a structured coverage
    report, applies quality-gate thresholds, and writes YAML + JSON output.
    Works for any microservice without hardcoding names or packages.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        logger.info("✅ Coverage Analyst Agent initialized (JaCoCo / Surefire / heuristic)")

    # ------------------------------
    # Core analysis
    # ------------------------------

    def _build_report(
        self,
        service_name: str,
        tests_dir:    Path,
        state:        TestAutomationState,
    ) -> CoverageReport:
        """
        Try each data source in order of richness:
          1. JaCoCo XML  (most detailed — class + branch + line + method)
          2. JaCoCo CSV  (class-level, no method breakdown)
          3. Heuristic   (test counts only from console output)
        """
        paths  = _locate_jacoco_reports(tests_dir)
        report = None

        # ── Source 1: JaCoCo XML ------------------------------
        if paths["xml"]:
            report = _parse_jacoco_xml(paths["xml"])
            if report:
                logger.info("   Data source: JaCoCo XML [OK]")

        # ── Source 2: JaCoCo CSV ------------------------------
        if report is None and paths["csv"]:
            report = _parse_jacoco_csv(paths["csv"])
            if report:
                logger.info("   Data source: JaCoCo CSV [OK]")

        # ── Source 3: Heuristic from console output ------------------------------
        if report is None:
            raw_output = ""
            if hasattr(state, "execution_result") and state.execution_result:
                raw_output = state.execution_result.get("raw_output_tail", "")
            report = _heuristic_from_console(raw_output, service_name)
            logger.warning("   Data source: heuristic (no JaCoCo instrumentation)")

            # Embed JaCoCo setup hint
            if not _check_pom_for_jacoco(tests_dir):
                report.warnings.append(
                    "jacoco-maven-plugin not detected in pom.xml. "
                    "To enable coverage: add the JaCoCo plugin (snippet below)."
                )
                report.warnings.append(_JACOCO_PLUGIN_SNIPPET.strip())

        # ── Enrich with Surefire test summary ------------------------------
        surefire_dir = tests_dir / "target" / "surefire-reports"
        surefire     = _parse_surefire_xml(surefire_dir)
        if surefire["tests"] > 0:
            report.test_summary = {**surefire, "source": "surefire-xml"}
        elif not report.test_summary:
            # Pull from state.execution_result if available
            if hasattr(state, "execution_result") and state.execution_result:
                er = state.execution_result
                report.test_summary = {
                    "tests":    er.get("total",   0),
                    "passed":   er.get("passed",  0),
                    "failures": er.get("failed",  0),
                    "errors":   0,
                    "skipped":  er.get("skipped", 0),
                    "source":   "state.execution_result",
                }

        return report

    def _get_thresholds(self, state: TestAutomationState) -> Dict[str, float]:
        """Read thresholds from state.config, fall back to defaults."""
        cfg = getattr(state, "config", {}) or {}
        thresholds = dict(_DEFAULT_THRESHOLDS)
        custom = cfg.get("coverage_thresholds", {})
        if isinstance(custom, dict):
            thresholds.update(custom)
        return thresholds

    # ------------------------------
    # Console logging
    # ------------------------------

    def _log_summary(self, report: CoverageReport) -> None:
        sep = "─" * 60
        logger.info(f"\n{sep}")
        logger.info(f"[CHART] COVERAGE REPORT — {report.service_name}")
        logger.info(sep)
        logger.info(f"  Data source      : {report.source}")
        logger.info(f"  Generated at     : {report.generated_at}")
        logger.info(f"  Packages         : {len(report.packages)}")
        logger.info(f"  Classes          : {report.total_classes}")
        logger.info(sep)

        if report.total_classes > 0:
            logger.info(f"  Line   coverage  : {report.line_rate:6.2f}%  "
                        f"({report.total_line_covered}/{report.total_line_covered + report.total_line_missed})")
            logger.info(f"  Branch coverage  : {report.branch_rate:6.2f}%  "
                        f"({report.total_branch_covered}/{report.total_branch_covered + report.total_branch_missed})")
            logger.info(f"  Method coverage  : {report.method_rate:6.2f}%  "
                        f"({report.total_method_covered}/{report.total_method_covered + report.total_method_missed})")
        else:
            logger.warning("  No class-level coverage data available.")

        if report.test_summary:
            ts = report.test_summary
            logger.info(sep)
            logger.info(f"  Tests total      : {ts.get('tests',    0)}")
            logger.info(f"  Tests passed     : {ts.get('passed',   0)}")
            logger.info(f"  Tests failed     : {ts.get('failures', 0) + ts.get('errors', 0)}")
            logger.info(f"  Tests skipped    : {ts.get('skipped',  0)}")

        logger.info(sep)
        if report.quality_gate_passed:
            logger.success("  ✅ Quality gate   : PASSED")
        else:
            logger.warning("  [ERROR] Quality gate   : FAILED")
            for v in report.threshold_violations:
                logger.warning(f"       -> {v}")

        if report.warnings:
            logger.info(sep)
            for w in report.warnings:
                if "<!--" not in w:  # Don't log the XML snippet verbosely
                    logger.warning(f"  [WARN] {w}")

        logger.info(sep + "\n")

    # ------------------------------
    # LangGraph entry point
    # ------------------------------

    def analyze(self, state: TestAutomationState) -> TestAutomationState:
        start = time.time()
        logger.info(f"[START] Coverage Analyst starting — service: {state.service_name}")

        try:
            tests_dir   = self.settings.paths.tests_dir
            reports_dir = getattr(self.settings.paths, "reports_dir", None)
            if reports_dir is None:
                reports_dir = self.settings.paths.base_dir / "output" / "reports"
            reports_dir = Path(reports_dir)

            # ── Build coverage report ------------------------------
            report = self._build_report(state.service_name, tests_dir, state)
            report.service_name = state.service_name  # always use state's name

            # ── Apply quality-gate thresholds ------------------------------
            thresholds = self._get_thresholds(state)
            report.apply_thresholds(thresholds)

            # ── Console summary ------------------------------
            self._log_summary(report)

            # ── Persist YAML + JSON ------------------------------
            yaml_path, json_path = _save_reports(report, state.service_name, reports_dir)

            # ── Attach to state ------------------------------
            state.coverage_report = report.to_dict()
            state.coverage_files  = [str(yaml_path), str(json_path)]

            duration_ms = (time.time() - start) * 1000

            # Propagate threshold violations as state warnings
            for violation in report.threshold_violations:
                state.add_warning(f"Coverage threshold violation: {violation}")

            state.add_agent_output(AgentOutput(
                agent_name="coverage_analyst",
                status=AgentStatus.SUCCESS,
                duration_ms=duration_ms,
                output_data={
                    "data_source":          report.source,
                    "total_classes":        report.total_classes,
                    "total_packages":       len(report.packages),
                    "line_coverage_%":      report.line_rate,
                    "branch_coverage_%":    report.branch_rate,
                    "method_coverage_%":    report.method_rate,
                    "quality_gate_passed":  report.quality_gate_passed,
                    "threshold_violations": report.threshold_violations,
                    "yaml_report":          str(yaml_path),
                    "json_report":          str(json_path),
                },
            ))
            logger.success(
                f"✅ Coverage Analyst finished in {duration_ms:.0f} ms  "
                f"[line={report.line_rate}%  branch={report.branch_rate}%  "
                f"method={report.method_rate}%]"
            )

        except Exception:
            duration_ms = (time.time() - start) * 1000
            tb = traceback.format_exc()
            logger.error(f"[ERROR] Coverage Analyst failed:\n{tb}")
            state.add_agent_output(AgentOutput(
                agent_name="coverage_analyst",
                status=AgentStatus.FAILED,
                duration_ms=duration_ms,
                error_message=tb,
            ))
            state.add_error(f"Coverage analysis failed: {tb}")

        return state


# ------------------------------
# LangGraph node
# ------------------------------

def coverage_analyst_node(state: TestAutomationState) -> TestAutomationState:
    return CoverageAnalystAgent().analyze(state)