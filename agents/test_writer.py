"""
Agent 4: Test Writer
Translates Gherkin scenarios into executable Java/Cucumber test code
Uses LLM to generate step definitions, test utilities, and configuration
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from loguru import logger
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from graph.state import TestAutomationState, AgentOutput, AgentStatus
from config.settings import get_settings
from tools.swagger_parser import get_api_context


class GeneratedTestFile(BaseModel):
    """Represents a generated test file"""
    filepath: str = Field(..., description="Relative path to the file")
    content: str = Field(..., description="File content")
    file_type: str = Field(..., description="Type: step_definition, runner, config, helper")


class TestWriterAgent:
    """
    Agent responsible for generating executable test code from Gherkin scenarios
    Generates Java/Cucumber step definitions with precise selectors
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = OllamaLLM(
            base_url=self.settings.ollama.base_url,
            model=self.settings.ollama.model,
            temperature=0.2,
            num_predict=4000,
        )
        self.parser = StrOutputParser()
        logger.info(f"✅ Test Writer initialized with model: {self.settings.ollama.model}")
    
    def _create_step_definition_prompt(self) -> ChatPromptTemplate:
        """Create prompt template for generating step definitions"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a senior Test Automation Engineer specializing in Java, Cucumber, and RestAssured.

CRITICAL REQUIREMENTS:
1. Generate COMPLETE, COMPILABLE Java code ONLY
2. ALWAYS include package declaration and ALL imports
3. NO placeholder comments - provide FULL working implementations
4. Use proper error handling and logging
5. NO markdown formatting - pure Java code only

TESTING FRAMEWORK:
- Cucumber JUnit 5
- RestAssured for API testing
- AssertJ for assertions
- SLF4J for logging

EXAMPLE STRUCTURE:
package com.servicename.steps;

import io.cucumber.java.en.*;
import io.restassured.response.Response;
import static io.restassured.RestAssured.*;
import static org.assertj.core.api.Assertions.*;

public class ServiceSteps {{
    private Response response;
    
    @Given("step definition")
    public void method() {{
        // Full implementation
    }}
}}"""),
            ("human", """Generate COMPLETE Java/Cucumber step definitions.

GHERKIN:
{gherkin_content}

API SPEC:
{api_context}

SERVICE: {service_name}

Requirements:
- Complete package and imports
- All methods fully implemented
- No TODOs or placeholders

Generate the step definitions class:""")
        ])
    
    def _create_test_runner_prompt(self) -> ChatPromptTemplate:
        """Create prompt for generating Cucumber test runner"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a Java test automation expert.
Generate a complete Cucumber test runner using JUnit 5.
Include package, imports, and all annotations.
NO markdown, ONLY Java code."""),
            ("human", """Generate Cucumber test runner for:

SERVICE: {service_name}
FEATURES: {feature_files}

Include JUnit 5 Suite configuration and Cucumber plugins.

Generate the runner class:""")
        ])
    
    def _create_helper_class_prompt(self) -> ChatPromptTemplate:
        """Create prompt for generating helper/utility classes"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a Java expert creating test utilities.
Generate complete, compilable helper classes.
Include package, imports, and full implementations.
NO placeholders or TODOs."""),
            ("human", """Generate test helper classes for:

SERVICE: {service_name}
API: {api_context}

Generate these 4 complete classes:
1. RestAssuredHelper - HTTP wrapper
2. TestContext - Thread-safe state
3. TestDataBuilder - Test data factory
4. AuthHelper - Authentication

Generate all classes:""")
        ])
    
    def _validate_generated_code(self, code: str, file_type: str) -> Tuple[bool, List[str]]:
        """Validate generated code quality"""
        issues = []
        
        if not re.search(r'^package\s+[\w.]+;', code, re.MULTILINE):
            issues.append("❌ Missing package declaration")
        
        if file_type in ["step_definitions", "helper"] and "import" not in code:
            issues.append("❌ Missing import statements")
        
        placeholders = ["// Implement", "// TODO", "// Add your", "as per your requirements"]
        for placeholder in placeholders:
            if placeholder.lower() in code.lower():
                issues.append(f"❌ Contains placeholder: '{placeholder}'")
        
        if file_type == "step_definitions":
            empty_methods = re.findall(
                r'@(?:Given|When|Then|And)\s*\([^)]+\)\s*public\s+void\s+\w+\([^)]*\)\s*\{\s*\}',
                code
            )
            if empty_methods:
                issues.append(f"❌ Found {len(empty_methods)} empty step methods")
        
        if not re.search(r'public\s+class\s+\w+', code):
            issues.append("❌ Missing public class declaration")
        
        is_valid = len([i for i in issues if i.startswith("❌")]) == 0
        
        if issues:
            logger.warning(f"Code validation issues ({file_type}):")
            for issue in issues:
                logger.warning(f"  {issue}")
        else:
            logger.success(f"✓ Code validation passed for {file_type}")
        
        return is_valid, issues
    
    def extract_unique_steps(self, gherkin_content: str) -> List[str]:
        """Extract unique Gherkin steps from scenarios"""
        steps = set()
        step_keywords = ['Given', 'When', 'Then', 'And', 'But']
        
        for line in gherkin_content.splitlines():
            line = line.strip()
            for keyword in step_keywords:
                if line.startswith(keyword):
                    step = line[len(keyword):].strip()
                    normalized = re.sub(r'"[^"]*"', '"{}"', step)
                    normalized = re.sub(r'\d+', '{}', normalized)
                    steps.add(normalized)
                    break
        
        return sorted(list(steps))
    
    def generate_step_definitions(
        self,
        gherkin_content: str,
        service_name: str,
        swagger_spec: Optional[Dict] = None,
        max_retries: int = 2
    ) -> str:
        """Generate step definitions with validation and retry"""
        logger.info("🔨 Generating step definitions...")
        
        api_context = get_api_context(swagger_spec) if swagger_spec else "No API spec"
        prompt = self._create_step_definition_prompt()
        chain = prompt | self.llm | self.parser
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.warning(f"🔄 Retry attempt {attempt}/{max_retries}")
            
            result = chain.invoke({
                "gherkin_content": gherkin_content,
                "api_context": api_context,
                "service_name": service_name.replace("-", "").lower()
            })
            
            cleaned_code = self._clean_code_output(result)
            is_valid, issues = self._validate_generated_code(cleaned_code, "step_definitions")
            
            if is_valid:
                logger.success("✓ Step definitions validation passed")
                return cleaned_code
            else:
                logger.error(f"✗ Validation failed (attempt {attempt + 1}/{max_retries + 1})")
                if attempt == max_retries:
                    logger.error("⚠️ Max retries reached. Returning code with issues.")
        
        return cleaned_code
    
    def generate_test_runner(
        self,
        service_name: str,
        feature_files: List[str],
        max_retries: int = 2
    ) -> str:
        """Generate test runner with validation"""
        logger.info("🔨 Generating test runner...")
        
        prompt = self._create_test_runner_prompt()
        chain = prompt | self.llm | self.parser
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.warning(f"🔄 Retry attempt {attempt}/{max_retries}")
            
            result = chain.invoke({
                "service_name": service_name.replace("-", "").lower(),
                "feature_files": ", ".join(feature_files)
            })
            
            cleaned_code = self._clean_code_output(result)
            is_valid, _ = self._validate_generated_code(cleaned_code, "runner")
            
            if is_valid:
                logger.success("✓ Test runner validation passed")
                return cleaned_code
            elif attempt == max_retries:
                logger.warning("⚠️ Test runner has issues but proceeding")
        
        return cleaned_code
    
    def generate_helper_classes(
        self,
        service_name: str,
        swagger_spec: Optional[Dict] = None,
        max_retries: int = 2
    ) -> Dict[str, str]:
        """Generate helper classes with validation"""
        logger.info("🔨 Generating helper classes...")
        
        api_context = get_api_context(swagger_spec) if swagger_spec else "No API spec"
        prompt = self._create_helper_class_prompt()
        chain = prompt | self.llm | self.parser
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.warning(f"🔄 Retry attempt {attempt}/{max_retries}")
            
            result = chain.invoke({
                "service_name": service_name.replace("-", "").lower(),
                "api_context": api_context
            })
            
            helper_classes = self._parse_helper_classes(result)
            
            all_valid = True
            for class_name, class_code in helper_classes.items():
                is_valid, _ = self._validate_generated_code(class_code, "helper")
                if not is_valid:
                    all_valid = False
                    logger.warning(f"⚠️ {class_name} has validation issues")
            
            if all_valid:
                logger.success(f"✓ All {len(helper_classes)} helper classes validated")
                return helper_classes
            elif attempt == max_retries:
                logger.warning("⚠️ Some helpers have issues but proceeding")
        
        return helper_classes
    
    def _clean_code_output(self, text: str) -> str:
        """Clean LLM output to ensure valid Java code"""
        text = re.sub(r"```java\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        
        lines = text.splitlines()
        code_start = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith("package ") or line.strip().startswith("import "):
                code_start = i
                break
        
        lines = lines[code_start:]
        lines = [line.rstrip() for line in lines]
        
        return "\n".join(lines)
    
    def _parse_helper_classes(self, generated_code: str) -> Dict[str, str]:
        """Parse multiple classes from generated code"""
        classes = {}
        current_class = None
        current_content = []
        package_line = ""
        imports = []
        
        for line in generated_code.splitlines():
            if line.strip().startswith("package "):
                package_line = line
            elif line.strip().startswith("import "):
                imports.append(line)
        
        in_class = False
        brace_count = 0
        
        for line in generated_code.splitlines():
            if line.strip().startswith("package ") or line.strip().startswith("import "):
                continue
            
            if re.search(r'public\s+class\s+(\w+)', line):
                if current_class and current_content:
                    class_code = package_line + "\n\n" + "\n".join(imports) + "\n\n" + "\n".join(current_content)
                    classes[current_class] = class_code
                
                match = re.search(r'public\s+class\s+(\w+)', line)
                current_class = match.group(1)
                current_content = [line]
                in_class = True
                brace_count = line.count('{') - line.count('}')
            elif in_class:
                current_content.append(line)
                brace_count += line.count('{') - line.count('}')
                
                if brace_count == 0 and current_content:
                    class_code = package_line + "\n\n" + "\n".join(imports) + "\n\n" + "\n".join(current_content)
                    classes[current_class] = class_code
                    current_class = None
                    current_content = []
                    in_class = False
        
        if current_class and current_content:
            class_code = package_line + "\n\n" + "\n".join(imports) + "\n\n" + "\n".join(current_content)
            classes[current_class] = class_code
        
        if not classes:
            classes["GeneratedCode"] = generated_code
            logger.warning("⚠️ Could not parse classes, returning as single file")
        else:
            logger.info(f"✓ Parsed {len(classes)} classes: {list(classes.keys())}")
        
        return classes
    
    def save_test_files(
        self,
        service_name: str,
        step_definitions: str,
        test_runner: str,
        helper_classes: Dict[str, str]
    ) -> List[Path]:
        """Save all generated test files to disk"""
        saved_files = []
        base_path = self.settings.paths.tests_dir
        package_base = base_path / "java" / service_name.replace("-", "").lower()
        
        # Save step definitions
        steps_dir = package_base / "steps"
        steps_dir.mkdir(parents=True, exist_ok=True)
        steps_file = steps_dir / f"{self._to_camel_case(service_name)}Steps.java"
        steps_file.write_text(step_definitions, encoding="utf-8")
        saved_files.append(steps_file)
        logger.success(f"✔ Saved: {steps_file.relative_to(base_path)}")
        
        # Save test runner
        runner_file = package_base / "RunCucumberTest.java"
        runner_file.write_text(test_runner, encoding="utf-8")
        saved_files.append(runner_file)
        logger.success(f"✔ Saved: {runner_file.relative_to(base_path)}")
        
        # Save helper classes
        utils_dir = package_base / "utils"
        utils_dir.mkdir(parents=True, exist_ok=True)
        
        for class_name, class_content in helper_classes.items():
            helper_file = utils_dir / f"{class_name}.java"
            helper_file.write_text(class_content, encoding="utf-8")
            saved_files.append(helper_file)
            logger.success(f"✔ Saved: {helper_file.relative_to(base_path)}")
        
        return saved_files
    
    def _to_camel_case(self, text: str) -> str:
        """Convert text to CamelCase"""
        parts = re.split(r'[-_\s]+', text)
        return ''.join(word.capitalize() for word in parts)
    
    def write_tests(self, state: TestAutomationState) -> TestAutomationState:
        """Main entry point - generates test code from Gherkin scenarios"""
        start_time = time.time()
        logger.info(f"🚀 Test Writer starting for service: {state.service_name}")
        
        validation_issues = []
        
        try:
            unique_steps = self.extract_unique_steps(state.gherkin_content)
            logger.info(f"📋 Found {len(unique_steps)} unique step patterns")
            
            logger.info("1️⃣ Generating step definitions...")
            step_definitions = self.generate_step_definitions(
                gherkin_content=state.gherkin_content,
                service_name=state.service_name,
                swagger_spec=state.swagger_spec,
                max_retries=2
            )
            
            logger.info("2️⃣ Generating test runner...")
            test_runner = self.generate_test_runner(
                service_name=state.service_name,
                feature_files=state.gherkin_files,
                max_retries=2
            )
            
            logger.info("3️⃣ Generating helper classes...")
            helper_classes = self.generate_helper_classes(
                service_name=state.service_name,
                swagger_spec=state.swagger_spec,
                max_retries=2
            )
            
            logger.info("4️⃣ Running final validation...")
            _, step_issues = self._validate_generated_code(step_definitions, "step_definitions")
            _, runner_issues = self._validate_generated_code(test_runner, "runner")
            
            all_issues = step_issues + runner_issues
            for class_name, class_code in helper_classes.items():
                _, class_issues = self._validate_generated_code(class_code, "helper")
                all_issues.extend([f"{class_name}: {issue}" for issue in class_issues])
            
            if all_issues:
                logger.warning(f"⚠️ Found {len(all_issues)} total validation issues")
                validation_issues = all_issues
            else:
                logger.success("✓ All generated code passed validation")
            
            logger.info("5️⃣ Saving test files...")
            saved_files = self.save_test_files(
                service_name=state.service_name,
                step_definitions=step_definitions,
                test_runner=test_runner,
                helper_classes=helper_classes
            )
            
            state.test_code = {
                "step_definitions": step_definitions,
                "test_runner": test_runner,
                **{f"helper_{name}": content for name, content in helper_classes.items()}
            }
            state.test_files = [str(f) for f in saved_files]
            
            if validation_issues:
                for issue in validation_issues:
                    state.add_warning(f"Code quality: {issue}")
            
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="test_writer",
                status=AgentStatus.SUCCESS,
                duration_ms=duration,
                output_data={
                    "files_generated": len(saved_files),
                    "step_definitions_lines": len(step_definitions.splitlines()),
                    "helper_classes_count": len(helper_classes),
                    "unique_steps": len(unique_steps),
                    "validation_issues": len(validation_issues),
                    "test_files": [str(f.relative_to(self.settings.paths.tests_dir)) for f in saved_files]
                }
            )
            state.add_agent_output(agent_output)
            
            logger.success(f"✅ Test code generated successfully in {duration:.0f}ms")
            logger.info(f"   Files: {len(saved_files)}")
            logger.info(f"   Lines: {sum(len(c.splitlines()) for c in state.test_code.values())}")
            if validation_issues:
                logger.warning(f"   ⚠️ Validation issues: {len(validation_issues)}")
            
        except Exception as e:
            logger.error(f"❌ Test generation failed: {str(e)}")
            
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="test_writer",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(e)
            )
            state.add_agent_output(agent_output)
            state.add_error(f"Test generation failed: {str(e)}")
        
        return state


def test_writer_node(state: TestAutomationState) -> TestAutomationState:
    """LangGraph node wrapper for Test Writer"""
    agent = TestWriterAgent()
    return agent.write_tests(state)