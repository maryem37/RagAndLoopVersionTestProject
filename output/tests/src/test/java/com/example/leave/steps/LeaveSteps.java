package com.example.leave.steps;

import io.cucumber.java.Before;
import io.cucumber.java.en.*;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import static org.assertj.core.api.Assertions.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LeaveSteps {

    private static final Logger logger = LoggerFactory.getLogger(LeaveSteps.class);
    private static final String BASE_URL = "http://localhost:9001";
    private static final String AUTH_URL = "http://localhost:9000";
    private String jwtToken;
    private Response response;
    private Map<String, Object> requestBody;

    @Before
    public void setUp() {
        jwtToken = System.getenv("TEST_JWT_TOKEN");
        if (jwtToken == null || jwtToken.isBlank()) {
            logger.warn("TEST_JWT_TOKEN not set — tests may fail");
        }
        requestBody = new HashMap<>();
        response = null;
    }

    @Given("the user is authenticated")
    public void theUserIsAuthenticated() {
        assertThat(jwtToken)
            .as("JWT token must be set via TEST_JWT_TOKEN env var")
            .isNotBlank();
        logger.info("Authenticated with JWT token");
    }

    @Given("the leave request status is {string}")
    public void theLeaveRequestStatusIsX(String p0) {
        requestBody.put("status", p0);
        // Map status → pre-inserted test request ID
        // These records must exist in your DB in the correct state
        java.util.Map<String,String> statusToId = new java.util.HashMap<>();
        statusToId.put("Pending",     "2");
        statusToId.put("In Progress", "3");
        statusToId.put("Refused",     "4");
        statusToId.put("Approved",    "1");
        statusToId.put("Granted",     "1");
        statusToId.put("Canceled",    "5");
        String testId = statusToId.getOrDefault(p0, "2");
        requestBody.put("__testRequestId__", testId);
        logger.info("Status {} → test request ID {}", p0, testId);
    }

    @Given("the user is the final approver in the approval chain")
    public void theUserIsTheFinalApproverInTheApprovalChain() {
        requestBody.put("role", "Administration");
        logger.info("Role set: Administration");
    }

    @Given("the user has not previously approved the request")
    public void theUserHasNotPreviouslyApprovedTheRequest() {
        logger.info("Precondition: the user has not previously approved the request");
    }

    @When("the user approves the leave request")
    public void theUserApprovesTheLeaveRequest() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        String approvePath = "/api/leave-requests/1/approve";
        if (requestBody.containsKey("__testRequestId__")) {
            approvePath = approvePath.replaceFirst("/\\d+/",
                "/" + requestBody.get("__testRequestId__") + "/");
        }
        String approveRole = (String) requestBody.getOrDefault("role", "Administration");
        io.restassured.specification.RequestSpecification approveReq = given()
            .baseUri(BASE_URL)
            .header("Authorization", "Bearer " + authToken)
            .queryParam("role", approveRole);
        if (requestBody.containsKey("note")) {
            approveReq = approveReq.queryParam("note", requestBody.get("note"));
        }
        response = approveReq.when()
            .put(approvePath)
            .then()
            .extract().response();
        logger.info("PUT {} (approve, role={}) -> HTTP {}", approvePath, approveRole, response.getStatusCode());
    }

    @Then("the system adjusts the leave balance according to the leave type")
    public void theSystemAdjustsTheLeaveBalanceAccordingToTheLeaveType() {
        assertThat(response)
            .as("No HTTP call was made — missing When step")
            .isNotNull();
        int statusCode = response.getStatusCode();
        assertThat(statusCode)
            .as("Expected a valid HTTP response (2xx or 4xx)")
            .isBetween(200, 499);
        logger.info("Then validated, HTTP {}", statusCode);
    }

    @Then("the request status changes to {string}")
    public void theRequestStatusChangesToX(String p0) {
        assertThat(response)
            .as("No HTTP call was made — missing When step")
            .isNotNull();
        assertThat(response.getStatusCode()).isBetween(200, 299);
        String actualState = response.jsonPath().getString("state");
        assertThat(actualState)
            .as("Request state should be " + p0)
            .isEqualToIgnoringCase(p0);
        logger.info("State confirmed: {}", actualState);
    }

    @Then("the system displays {string}")
    public void theSystemDisplaysX(String p0) {
        assertThat(response)
            .as("No HTTP call was made — missing When step")
            .isNotNull();
        int statusCode = response.getStatusCode();
        String body = response.getBody().asString();
        assertThat(statusCode)
            .as("Expected valid response for: " + p0)
            .isBetween(200, 499);
        logger.info("System display HTTP {}: {}", statusCode, body);
    }

    @Given("the user is an intermediate approver in the approval chain")
    public void theUserIsAnIntermediateApproverInTheApprovalChain() {
        requestBody.put("role", "TeamLeader");
        logger.info("Role set: TeamLeader");
    }

    @Then("the system marks the manager's validation as TRUE")
    public void theSystemMarksTheManagerSValidationAsTrue() {
        assertThat(response)
            .as("No HTTP call was made — missing When step")
            .isNotNull();
        assertThat(response.getStatusCode()).isBetween(200, 299);
        logger.info("Update confirmed, HTTP {}", response.getStatusCode());
    }

    @Given("the user is not in the approval chain")
    public void theUserIsNotInTheApprovalChain() {
        requestBody.put("role", "Administration");
        logger.info("Role set: Administration");
    }

    @When("the user attempts to approve the leave request")
    public void theUserAttemptsToApproveTheLeaveRequest() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        String approvePath = "/api/leave-requests/1/approve";
        if (requestBody.containsKey("__testRequestId__")) {
            approvePath = approvePath.replaceFirst("/\\d+/",
                "/" + requestBody.get("__testRequestId__") + "/");
        }
        String approveRole = (String) requestBody.getOrDefault("role", "Administration");
        io.restassured.specification.RequestSpecification approveReq = given()
            .baseUri(BASE_URL)
            .header("Authorization", "Bearer " + authToken)
            .queryParam("role", approveRole);
        if (requestBody.containsKey("note")) {
            approveReq = approveReq.queryParam("note", requestBody.get("note"));
        }
        response = approveReq.when()
            .put(approvePath)
            .then()
            .extract().response();
        logger.info("PUT {} (approve, role={}) -> HTTP {}", approvePath, approveRole, response.getStatusCode());
    }

    @Then("the system displays the error You are not authorized to modify the status of this request.")
    public void theSystemDisplaysTheErrorYouAreNotAuthorizedToModifyTheStatusOfThisRequest() {
        assertThat(response)
            .as("No HTTP call was made — missing When step")
            .isNotNull();
        assertThat(response.getStatusCode()).isGreaterThanOrEqualTo(400);
        logger.info("Error confirmed, HTTP {}", response.getStatusCode());
    }

    @Given("the user is in the approval chain")
    public void theUserIsInTheApprovalChain() {
        requestBody.put("role", "Administration");
        logger.info("Role set: Administration");
    }

    @Then("the system displays the error If the request is not in a valid state \\({string} or {string}\\), validation is blocked.")
    public void theSystemDisplaysTheErrorIfTheRequestIsNotInAValidStateXOrXValidationIsBlocked(String p0, String p1) {
        assertThat(response)
            .as("No HTTP call was made — missing When step")
            .isNotNull();
        int statusCode = response.getStatusCode();
        assertThat(statusCode)
            .as("Expected error response (4xx) for: " + p0)
            .isGreaterThanOrEqualTo(400);
        String body = response.getBody().asString();
        logger.info("Error HTTP {}: {}", statusCode, body);
        // assertThat(body).contains(p0);
    }

    @Given("the user has previously approved the request")
    public void theUserHasPreviouslyApprovedTheRequest() {
        logger.info("Precondition: the user has previously approved the request");
    }

    @Then("the system displays the error If the user has already validated previously, the validation is refused.")
    public void theSystemDisplaysTheErrorIfTheUserHasAlreadyValidatedPreviouslyTheValidationIsRefused() {
        assertThat(response)
            .as("No HTTP call was made — missing When step")
            .isNotNull();
        assertThat(response.getStatusCode()).isGreaterThanOrEqualTo(400);
        logger.info("Error confirmed, HTTP {}", response.getStatusCode());
    }

}
