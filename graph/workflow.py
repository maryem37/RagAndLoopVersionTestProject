"""
workflow.py
Full LangGraph-style workflow for Gherkin generation, validation, and test writing
"""

import re
import time
import uuid
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from loguru import logger
from rich import print as rprint
from pydantic import BaseModel, Field
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

# LangGraph imports
from langgraph.graph import StateGraph, END

from graph.state import (
    TestAutomationState,
    AgentOutput,
    AgentStatus,
    ValidationResult,
    ValidationIssue
)
from config.settings import get_settings
from tools.swagger_parser import load_swagger_file, get_api_context

# Import Test Writer from agents module
from agents.test_writer import TestWriterAgent, test_writer_node

# ---------------------------------------------
# Gherkin Generator Agent
# ---------------------------------------------
class GherkinGeneratorAgent:
    def __init__(self):
        self.settings = get_settings()
        self.llm = OllamaLLM(
            base_url=self.settings.ollama.base_url,
            model=self.settings.ollama.model,
            temperature=0.0,
            num_predict=3000,
        )
        self.parser = StrOutputParser()
        logger.info(f"✅ Gherkin Generator initialized (model={self.settings.ollama.model})")

    def _create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a senior BDD/QA expert.
STRICT RULES: Generate only valid Gherkin, max 10 scenarios per feature, proper Given-When-Then order, no explanations.
Include all acceptance criteria and business rules."""),
            ("human", "SPECIFICATION: {story}\n{swagger_context}\nGenerate the Gherkin feature:")
        ])

    def extract_features(self, text: str) -> List[str]:
        blocks = []
        current = []
        inside_gherkin = False
        for line in text.splitlines():
            if line.strip().startswith("Gherkin"):
                inside_gherkin = True
            if re.match(r"(User Story|Feature)\s*[-:]", line, re.IGNORECASE):
                if current:
                    blocks.append("\n".join(current).strip())
                    current = []
                inside_gherkin = False
            if not inside_gherkin and line.strip():
                current.append(line)
        if current:
            blocks.append("\n".join(current).strip())
        logger.info(f"📋 Extracted {len(blocks)} feature specifications")
        return blocks

    def generate_single(self, story: str, swagger_context: str = "") -> str:
        prompt = self._create_prompt()
        chain = prompt | self.llm | self.parser
        logger.info("🤖 Generating Gherkin with LLM...")
        result = chain.invoke({"story": story, "swagger_context": swagger_context})
        return self._clean_output(result)

    def _clean_output(self, text: str) -> str:
        text = re.sub(r"```gherkin\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        return "\n".join([line.rstrip() for line in text.strip().splitlines()])

    def _format_swagger_context(self, swagger_spec: dict) -> str:
        if not swagger_spec or "paths" not in swagger_spec:
            return ""
        return get_api_context(swagger_spec)

    def save_feature_file(self, content: str, service_name: str = None) -> Path:
        match = re.search(r"Feature:\s*(.+)", content)
        feature_name = match.group(1) if match else (service_name or "feature")
        safe_name = re.sub(r"[^a-z0-9]+", "-", feature_name.lower()).strip("-")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.feature"
        filepath = self.settings.paths.features_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        logger.success(f"✔ Saved: {filepath.name}")
        return filepath

    def generate(self, state: TestAutomationState) -> TestAutomationState:
        start_time = time.time()
        try:
            swagger_context = self._format_swagger_context(state.swagger_spec) if state.swagger_spec else ""
            features = self.extract_features(state.user_story)
            if not features:
                raise ValueError("No features found in user story")
            feature_spec = features[0]
            gherkin_content = self.generate_single(feature_spec, swagger_context)
            feature_file = self.save_feature_file(gherkin_content, state.service_name)
            state.gherkin_content = gherkin_content
            state.gherkin_files = [str(feature_file)]
            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_generator",
                status=AgentStatus.SUCCESS,
                duration_ms=duration,
                output_data={
                    "features_extracted": len(features),
                    "features_generated": 1,
                    "feature_file": str(feature_file),
                    "gherkin_length": len(gherkin_content),
                    "lines_generated": len(gherkin_content.splitlines())
                }
            ))
            logger.success(f"✅ Gherkin generated successfully in {duration:.0f}ms")
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ Gherkin generation failed: {str(e)}")
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_generator",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(e)
            ))
            state.add_error(f"Gherkin generation failed: {str(e)}")
        return state


def gherkin_generator_node(state: TestAutomationState) -> TestAutomationState:
    return GherkinGeneratorAgent().generate(state)


# ---------------------------------------------
# Gherkin Validator Agent
# ---------------------------------------------
class LLMValidationOutput(BaseModel):
    coverage_score: float = Field(..., ge=0, le=100)
    missing_scenarios: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class GherkinValidatorAgent:
    def __init__(self):
        self.settings = get_settings()
        self.llm = OllamaLLM(
            base_url=self.settings.ollama.base_url,
            model=self.settings.ollama.model,
            temperature=0.0
        )
        self.output_parser = JsonOutputParser(pydantic_object=LLMValidationOutput)
        self.has_gherkin_lint = self._check_gherkin_lint()
        logger.info(f"✅ Gherkin Validator initialized (gherkin-lint: {self.has_gherkin_lint})")

    def _check_gherkin_lint(self) -> bool:
        try:
            subprocess.run(['gherkin-lint', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("⚠️ gherkin-lint not found. Install with: npm install -g @cucumber/gherkin-lint")
            return False

    def validate(self, state: TestAutomationState) -> TestAutomationState:
        start_time = time.time()
        all_issues = []
        try:
            if self.has_gherkin_lint and self.settings.gherkin.use_gherkin_lint:
                for feature_file in state.gherkin_files:
                    all_issues.extend(self._validate_syntax(Path(feature_file)))
            for feature_file in state.gherkin_files:
                all_issues.extend(self._validate_semantics(Path(feature_file)))
            llm_result = self._validate_with_llm(state.gherkin_content, state.user_story)
            validation_result = ValidationResult(
                is_valid=not any(issue.level == "error" for issue in all_issues),
                issues=all_issues,
                coverage_score=llm_result.coverage_score,
                missing_scenarios=llm_result.missing_scenarios,
                suggestions=llm_result.suggestions
            )
            state.validation_result = validation_result
            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_validator",
                status=AgentStatus.SUCCESS if validation_result.is_valid else AgentStatus.FAILED,
                duration_ms=duration,
                output_data={
                    "is_valid": validation_result.is_valid,
                    "total_issues": len(all_issues),
                    "coverage_score": llm_result.coverage_score
                }
            ))
        except Exception as e:
            logger.error(f"❌ Validation error: {str(e)}")
            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_validator",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(e)
            ))
            state.add_error(f"Validation failed: {str(e)}")
        return state

    def _validate_syntax(self, feature_file: Path) -> List[ValidationIssue]:
        issues = []
        try:
            result = subprocess.run(['gherkin-lint', str(feature_file)], capture_output=True, text=True)
            if result.returncode != 0:
                for line in result.stdout.splitlines():
                    if ':' in line and ('error' in line.lower() or 'warning' in line.lower()):
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            line_num = int(parts[1]) if parts[1].isdigit() else 0
                            level = "error" if "error" in parts[2].lower() else "warning"
                            issues.append(ValidationIssue(
                                level=level,
                                message=parts[3].strip(),
                                line_number=line_num,
                                scenario="Syntax"
                            ))
        except Exception as e:
            logger.warning(f"Error running gherkin-lint: {str(e)}")
        return issues

    def _validate_semantics(self, feature_file: Path) -> List[ValidationIssue]:
        issues = []
        with open(feature_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        current_scenario = ""
        last_step_type = None
        step_order = {"Given": 0, "When": 1, "Then": 2}
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("Scenario"):
                current_scenario = stripped
                last_step_type = None
                continue
            for keyword in ["Given", "When", "Then"]:
                if stripped.startswith(keyword):
                    if last_step_type and step_order[keyword] < step_order.get(last_step_type, 0):
                        issues.append(ValidationIssue(
                            level="warning",
                            message=f"Unexpected step order: {keyword} after {last_step_type}",
                            line_number=line_num,
                            scenario=current_scenario
                        ))
                    last_step_type = keyword
                    break
        return issues

    def _validate_with_llm(self, gherkin_content: str, user_story: str) -> LLMValidationOutput:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a QA expert validating BDD scenarios against requirements.
STRICT RULES:
1. Respond ONLY in valid JSON.
2. JSON must have keys: coverage_score (0-100), missing_scenarios (list of strings), issues (list of strings), suggestions (list of strings).
3. Do NOT include any explanation or text outside the JSON.
4. If no issues, return empty lists."""),
            ("human", f"User Story:\n{user_story}\nGenerated Gherkin:\n{gherkin_content}")
        ])
        chain = prompt | self.llm | self.output_parser
        try:
            result = chain.invoke({})
            return LLMValidationOutput(**result)
        except Exception as e:
            logger.warning(f"LLM validation error: {str(e)}")
            return LLMValidationOutput(
                coverage_score=0,
                missing_scenarios=[],
                issues=[f"LLM error: {str(e)}"],
                suggestions=[]
            )


