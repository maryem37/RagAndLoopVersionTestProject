"""
Agent 4: Contract-Level Test Writer (Multi-Service Version)
Generates CONTRACT-LEVEL E2E API tests from Gherkin scenarios
Validates API interoperability, NOT business logic or authorization semantics

PHILOSOPHY:
- Validates service-to-service contracts
- Validates API structure and availability
- Does NOT validate business rules
- Does NOT manage authentication/authorization
- Does NOT create test data
- Does NOT interpret semantic meaning
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime

from loguru import logger
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from graph.state import TestAutomationState, AgentOutput, AgentStatus
from config.settings import get_settings
from tools.swagger_parser import get_api_context_multi


class GeneratedTestFile(BaseModel):
    """Represents a generated test file"""
    filepath: str = Field(..., description="Relative path to the file")
    content: str = Field(..., description="File content")
    file_type: str = Field(..., description="Type: step_definition, runner, config")


class TestWriterAgent:
    """
    Contract-Level Test Writer Agent for multi-service architectures.
    
    SCOPE: Contract-level E2E API testing
    - Validates API endpoints exist and are reachable
    - Validates request/response structure compatibility
    - Validates service-to-service communication
    
    OUT OF SCOPE:
    - Business logic validation (e.g., balance checks, approval rules)
    - Authentication/Authorization (assumes pre-configured tokens)
    - Test data creation (assumes data exists or uses stubs)
    - Database state management
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = OllamaLLM(
            base_url=self.settings.ollama.base_url,
            model=self.settings.ollama.model,
            temperature=0.1,  # Lower for more deterministic contract tests
            num_predict=4000,
        )
        self.parser = StrOutputParser()
        logger.info(f"✅ Contract-Level Test Writer initialized with model: {self.settings.ollama.model}")
        logger.info(f"📋 Test Type: CONTRACT-LEVEL E2E (API Structure & Interoperability)")
    
    def _extract_swagger_endpoints(self, swagger_specs: Dict[str, Dict]) -> Set[str]:
        """Extract all valid endpoints from Swagger specs for validation"""
        valid_endpoints = set()
        
        for service_name, spec in swagger_specs.items():
            paths = spec.get("paths", {})
            for path in paths.keys():
                valid_endpoints.add(path)
                logger.debug(f"   Valid endpoint [{service_name}]: {path}")
        
        return valid_endpoints
    
    def _create_step_definition_prompt(self) -> ChatPromptTemplate:
        """Create CONTRACT-FOCUSED prompt for step definitions"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a **Contract-Level API Test Engineer** specializing in microservice contract testing.

🎯 **YOUR MISSION**
Generate CONTRACT-LEVEL E2E tests that validate API structure and service interoperability.
These are NOT business logic tests, NOT security tests, NOT data validation tests.

📋 **TEST TYPE: CONTRACT-LEVEL E2E**
✅ VALIDATE: API endpoints exist and respond
✅ VALIDATE: Request/response structure compatibility  
✅ VALIDATE: HTTP status codes are in expected ranges
✅ VALIDATE: Required fields exist in responses
❌ DO NOT: Validate business rules (balance > 0, approval logic, etc.)
❌ DO NOT: Create users, authenticate, or manage auth flows
❌ DO NOT: Assume database state or create test data
❌ DO NOT: Validate field values beyond existence

🔐 **AUTHENTICATION STRATEGY**
Authentication tokens are INJECTED, not generated:
```java
// CORRECT - Token injection
private String jwtToken = System.getenv("TEST_JWT_TOKEN");

// ALTERNATIVE - Placeholder for CI/CD
private String jwtToken = "BEARER_TOKEN_INJECTED_BY_TEST_SETUP";

// WRONG - Do NOT authenticate in contract tests
@Given("user is authenticated")
public void authenticate() {{
    // NO login calls here
    response = given().post("/api/auth/login"); // ❌ WRONG
}}
```

📋 **STRICT CONTRACT-TEST RULES**

1. **Endpoint Validation Only**
```java
// ✅ CORRECT - Contract validation
@When("employee submits leave request")
public void employeeSubmitsLeaveRequest() {{
    response = given()
        .baseUri(LEAVE_BASE_URL)
        .header("Authorization", "Bearer " + jwtToken)
        .contentType(ContentType.JSON)
        .body(requestBody)
        .when()
        .post("/api/leave/request")
        .then()
        .extract()
        .response();
}}

@Then("the API should accept the request")
public void theApiShouldAcceptTheRequest() {{
    assertThat(response.getStatusCode())
        .as("API contract: endpoint accepts valid request structure")
        .isBetween(200, 299);
}}
```

2. **Response Structure Validation (NOT Semantics)**
```java
// ✅ CORRECT - Validate field exists
@Then("response should contain status field")
public void responseShouldContainStatusField() {{
    String status = response.jsonPath().getString("status");
    assertThat(status)
        .as("API contract: status field must exist")
        .isNotNull();
}}

// ❌ WRONG - Business logic validation
@Then("leave balance should be sufficient")
public void leaveBalanceShouldBeSufficient() {{
    int balance = response.jsonPath().getInt("balance");
    assertThat(balance).isGreaterThan(0); // ❌ Business rule!
}}
```

3. **NO Data Creation**
```java
// ❌ ABSOLUTELY FORBIDDEN
.post("/api/auth/signup")  // ❌ Do not create users
.post("/api/users")        // ❌ Do not create data
.queryParam("role", "admin") // ❌ Do not spoof roles

// ✅ CORRECT - Assume data exists
// Test setup (outside generated code) should pre-seed data
// Or use mock/stub services
```

4. **Steps Without Clear Contract Mapping**
If a Gherkin step does NOT map to a Swagger endpoint:
```java
// ✅ CORRECT - Minimal placeholder for non-API steps
@Given("employee has sufficient leave balance")
public void employeeHasSufficientLeaveBalance() {{
    // Contract test assumption: test data is pre-configured
    // This step is a business precondition, not an API contract
    logger.info("Assuming leave balance precondition met in test environment");
}}

// ❌ WRONG - Inventing API calls
@Given("employee has sufficient leave balance")
public void employeeHasSufficientLeaveBalance() {{
    response = given().get("/api/leave/balance"); // ❌ Not in Gherkin!
    int balance = response.jsonPath().getInt("balance");
    assertThat(balance).isGreaterThan(0); // ❌ Business logic!
}}
```

5. **ONLY Use Swagger-Defined Endpoints**
```java
// Example from Swagger: POST /api/leave/request
@When("employee submits leave request")
public void employeeSubmitsLeaveRequest() {{
    response = given()
        .baseUri(LEAVE_BASE_URL)
        .header("Authorization", "Bearer " + jwtToken)
        .contentType(ContentType.JSON)
        .body(requestBody)
        .post("/api/leave/request"); // ✅ Exists in Swagger
}}

// ❌ WRONG - Endpoint not in Swagger
.post("/api/leave/submit") // ❌ Invented!
```

📦 **REQUIRED IMPORTS**
```java
import io.cucumber.java.en.*;
import io.cucumber.datatable.DataTable;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import static org.assertj.core.api.Assertions.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
```

🏗️ **COMPLETE CONTRACT-TEST EXAMPLE**
```java
package com.example.leaverequest.steps;

import io.cucumber.java.en.*;
import io.cucumber.datatable.DataTable;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import static org.assertj.core.api.Assertions.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LeaveRequestSteps {{
    
    private static final Logger logger = LoggerFactory.getLogger(LeaveRequestSteps.class);
    private static final String AUTH_BASE_URL = "http://localhost:9000";
    private static final String LEAVE_BASE_URL = "http://localhost:9001";
    
    private Response response;
    private String jwtToken = System.getenv("TEST_JWT_TOKEN");
    private Map<String, Object> requestBody = new HashMap<>();
    
    @Given("the employee is authenticated")
    public void theEmployeeIsAuthenticated() {{
        // Contract test: authentication is pre-configured
        assertThat(jwtToken)
            .as("Contract test setup: JWT token must be provided via TEST_JWT_TOKEN env var")
            .isNotBlank();
        logger.info("Using pre-configured authentication token");
    }}
    
    @Given("the employee has sufficient leave balance")
    public void theEmployeeHasSufficientLeaveBalance() {{
        // Contract test assumption: test environment has pre-seeded data
        // This is a business precondition, not an API contract to validate
        logger.info("Assuming leave balance precondition met in test data");
    }}
    
    @When("the employee submits a leave request with")
    public void theEmployeeSubmitsLeaveRequestWith(DataTable dataTable) {{
        // Contract test: validate API accepts structured request
        List<Map<String, String>> rows = dataTable.asMaps(String.class, String.class);
        for (Map<String, String> row : rows) {{
            requestBody.putAll(row);
        }}
        
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization", "Bearer " + jwtToken)
            .contentType(ContentType.JSON)
            .body(requestBody)
            .when()
            .post("/api/leave/request")
            .then()
            .extract()
            .response();
        
        logger.info("Contract test: POST /api/leave/request executed");
    }}
    
    @Then("the system should return status code {{int}}")
    public void theSystemShouldReturnStatusCode(int expectedStatus) {{
        // Contract test: validate HTTP contract
        assertThat(response.getStatusCode())
            .as("API contract: HTTP status code")
            .isEqualTo(expectedStatus);
    }}
    
    @Then("the system should display {{string}}")
    public void theSystemShouldDisplay(String expectedMessage) {{
        // Contract test: validate response structure contains message field
        String actualMessage = response.jsonPath().getString("message");
        assertThat(actualMessage)
            .as("API contract: message field must exist")
            .isNotNull();
        
        // Optional: loose semantic check (not strict equality)
        logger.info("Response message: {{}}", actualMessage);
    }}
    
    @Then("the leave request should have status {{string}}")
    public void theLeaveRequestShouldHaveStatus(String expectedStatus) {{
        // Contract test: validate response structure
        assertThat(response).isNotNull();
        assertThat(response.getStatusCode()).isBetween(200, 299);
        
        // Validate field exists (contract requirement)
        String actualStatus = response.jsonPath().getString("status");
        assertThat(actualStatus)
            .as("API contract: status field must exist in response")
            .isNotNull();
        
        logger.info("Leave request status from API: {{}}", actualStatus);
    }}
}}
```

⚠️ **VALIDATION RULES**
1. ✅ NO business logic assertions (>, <, ==specific values)
2. ✅ NO authentication/signup flows
3. ✅ NO data creation endpoints
4. ✅ ONLY Swagger-defined endpoints
5. ✅ Token injection (env var or placeholder)
6. ✅ Field existence validation, NOT value validation

🎯 **OUTPUT FORMAT**
Return ONLY the complete Java class code.
- Start with: package com.example...
- End with: }}
- NO markdown backticks
- NO explanatory text after code

Remember: These are CONTRACT tests, not BUSINESS tests."""),

            ("human", """Generate CONTRACT-LEVEL step definitions for the following specification.

📄 **GHERKIN SCENARIOS**
{gherkin_content}

🔌 **API SPECIFICATIONS** (Swagger-Defined Endpoints Only)
{api_context}

🏷️ **PROJECT INFO**
Service: {service_name}
Package: com.example.{package_name}.steps

**CONTRACT-TEST REQUIREMENTS**:
1. Use ONLY endpoints defined in Swagger specifications
2. Validate HTTP status codes and response structure
3. DO NOT validate business logic or field values
4. Authentication via injected token (System.getenv("TEST_JWT_TOKEN"))
5. NO user creation, NO data creation
6. For steps without API mapping: log assumption, do not invent endpoints

Generate the complete {service_name}Steps.java class following CONTRACT-TEST philosophy.

Return ONLY the Java code. Stop immediately after the final closing brace.""")
        ])
    
    def _create_test_runner_prompt(self) -> ChatPromptTemplate:
        """Create prompt for JUnit 4 Cucumber test runner"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a **Test Automation Expert** creating a Cucumber test runner.

🎯 **TASK**
Generate a JUnit 4 Cucumber test runner class for CONTRACT-LEVEL E2E tests.

📋 **MANDATORY REQUIREMENTS**

1. **Framework Version**
   - JUnit 4 (NOT JUnit 5)
   - Cucumber 7.x
   - NO Serenity BDD

2. **Required Annotations**
```java
@RunWith(Cucumber.class)
@CucumberOptions(
    features = "classpath:features",
    glue = "com.example.<package>.steps",
    plugin = {{
        "pretty",
        "html:target/cucumber-reports/cucumber.html",
        "json:target/cucumber-reports/cucumber.json"
    }},
    tags = "@contract",
    monochrome = true
)
```

3. **Required Imports**
```java
import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;
```

4. **Class Structure**
```java
package com.example.<package>;

import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "classpath:features",
    glue = "com.example.<package>.steps",
    plugin = {{
        "pretty",
        "html:target/cucumber-reports/cucumber.html",
        "json:target/cucumber-reports/cucumber.json"
    }},
    tags = "@contract",
    monochrome = true
)
public class ContractTestRunner {{
}}
```

⚠️ **CRITICAL**
- Class MUST be named "ContractTestRunner"
- Include tags = "@contract" to identify contract tests
- glue parameter MUST match step definitions package
- NO explanatory text after code

Return ONLY valid Java code."""),

            ("human", """Generate the Cucumber test runner for CONTRACT tests:

**Service**: {service_name}
**Package**: com.example.{package_name}
**Steps Package**: com.example.{package_name}.steps

Return ONLY the Java code. Stop after the final closing brace.""")
        ])
    
    def generate_pom_dependencies_snippet(self) -> str:
        """Generate dependencies snippet"""
        logger.info("📦 Generating Contract Test dependencies snippet...")
        
        snippet = """<!-- ============================================ -->
<!-- Contract-Level E2E Test Dependencies -->
<!-- Add these to your existing <dependencies> section -->
<!-- ============================================ -->

<!-- Cucumber -->
<dependency>
    <groupId>io.cucumber</groupId>
    <artifactId>cucumber-java</artifactId>
    <version>7.14.0</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>io.cucumber</groupId>
    <artifactId>cucumber-junit</artifactId>
    <version>7.14.0</version>
    <scope>test</scope>
</dependency>

<!-- RestAssured for API Testing -->
<dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>rest-assured</artifactId>
    <version>5.3.2</version>
    <scope>test</scope>
</dependency>

<!-- AssertJ for Fluent Assertions -->
<dependency>
    <groupId>org.assertj</groupId>
    <artifactId>assertj-core</artifactId>
    <version>3.24.2</version>
    <scope>test</scope>
</dependency>

<!-- SLF4J for Logging -->
<dependency>
    <groupId>org.slf4j</groupId>
    <artifactId>slf4j-api</artifactId>
    <version>2.0.9</version>
    <scope>test</scope>
</dependency>

<!-- JUnit 4 (if not already present) -->
<dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.13.2</version>
    <scope>test</scope>
</dependency>
"""
        return snippet
    
    def _validate_generated_code(self, code: str, file_type: str, valid_endpoints: Set[str] = None) -> Tuple[bool, List[str]]:
        """
        CONTRACT-FOCUSED code validation
        
        CRITICAL: This validation enforces contract-test philosophy
        """
        issues = []
        
        # 1. Package declaration
        if not code.strip().startswith("package "):
            issues.append("❌ Missing package declaration")
        
        # 2. Import statements
        if file_type in ["step_definitions", "runner"]:
            if "import" not in code:
                issues.append("❌ Missing import statements")
        
        # 3. Forbidden placeholders
        placeholder_patterns = [
            r'//\s*TODO',
            r'//\s*Implement',
            r'//\s*FIXME'
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"❌ Contains placeholder: {pattern}")
        
        # 4. CONTRACT-SPECIFIC VALIDATIONS
        if file_type == "step_definitions":
            # ❌ FORBIDDEN: Business logic assertions
            business_logic_patterns = [
                r'\.isGreaterThan\(',
                r'\.isLessThan\(',
                r'\.isGreaterThanOrEqualTo\(',
                r'\.isLessThanOrEqualTo\(',
            ]
            
            for pattern in business_logic_patterns:
                if re.search(pattern, code):
                    issues.append(f"❌ CRITICAL: Business logic assertion detected: {pattern}")
                    logger.error(f"CONTRACT VIOLATION: Business logic in contract test - {pattern}")
            
            # ❌ FORBIDDEN: User/data creation endpoints
            forbidden_endpoints = [
                r'\.post\(["\'].*?/signup["\']',
                r'\.post\(["\'].*?/register["\']',
                r'\.post\(["\'].*?/users["\']',
                r'\.queryParam\(["\']role["\']',
            ]
            
            for pattern in forbidden_endpoints:
                if re.search(pattern, code):
                    issues.append(f"❌ CRITICAL: Data creation/role spoofing detected: {pattern}")
                    logger.error(f"CONTRACT VIOLATION: Test data creation in contract test")
            
            # ❌ FORBIDDEN: Empty step methods
            step_methods = re.finditer(
                r'@(?:Given|When|Then|And|But)[\s\S]*?public\s+void\s+\w+\([^)]*\)\s*\{([\s\S]*?)\n\s*\}',
                code
            )

            for match in step_methods:
                body = match.group(1)
                body = re.sub(r'//.*', '', body)
                body = re.sub(r'/\*[\s\S]*?\*/', '', body)
                body = body.strip()

                if not body:
                    issues.append("❌ Empty step definition detected")
            
            # ✅ REQUIRED: Token injection pattern
            if "jwtToken" in code:
                if "System.getenv" not in code and "BEARER_TOKEN" not in code:
                    issues.append("⚠️ JWT token should use System.getenv() or placeholder")
            
            # ✅ VALIDATE: Only Swagger endpoints used
            if valid_endpoints:
                endpoint_pattern = r'\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
                used_endpoints = re.findall(endpoint_pattern, code)
                
                for method, endpoint in used_endpoints:
                    # Normalize endpoint (remove path params)
                    normalized = re.sub(r'\{[^}]+\}', '{id}', endpoint)
                    if normalized not in valid_endpoints:
                        issues.append(f"⚠️ Endpoint not in Swagger: {method.upper()} {endpoint}")
                        logger.warning(f"Potentially invented endpoint: {endpoint}")
        
        # 5. Runner validation
        if file_type == "runner":
            if "@RunWith(Cucumber.class)" not in code:
                issues.append("❌ Missing @RunWith(Cucumber.class)")
            if "@CucumberOptions" not in code:
                issues.append("❌ Missing @CucumberOptions")
            if "import org.junit.runner.RunWith;" not in code:
                issues.append("❌ Missing @RunWith import")
        
        # Determine validity
        critical_issues = [i for i in issues if i.startswith("❌ CRITICAL")]
        
        if critical_issues:
            logger.error(f"🚨 CRITICAL CONTRACT VIOLATIONS:")
            for issue in critical_issues:
                logger.error(f"   {issue}")
        
        standard_critical = [i for i in issues if i.startswith("❌") and "CRITICAL" not in i]
        is_valid = len(standard_critical) == 0 and len(critical_issues) == 0
        
        if issues:
            logger.warning(f"Code validation issues for {file_type}:")
            for issue in issues:
                if not issue.startswith("❌ CRITICAL"):  # Already logged
                    logger.warning(f"  {issue}")
        else:
            logger.success(f"✓ Contract-test validation passed for {file_type}")
        
        return is_valid, issues
    
    def extract_unique_steps(self, gherkin_content: str) -> List[str]:
        """Extract unique Gherkin step patterns"""
        steps = set()
        step_keywords = ['Given', 'When', 'Then', 'And', 'But']
        
        for line in gherkin_content.splitlines():
            line = line.strip()
            for keyword in step_keywords:
                if line.startswith(keyword):
                    step = line[len(keyword):].strip()
                    normalized = re.sub(r'"[^"]*"', '"{}"', step)
                    normalized = re.sub(r'\d+', '{}', normalized)
                    steps.add(f"{keyword} {normalized}")
                    break
        
        return sorted(list(steps))
    
    def _clean_code_output(self, text: str) -> str:
        """Clean LLM output to extract valid Java code"""
        text = re.sub(r"```java\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        
        lines = text.splitlines()
        code_start = -1
        code_end = len(lines)
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("package "):
                code_start = i
                break
        
        if code_start == -1:
            for i, line in enumerate(lines):
                if line.strip().startswith("import "):
                    code_start = i
                    break
        
        if code_start == -1:
            code_start = 0
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "}":
                code_end = i + 1
                break
        
        lines = lines[code_start:code_end]
        
        while lines and not lines[-1].strip():
            lines.pop()
        
        return "\n".join(line.rstrip() for line in lines)
    
    def _post_process_generated_code(self, code: str, file_type: str) -> str:
        """
        Post-process code WITHOUT auto-fixing
        
        CRITICAL: We do NOT auto-fix with fake assertions
        Let validation fail and retry instead
        """
        logger.info(f"🔧 Post-processing {file_type} code...")
        
        # 1. Clean output
        code = self._clean_code_output(code)
        
        # 2. Fix imports if missing
        if file_type == "runner":
            if "@RunWith" in code and "import org.junit.runner.RunWith;" not in code:
                logger.info("   Adding missing @RunWith import")
                code = re.sub(
                    r'(package [^;]+;)\n',
                    r'\1\n\nimport org.junit.runner.RunWith;\n',
                    code,
                    count=1
                )
        
        # 3. Normalize line endings
        code = code.replace('\r\n', '\n')
        
        # 4. Remove trailing text
        lines = code.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "}":
                code = "\n".join(lines[:i + 1])
                break
        
        # ❌ NO AUTO-FIXING of empty methods or business logic
        # Let validation catch it and retry
        
        return code
    
    def generate_step_definitions(
        self,
        gherkin_content: str,
        service_name: str,
        swagger_specs: Dict[str, Dict],
        max_retries: int = 3
    ) -> str:
        """Generate CONTRACT-LEVEL step definitions"""
        logger.info("🔨 Generating CONTRACT-LEVEL step definitions...")
        logger.info("   Scope: API structure validation, NOT business logic")
        
        api_context = get_api_context_multi(swagger_specs)
        unique_steps = self.extract_unique_steps(gherkin_content)
        valid_endpoints = self._extract_swagger_endpoints(swagger_specs)
        
        logger.info(f"   Found {len(unique_steps)} unique step patterns")
        logger.info(f"   Valid Swagger endpoints: {len(valid_endpoints)}")
        
        prompt = self._create_step_definition_prompt()
        chain = prompt | self.llm | self.parser
        
        package_name = service_name.replace("-", "").replace("_", "").lower()
        
        for attempt in range(max_retries):
            if attempt > 0:
                logger.warning(f"🔄 Retry attempt {attempt}/{max_retries} - enforcing contract-test rules")
            
            result = chain.invoke({
                "gherkin_content": gherkin_content,
                "api_context": api_context,
                "service_name": service_name,
                "package_name": package_name
            })
            
            cleaned_code = self._post_process_generated_code(result, "step_definitions")
            is_valid, issues = self._validate_generated_code(cleaned_code, "step_definitions", valid_endpoints)
            
            # Check for CRITICAL violations
            critical_violations = [i for i in issues if "CRITICAL" in i]
            
            if critical_violations:
                logger.error(f"🚨 CRITICAL contract violations detected (attempt {attempt + 1})")
                for violation in critical_violations:
                    logger.error(f"   {violation}")
                
                if attempt == max_retries - 1:
                    logger.error("⚠️ Max retries reached with CRITICAL violations")
                    logger.error("⚠️ Generated code violates contract-test philosophy")
                    raise ValueError("Code generation failed: Critical contract-test violations")
                
                continue  # Retry
            
            if is_valid:
                logger.success(f"✓ Contract-test code generated and validated (attempt {attempt + 1})")
                return cleaned_code
            else:
                warnings = [i for i in issues if i.startswith("⚠️")]
                logger.warning(f"✗ Validation warnings: {len(warnings)} (attempt {attempt + 1}/{max_retries})")
                
                if attempt == max_retries - 1:
                    logger.warning("⚠️ Max retries reached with warnings (no critical issues)")
                    return cleaned_code
        
        return cleaned_code
    
    def generate_test_runner(
        self,
        service_name: str,
        feature_count: int,
        max_retries: int = 2
    ) -> str:
        """Generate JUnit 4 Cucumber test runner"""
        logger.info("🔨 Generating CONTRACT test runner...")
        
        prompt = self._create_test_runner_prompt()
        chain = prompt | self.llm | self.parser
        
        package_name = service_name.replace("-", "").replace("_", "").lower()
        
        for attempt in range(max_retries):
            if attempt > 0:
                logger.warning(f"🔄 Retry attempt {attempt}/{max_retries}")
            
            result = chain.invoke({
                "service_name": service_name,
                "package_name": package_name,
                "feature_count": feature_count
            })
            
            cleaned_code = self._post_process_generated_code(result, "runner")
            is_valid, _ = self._validate_generated_code(cleaned_code, "runner")
            
            if is_valid:
                logger.success(f"✓ Test runner generated and validated (attempt {attempt + 1})")
                return cleaned_code
            elif attempt == max_retries - 1:
                logger.warning("⚠️ Test runner has issues but proceeding")
        
        return cleaned_code
    
    def save_test_files(
        self,
        service_name: str,
        step_definitions: str,
        test_runner: str,
        pom_dependencies: str
    ) -> List[Path]:
        """Save contract test files"""
        saved_files = []
        base_path = self.settings.paths.tests_dir
        
        package_name = service_name.replace("-", "").replace("_", "").lower()
        java_base = base_path / "src" / "test" / "java" / "com" / "example" / package_name
        
        # 1. Save step definitions
        steps_dir = java_base / "steps"
        steps_dir.mkdir(parents=True, exist_ok=True)
        
        class_name = self._to_camel_case(service_name) + "Steps"
        steps_file = steps_dir / f"{class_name}.java"
        steps_file.write_text(step_definitions, encoding="utf-8")
        saved_files.append(steps_file)
        logger.success(f"✔ Saved: {steps_file.relative_to(base_path)}")
        
        # 2. Save test runner
        runner_file = java_base / "ContractTestRunner.java"
        runner_file.write_text(test_runner, encoding="utf-8")
        saved_files.append(runner_file)
        logger.success(f"✔ Saved: {runner_file.relative_to(base_path)}")
        
        # 3. Save setup instructions
        setup_file = base_path / "CONTRACT_TEST_SETUP.md"
        setup_content = f"""# Contract-Level E2E Test Setup for {service_name}

## 🎯 **Test Type: CONTRACT-LEVEL E2E**

These tests validate:
✅ API endpoints exist and respond
✅ Request/response structure compatibility
✅ Service-to-service communication

These tests DO NOT validate:
❌ Business logic (e.g., balance checks, approval rules)
❌ Authentication/Authorization (assumes pre-configured tokens)
❌ Test data creation (assumes data exists or uses stubs)

## 📦 Required Dependencies

Add these to your microservice `pom.xml`:
```xml
{pom_dependencies}
```

## 🔐 Authentication Setup

Contract tests require a pre-configured JWT token:
```bash
# Set environment variable before running tests
export TEST_JWT_TOKEN="your-valid-jwt-token-here"

# Or in CI/CD (GitHub Actions example)
env:
  TEST_JWT_TOKEN: ${{{{ secrets.TEST_JWT_TOKEN }}}}
```

## 🚀 Running Tests
```bash
# With token
export TEST_JWT_TOKEN="valid-token"
mvn test -Dtest=ContractTestRunner

# Or run all contract tests
mvn test -Dcucumber.filter.tags="@contract"
```

## 📝 Important Notes

1. **Test Data**: These tests assume data exists. Pre-seed your test environment.
2. **Authentication**: Tokens must be valid. Use a dedicated test user.
3. **Environment**: Point to test/staging environment, NOT production.
4. **CI/CD**: Store JWT token as secret, inject via environment variable.

## 🏗️ Test Philosophy

> "The TestWriter agent generates contract-level end-to-end API tests, 
> validating service interoperability and API compatibility rather than 
> business rules, data correctness, or authorization semantics."

## ⚠️ What These Tests Do NOT Cover

- Business rule validation (use unit/integration tests)
- Authorization logic (use security-focused tests)
- Data correctness (use business logic tests)
- Performance/load (use dedicated performance tests)

## 📁 Generated Files

- **Step Definitions**: `{steps_file.relative_to(base_path)}`
- **Test Runner**: `{runner_file.relative_to(base_path)}`
"""
        setup_file.write_text(setup_content, encoding="utf-8")
        saved_files.append(setup_file)
        logger.success(f"✔ Saved: {setup_file.relative_to(base_path)}")
        
        return saved_files
    
    def _to_camel_case(self, text: str) -> str:
        """Convert text to CamelCase"""
        parts = re.split(r'[-_\s]+', text)
        return ''.join(word.capitalize() for word in parts if word)
    
    def write_tests(self, state: TestAutomationState) -> TestAutomationState:
        """Main entry point - generates CONTRACT-LEVEL test code"""
        start_time = time.time()
        logger.info(f"🚀 Contract-Level Test Writer starting for: {state.service_name}")
        logger.info(f"📋 Test Philosophy: API Structure Validation (NOT Business Logic)")
        
        validation_issues = []
        
        try:
            # Prepare Swagger specs
            if not hasattr(state, 'swagger_specs') or not state.swagger_specs:
                logger.warning("⚠️ No swagger_specs found in state")
                swagger_specs = {}
                if state.swagger_spec:
                    swagger_specs["primary"] = state.swagger_spec
            else:
                swagger_specs = state.swagger_specs
            
            logger.info(f"📋 Using {len(swagger_specs)} Swagger specification(s)")
            for service_key in swagger_specs.keys():
                logger.info(f"   - {service_key}")
            
            # Analyze Gherkin
            unique_steps = self.extract_unique_steps(state.gherkin_content)
            logger.info(f"📋 Found {len(unique_steps)} unique step patterns")
            
            # Generate step definitions
            logger.info("1️⃣ Generating CONTRACT-LEVEL step definitions...")
            step_definitions = self.generate_step_definitions(
                gherkin_content=state.gherkin_content,
                service_name=state.service_name,
                swagger_specs=swagger_specs,
                max_retries=3
            )
            
            # Generate test runner
            logger.info("2️⃣ Generating CONTRACT test runner...")
            test_runner = self.generate_test_runner(
                service_name=state.service_name,
                feature_count=len(state.gherkin_files),
                max_retries=2
            )
            
            # Generate dependencies
            logger.info("3️⃣ Generating Maven dependencies...")
            pom_dependencies = self.generate_pom_dependencies_snippet()
            
            # Final validation
            logger.info("4️⃣ Running contract-test validation...")
            valid_endpoints = self._extract_swagger_endpoints(swagger_specs)
            _, step_issues = self._validate_generated_code(step_definitions, "step_definitions", valid_endpoints)
            _, runner_issues = self._validate_generated_code(test_runner, "runner")
            
            validation_issues = step_issues + runner_issues
            
            # Check for critical violations
            critical = [i for i in validation_issues if "CRITICAL" in i]
            if critical:
                logger.error(f"🚨 {len(critical)} CRITICAL contract violations detected")
                raise ValueError("Contract-test generation failed with critical violations")
            
            if validation_issues:
                logger.warning(f"⚠️ Found {len(validation_issues)} validation warnings")
            else:
                logger.success("✓ All contract-test validation passed")
            
            # Save files
            logger.info("5️⃣ Saving contract test files...")
            saved_files = self.save_test_files(
                service_name=state.service_name,
                step_definitions=step_definitions,
                test_runner=test_runner,
                pom_dependencies=pom_dependencies
            )
            
            # Update state
            state.test_code = {
                "step_definitions": step_definitions,
                "test_runner": test_runner,
                "pom_dependencies": pom_dependencies
            }
            state.test_files = [str(f) for f in saved_files]
            
            for issue in validation_issues:
                state.add_warning(f"Code quality: {issue}")
            
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="test_writer",
                status=AgentStatus.SUCCESS,
                duration_ms=duration,
                output_data={
                    "test_type": "CONTRACT_LEVEL_E2E",
                    "files_generated": len(saved_files),
                    "swagger_specs_used": len(swagger_specs),
                    "step_definitions_lines": len(step_definitions.splitlines()),
                    "unique_steps_implemented": len(unique_steps),
                    "validation_issues": len(validation_issues),
                    "critical_violations": len([i for i in validation_issues if "CRITICAL" in i]),
                    "test_files": [str(f.relative_to(self.settings.paths.tests_dir)) for f in saved_files]
                }
            )
            state.add_agent_output(agent_output)
            
            logger.success(f"✅ Contract-level tests generated in {duration:.0f}ms")
            logger.info(f"   Test Type: CONTRACT-LEVEL E2E")
            logger.info(f"   Files: {len(saved_files)}")
            logger.info(f"   Validation Issues: {len(validation_issues)}")
            
        except Exception as e:
            logger.error(f"❌ Contract-test generation failed: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="test_writer",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(e)
            )
            state.add_agent_output(agent_output)
            state.add_error(f"Contract-test generation failed: {str(e)}")
        
        return state


def test_writer_node(state: TestAutomationState) -> TestAutomationState:
    """LangGraph node wrapper for Contract-Level Test Writer"""
    agent = TestWriterAgent()
    return agent.write_tests(state)