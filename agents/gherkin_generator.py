"""
Agent 2: Enterprise Gherkin Generator
Adapted for large functional specifications with LangGraph integration
"""

import re
import time
from pathlib import Path
import traceback
from typing import List
from datetime import datetime

from loguru import logger
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import ChatPromptTemplate
from graph import state
from graph.state import TestAutomationState, AgentOutput, AgentStatus
from config.settings import get_settings



class GherkinGeneratorAgent:
    """
    Enterprise-grade Gherkin Generator
    Handles large functional specifications and generates complete Gherkin features
    """
        # self.llm = OllamaLLM(
        #     base_url=self.settings.ollama.base_url,
        #     model=self.settings.ollama.model,
        #     temperature=0.2,  # Lower for more consistent output
        #     num_predict=3000,  # Higher for large specs
        # )
          # Using Gemini instead of Ollama
    def __init__(self):
        self.settings = get_settings()
        print(self.settings)  # pour debug
        
        # Create the base endpoint
        llm = HuggingFaceEndpoint(
            repo_id=self.settings.huggingface.gherkin_generator.model_name,
            huggingfacehub_api_token=self.settings.huggingface.api_token,
            temperature=self.settings.huggingface.gherkin_generator.temperature,
            max_new_tokens=1200,
        )
        
        # Wrap it with ChatHuggingFace for proper chat formatting
        self.llm = ChatHuggingFace(llm=llm)
        
        self.parser = None
        
        logger.info(f"✅ Enterprise Gherkin Generator initialized with model: {self.settings.huggingface.gherkin_generator.model_name}")

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template for Gherkin generation"""

        return ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a senior expert in BDD and Enterprise Test Automation.

MANDATORY OUTPUT STRUCTURE (DO NOT DEVIATE):

Feature: <added leave request>
  Background:
    Given the employee is authenticated
    And required reference data exists
    And at least one leave type is available

  Scenario: <happy path title>
    Given ...
    When ...
    Then ...

  Scenario: <one business rule violation>
    Given ...
    When ...
    Then the system displays "<EXACT error message>"

STRICT RULES:
- Generate ONLY valid Gherkin (no markdown, no explanations)
- EXACT error messages as written in the specification
- ONE business rule per scenario
- Use Background when steps are shared
- Use concrete dates, values, and leave types
- Verify SYSTEM BEHAVIOR (status, flags, calculations)
- No abstract steps like "fills in correctly"
- Maximum 10 scenarios
- Language: English
- Indentation: 2 spaces


QUALITY REQUIREMENTS:
- Each scenario must be independent and executable
- Steps must be clear and actionable
- Use realistic test data
- Include all acceptance criteria from the specification
- Cover all business rules with separate scenarios



FORBIDDEN:
- Generic steps (e.g. "fills in valid data")
- UI-only wording without system effect
- Missing Given/When/Then


"""



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
    

    def _normalize_scenario_steps(self, gherkin_text: str) -> str:
        """
        Enforce exactly ONE When per Scenario.
        - All actions before the trigger become Given
        - The LAST When becomes the real trigger
        - All assertions stay Then
        """

        scenarios = re.split(r"(?=^\s*Scenario:)", gherkin_text, flags=re.MULTILINE)
        normalized = []

        for block in scenarios:
            if not block.strip().startswith("Scenario:"):
                normalized.append(block)
                continue

            lines = block.splitlines()
            header = lines[0]

            givens, whens, thens, others = [], [], [], []
            current_phase = None

            for line in lines[1:]:
                stripped = line.strip()

                if stripped.startswith("Given"):
                    current_phase = "Given"
                    givens.append(line)

                elif stripped.startswith("When"):
                    current_phase = "When"
                    whens.append(line)

                elif stripped.startswith("Then"):
                    current_phase = "Then"
                    thens.append(line)

                elif stripped.startswith("And"):
                    if current_phase == "Given":
                        givens.append(line)
                    elif current_phase == "When":
                        whens.append(line)
                    elif current_phase == "Then":
                        thens.append(line)
                    else:
                        others.append(line)
                else:
                    others.append(line)

            # 🔑 Enforce ONE When: keep only the LAST one
            final_whens = whens[-1:] if whens else []

            rebuilt = (
                [header]
                + givens
                + final_whens
                + thens
                + others
            )

            normalized.append("\n".join(rebuilt))

        return "\n".join(normalized)


    # def generate_single(self, story: str, swagger_context: str = "") -> str:
    #     """Generate Gherkin for a single feature specification"""
    
    #     # Parse the story for business rules and acceptance criteria
    #     business_rules_text = self._extract_section(story, "Business Rules:")
    #     acceptance_criteria_text = self._extract_section(story, "Acceptance Criteria:")

    #     combined_context = ""
    #     if business_rules_text:
    #         combined_context += "BUSINESS RULES:\n" + business_rules_text.strip() + "\n\n"
    #     if acceptance_criteria_text:
    #         combined_context += "ACCEPTANCE CRITERIA:\n" + acceptance_criteria_text.strip() + "\n\n"

    #     prompt = self._create_prompt()
    #     chain = prompt | self.llm | self.parser

    #     logger.info("🤖 Generating Gherkin with LLM...")

    #     result = chain.invoke({
    #         "story": combined_context + story,
    #         "swagger_context": swagger_context
    #     })

    #     result = self._normalize_scenario_steps(result)
    #     return self._clean_output(result)
    

   

    def generate_single(self, story: str, swagger_context: str = "") -> str:
        """Generate Gherkin for a single feature specification using conversational LLM"""

        # Extract business rules and acceptance criteria
        business_rules_text = self._extract_section(story, "Business Rules:")
        acceptance_criteria_text = self._extract_section(story, "Acceptance Criteria:")

        combined_context = ""
        if business_rules_text:
            combined_context += "BUSINESS RULES:\n" + business_rules_text.strip() + "\n\n"
        if acceptance_criteria_text:
            combined_context += "ACCEPTANCE CRITERIA:\n" + acceptance_criteria_text.strip() + "\n\n"

        # Build prompt template
        template = (
            "You are a Gherkin scenario generator. Convert the following user story into Gherkin syntax.\n\n"
            "Context:\n{story}\n\n"
            "Swagger context (if any):\n{swagger_context}\n\n"
            "Return valid Gherkin feature scenarios."
        )

        prompt = ChatPromptTemplate.from_template(template)

        # Use LCEL syntax (modern LangChain)
        chain = prompt | self.llm
        
        logger.info("🤖 Generating Gherkin with LLM...")

        # Invoke and extract text from response
        response = chain.invoke({
            "story": combined_context + story,
            "swagger_context": swagger_context
        })
        
        # Extract text from ChatHuggingFace response
        if hasattr(response, 'content'):
            result = response.content
        elif isinstance(response, str):
            result = response
        else:
            result = str(response)

        result = self._normalize_scenario_steps(result)
        return self._clean_output(result)

    def _extract_section(self, text: str, header: str) -> str:
        """Extract a section from a markdown or text story"""
        pattern = rf"{header}(.*?)(\n\n|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""


 
    def _clean_output(self, text: str) -> str:
        """Clean LLM output to ensure valid Gherkin with proper formatting"""

        # Remove any markdown code blocks
        text = re.sub(r"```gherkin\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.strip().splitlines()]
        
        # Join lines and ensure blank line at EOF
        cleaned_text = "\n".join(lines)
        
        # Ensure file ends with a newline (blank line at EOF)
        # This is required by gherkin-lint's new-line-at-eof rule
        if not cleaned_text.endswith("\n"):
            cleaned_text += "\n"
        
        return cleaned_text

    def _validate_required_errors(self, text: str):
        """Ensure all required business error messages are present"""
    
        REQUIRED_ERRORS = [
            "Warning! Please check the Employee ID and/or number of days and/or start date and/or end date!",
            "Warning: 'From' date is later than 'To' date.",
            "Number of days is zero.",
            "Other requests exist during this period.",
            "Insufficient balance.",
            "The mandatory 48-hour notice period is not respected."
        ]
        
        for err in REQUIRED_ERRORS:
            if err not in text:
                logger.warning(f"⚠ Missing expected error message: {err}")




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

        # Create safe filename with length limit
        safe_name = re.sub(r"[^a-z0-9]+", "-", feature_name.lower()).strip("-")
        
        # Limit filename length to avoid Windows path issues (max 50 chars for the name part)
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.feature"

        # Save to features directory
        filepath = self.settings.paths.features_dir / filename

        # Make sure the folder exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Ensure content ends with newline before saving
        if not content.endswith("\n"):
            content += "\n"
        
        # Write with newline parameter to preserve line endings
        filepath.write_text(content, encoding="utf-8", newline="\n")

        logger.success(f"✔ Saved: {filepath.name}")
        return filepath
            
    def generate(self, state: TestAutomationState) -> TestAutomationState:
        """
        Main entry point for LangGraph node.
        Generates Gherkin from all user stories/features in state.user_story.
        Supports multiple features, each saved as a separate .feature file.
        """
        start_time = time.time()
        logger.info(f"🚀 Gherkin Generator starting for service: {state.service_name}")

        try:
            # Format swagger context if available
            swagger_context = ""
            if state.swagger_spec:
                swagger_context = self._format_swagger_context(state.swagger_spec)

            # Extract features/user stories from state
            features = self.extract_features(state.user_story)

            if not features:
                raise ValueError("No features found in user story")

            logger.info(f"📌 Found {len(features)} feature(s) to generate Gherkin for")

            gherkin_files = []
            all_gherkin_content = []

            # Loop through all features and generate Gherkin
            for i, feature in enumerate(features, start=1):
                # Further split by individual User Story within this feature
                user_stories = re.split(r"(User Story\s*:)", feature, flags=re.IGNORECASE)
                
                # Combine the split pieces properly
                combined_stories = []
                for j in range(0, len(user_stories), 2):
                    header = user_stories[j].strip()
                    body = user_stories[j+1].strip() if j+1 < len(user_stories) else ""
                    combined_stories.append(header + "\n" + body)

                for k, story_text in enumerate(combined_stories, start=1):
                    if story_text.strip():
                        logger.info(f"📝 Generating Gherkin for a user story {k} in feature {i}")
                        
                        gherkin_content = self.generate_single(story_text, swagger_context)
                        
                        # Validate required business rule errors
                        self._validate_required_errors(gherkin_content)
                        
                        # Save each user story as a separate .feature file with unique name
                        feature_file = self.save_feature_file(gherkin_content, f"{state.service_name}_{i}_{k}")
                        gherkin_files.append(str(feature_file))
                        all_gherkin_content.append(gherkin_content)


            # Update state with all generated content and files
            state.gherkin_content = "\n\n".join(all_gherkin_content)
            state.gherkin_files = gherkin_files

            # Record agent output
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="gherkin_generator",
                status=AgentStatus.SUCCESS,
                duration_ms=duration,
                output_data={
                    "features_extracted": len(features),
                    "features_generated": len(features),
                    "feature_files": gherkin_files,
                    "gherkin_total_length": sum(len(f) for f in all_gherkin_content),
                    "lines_generated": sum(len(f.splitlines()) for f in all_gherkin_content)
                }
            )
            state.add_agent_output(agent_output)

            logger.success(f"✅ Gherkin generated successfully for {len(features)} feature(s) in {duration:.0f}ms")

        except Exception as e:
            logger.error("❌ Gherkin generation failed:")
            logger.error(traceback.format_exc())

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
