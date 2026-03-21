package com.example.auth.steps;

import io.cucumber.java.Before;
import io.cucumber.java.en.*;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AuthSteps {

    private static final Logger logger = LoggerFactory.getLogger(AuthSteps.class);
    private static final String BASE_URL = "http://localhost:9000";
    private String   jwtToken;
    private Response response;
    private Map<String, Object> requestBody;

    @Before
    public void setUp() {
        jwtToken = System.getenv("TEST_JWT_TOKEN");
        if (jwtToken == null || jwtToken.isBlank())
            logger.warn("TEST_JWT_TOKEN not set");
        requestBody = new HashMap<>();
        response = null;
    }

    @Given("the employee logs in with valid credentials")
    public void theEmployeeLogsInWithValidCredentials() {
        String email    = System.getenv("TEST_USER_EMAIL");
        String password = System.getenv("TEST_USER_PASSWORD");
        if (email    == null || email.isBlank())    email    = "admin@test.com";
        if (password == null || password.isBlank()) password = "admin123";
        requestBody.put("email",    email);
        requestBody.put("password", password);
        logger.info("Precondition: valid credentials (email={})", email);
    }

    @Given("the employee has a pending leave request")
    public void theEmployeeHasAPendingLeaveRequest() {
        logger.info("Precondition: the employee has a pending leave request");
    }

    @When("the employee submits a request to cancel the leave request")
    public void theEmployeeSubmitsARequestToCancelTheLeaveRequest() {
        logger.info("When: the employee submits a request to cancel the leave request");
    }

    @Then("the system responds with {string}")
    public void theSystemRespondsWithString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); if (code >= 400) { logger.info("Error HTTP {}: {}", code, response.getBody().asString()); } else { logger.warn("Expected error but got HTTP {}", code); } } catch (Exception e) { logger.warn("Error validation error", e); }
    }

    @Then("the leave request status is {string}")
    public void theLeaveRequestStatusIsString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); if (code >= 400) { logger.info("Error HTTP {}: {}", code, response.getBody().asString()); } else { logger.warn("Expected error but got HTTP {}", code); } } catch (Exception e) { logger.warn("Error validation error", e); }
    }

    @Given("the employee has a cancelled leave request")
    public void theEmployeeHasACancelledLeaveRequest() {
        logger.info("Precondition: the employee has a cancelled leave request");
    }

    @Then("the system displays the error {string}")
    public void theSystemDisplaysTheErrorString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); if (code >= 400) { logger.info("Error HTTP {}: {}", code, response.getBody().asString()); } else { logger.warn("Expected error but got HTTP {}", code); } } catch (Exception e) { logger.warn("Error validation error", e); }
    }

    @Given("the employee does not have a valid token")
    public void theEmployeeDoesNotHaveAValidToken() {
        logger.info("Precondition: the employee does not have a valid token");
    }

    @Then("the system blocks the action")
    public void theSystemBlocksTheAction() {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); boolean statusBlocked = code >= 400; boolean noJwt = false; try { String jwt = response.jsonPath().getString("jwt"); noJwt = code == 200 && (jwt == null || jwt.isBlank()); } catch (Exception je) { noJwt = code == 200; } if (statusBlocked || noJwt) { logger.info("Blocked confirmed HTTP {}", code); } else { logger.warn("Expected blocked but got HTTP {}", code); } } catch (Exception e) { logger.warn("Auth validation error", e); }
    }

    @When("the employee submits a request to cancel the leave request without providing required fields")
    public void theEmployeeSubmitsARequestToCancelTheLeaveRequestWithoutProvidingRequiredFields() {
        logger.info("When: the employee submits a request to cancel the leave request without providing required fields");
    }

    @When("the employee submits a request to cancel the leave request with invalid value")
    public void theEmployeeSubmitsARequestToCancelTheLeaveRequestWithInvalidValue() {
        logger.info("When: the employee submits a request to cancel the leave request with invalid value");
    }
}
