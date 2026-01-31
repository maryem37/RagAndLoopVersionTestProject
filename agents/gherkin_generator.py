"""
Agent 2: Enterprise Gherkin Generator
Adapted for large functional specifications with LangGraph integration
"""

import re
import time
from pathlib import Path
from typing import List
from datetime import datetime

from loguru import logger
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from graph.state import TestAutomationState, AgentOutput, AgentStatus
from config.settings import get_settings


class GherkinGeneratorAgent:
    """
    Enterprise-grade Gherkin Generator
    Handles large functional specifications and generates complete Gherkin features
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm = OllamaLLM(
            base_url=self.settings.ollama.base_url,
            model=self.settings.ollama.model,
            temperature=0.2,  # Lower for more consistent output
            num_predict=3000,  # Higher for large specs
        )
        self.parser = StrOutputParser()

        logger.info(f"✅ Enterprise Gherkin Generator initialized with model: {self.settings.ollama.model}")

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template for Gherkin generation"""

        return ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a senior expert in BDD and Test Automation.  
STRICT RULES: 
- Generate ONLY valid Gherkin format
- ONE Feature per response
- Use Background section when there are common preconditions
- Respect EXACT error messages provided in the specification
- Cover: happy path + all business error cases
- No markdown code blocks, no explanations
- Language: English
- Maximum 10 scenarios per feature
- Follow strict Given-When-Then structure
- Use proper indentation (2 spaces)  

QUALITY REQUIREMENTS:
- Each scenario must be independent and executable
- Steps must be clear and actionable
- Use realistic test data
- Include all acceptance criteria from the specification
- Cover all business rules with separate scenarios"""
            ),
            (
                "human",
                """Based on the following functional specification, generate the COMPLETE corresponding Gherkin feature file.  
SPECIFICATION: {story}  
{swagger_context}  
Generate the Gherkin feature:"""
            )
        ])

    def extract_features(self, text: str) -> List[str]:
        """
        Extract Feature-level user stories from a large document.
        Stops before existing Gherkin sections to avoid duplication.
        """
        blocks = []
        current = []
        inside_gherkin = False

        for line in text.splitlines():
            # Detect if we're entering an existing Gherkin section
            if line.strip().startswith("Gherkin"):
                inside_gherkin = True

            # Detect feature boundaries
            if re.match(r"(User Story|Feature)\s*[-:]", line, re.IGNORECASE):
                if current:
                    blocks.append("\n".join(current).strip())
                    current = []
                inside_gherkin = False

            # Only collect lines outside of existing Gherkin
            if not inside_gherkin and line.strip():
                current.append(line)

        # Add last block if exists
        if current:
            blocks.append("\n".join(current).strip())

        logger.info(f"📋 Extracted {len(blocks)} feature specifications")
        return blocks

    def generate_single(self, story: str, swagger_context: str = "") -> str:
        """Generate Gherkin for a single feature specification"""

        prompt = self._create_prompt()
        chain = prompt | self.llm | self.parser

        logger.info("🤖 Generating Gherkin with LLM...")

        result = chain.invoke({
            "story": story,
            "swagger_context": swagger_context
        })

        return self._clean_output(result)

    def _clean_output(self, text: str) -> str:
        """Clean LLM output to ensure valid Gherkin"""

        # Remove any markdown code blocks
        text = re.sub(r"```gherkin\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.strip().splitlines()]
        return "\n".join(lines)

    def _format_swagger_context(self, swagger_spec: dict) -> str:
        """Format Swagger specification for context"""
        if not swagger_spec or "paths" not in swagger_spec:
            return ""

        context = "\nAPI ENDPOINTS:\n"
        for path, methods in swagger_spec.get("paths", {}).items():
            for method, details in methods.items():
                summary = details.get("summary", "")
                context += f"- {method.upper()} {path}: {summary}\n"

        return context

    def save_feature_file(self, content: str, service_name: str = None) -> Path:
        """Save Gherkin content to a .feature file"""

        # Extract feature name from content
        match = re.search(r"Feature:\s*(.+)", content)
        feature_name = match.group(1) if match else (service_name or "feature")

        # Create safe filename
        safe_name = re.sub(r"[^a-z0-9]+", "-", feature_name.lower()).strip("-")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.feature"

        # Save to features directory
        filepath = self.settings.paths.features_dir / filename

        # ✅ Make sure the folder exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        filepath.write_text(content, encoding="utf-8")

        logger.success(f"✔ Saved: {filepath.name}")
        return filepath

    def generate(self, state: TestAutomationState) -> TestAutomationState:
        """
        Main entry point for LangGraph node
        Generates Gherkin from user story in state
        """
        start_time = time.time()
        logger.info(f"🚀 Gherkin Generator starting for service: {state.service_name}")

        try:
            # Format swagger context if available
            swagger_context = ""
            if state.swagger_spec:
                swagger_context = self._format_swagger_context(state.swagger_spec)

            # Extract features from user story
            features = self.extract_features(state.user_story)

            if len(features) == 0:
                raise ValueError("No features found in user story")

            # Generate for first feature (can be extended for multiple)
            feature_spec = features[0]
            logger.info(f"📝 Generating Gherkin for feature 1 of {len(features)}")

            # Generate Gherkin
            gherkin_content = self.generate_single(feature_spec, swagger_context)

            # Save to file
            feature_file = self.save_feature_file(gherkin_content, state.service_name)

            # Update state
            state.gherkin_content = gherkin_content
            state.gherkin_files = [str(feature_file)]

            # Record agent output
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
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
            )
            state.add_agent_output(agent_output)

            logger.success(f"✅ Gherkin generated successfully in {duration:.0f}ms")

        except Exception as e:
            logger.error(f"❌ Gherkin generation failed: {str(e)}")

            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="gherkin_generator",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(e)
            )
            state.add_agent_output(agent_output)
            state.add_error(f"Gherkin generation failed: {str(e)}")

        return state


def gherkin_generator_node(state: TestAutomationState) -> TestAutomationState:
    """LangGraph node wrapper"""
    agent = GherkinGeneratorAgent()
    return agent.generate(state)