def gherkin_validator_node(state: TestAutomationState) -> TestAutomationState:
    return GherkinValidatorAgent().validate(state)


# ---------------------------------------------
# BUILD LANGGRAPH WORKFLOW - ADD THIS FUNCTION!
# ---------------------------------------------
def build_workflow() -> StateGraph:
    """Build the complete test automation workflow as a LangGraph"""
    
    workflow = StateGraph(TestAutomationState)
    
    # Add nodes
    workflow.add_node("generate_gherkin", gherkin_generator_node)
    workflow.add_node("validate_gherkin", gherkin_validator_node)
    workflow.add_node("write_tests", test_writer_node)
    
    # Define edges (workflow flow)
    workflow.set_entry_point("generate_gherkin")
    workflow.add_edge("generate_gherkin", "validate_gherkin")
    workflow.add_edge("validate_gherkin", "write_tests")
    workflow.add_edge("write_tests", END)
    
    return workflow.compile()


# ---------------------------------------------
# Main Workflow Execution
# ---------------------------------------------
# ---------------------------------------------
# Main Workflow Execution
# ---------------------------------------------
if __name__ == "__main__":
    # Load example user story
    user_story_file = Path("examples/sample_user_story.md")
    if not user_story_file.exists():
        raise FileNotFoundError(f"{user_story_file} not found.")
    user_story_text = user_story_file.read_text(encoding="utf-8")

    # Load Swagger spec (optional)
    swagger_spec = None
    swagger_file = Path("examples/sample_swagger.json")
    if swagger_file.exists():
        swagger_spec = load_swagger_file(str(swagger_file))
        logger.info("✅ Loaded Swagger specification")

    # Build the workflow graph
    app = build_workflow()
    
    # Generate and save Mermaid diagram
    try:
        from langgraph.graph import draw_mermaid_png
        
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Save as PNG
        png_data = draw_mermaid_png(app.get_graph())
        png_path = output_dir / "workflow_graph.png"
        with open(png_path, "wb") as f:
            f.write(png_data)
        logger.success(f"✅ Workflow graph saved to: {png_path}")
        
        # Also save as Mermaid text
        mermaid_text = app.get_graph().draw_mermaid()
        mermaid_path = output_dir / "workflow_graph.mmd"
        with open(mermaid_path, "w") as f:
            f.write(mermaid_text)
        logger.success(f"✅ Mermaid diagram saved to: {mermaid_path}")
        
    except ImportError:
        logger.warning("⚠️ Could not generate graph visualization. Install: pip install grandalf")
    except Exception as e:
        logger.warning(f"⚠️ Graph generation failed: {e}")

    # Initialize state
    state = TestAutomationState(
        workflow_id=str(uuid.uuid4()),
        service_name="user-service",
        user_story=user_story_text,
        gherkin_content="",
        gherkin_files=[],
        swagger_spec=swagger_spec
    )

    # Run the workflow
    logger.info("🚀 Starting Test Automation Workflow")
    result = app.invoke(state)
    
    # Convert dict result back to TestAutomationState
    final_state = TestAutomationState(**result)

    # Display results
    rprint("\n" + "="*70)
    rprint("📊 WORKFLOW RESULTS")
    rprint("="*70)
    rprint(f"✅ Valid: {final_state.validation_result.is_valid if final_state.validation_result else 'N/A'}")
    rprint(f"📊 Coverage: {final_state.validation_result.coverage_score if final_state.validation_result else 'N/A'}%")
    rprint(f"⚠️  Issues: {len(final_state.validation_result.issues) if final_state.validation_result else 0}")

    if hasattr(final_state, "test_files") and final_state.test_files:
        rprint(f"\n💻 Generated test files ({len(final_state.test_files)}):")
        for f in final_state.test_files:
            rprint(f" - {f}")
        
        if final_state.warnings:
            rprint(f"\n⚠️  Code Quality Warnings ({len(final_state.warnings)}):")
            for warning in final_state.warnings[:10]:
                rprint(f"  • {warning}")

    if final_state.gherkin_content:
        rprint("\n" + "="*70)
        rprint("GENERATED GHERKIN (first 20 lines)")
        rprint("="*70)
        rprint("\n".join(final_state.gherkin_content.splitlines()[:20]))
    
    # Show agent execution summary
    rprint("\n" + "="*70)
    rprint("⏱️  AGENT EXECUTION SUMMARY")
    rprint("="*70)
    for agent_output in final_state.agent_outputs:
        status_icon = "✅" if agent_output.status == AgentStatus.SUCCESS else "❌"
        rprint(f"{status_icon} {agent_output.agent_name}: {agent_output.duration_ms:.0f}ms")
        if agent_output.error_message:
            rprint(f"   Error: {agent_output.error_message}")
    
    rprint("\n" + "="*70)
    rprint(f"📈 Workflow graph saved to: output/workflow_graph.png")
    rprint(f"📁 Mermaid diagram saved to: output/workflow_graph.mmd")
    rprint("="*70)