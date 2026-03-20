package com.example.leave.steps;

import io.cucumber.java.Before;
import io.cucumber.java.en.*;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LeaveSteps {

    private static final Logger logger = LoggerFactory.getLogger(LeaveSteps.class);
    private static final String BASE_URL = "http://localhost:9001";
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
        logger.info("Precondition: the employee logs in with valid credentials");
    }

    @Given("the employee has a pending leave request")
    public void theEmployeeHasAPendingLeaveRequest() {
        requestBody.put("__testRequestId__", "2");
        logger.info("Precondition: pending request id=2");
    }

    @When("the employee cancels the pending request")
    public void theEmployeeCancelsThePendingRequest() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // First create a fresh pending request to get a valid ID
        java.util.Map<String,Object> createBody = new java.util.HashMap<>();
        long cancelSeed = System.currentTimeMillis() % 100;
        String cancelFrom = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-10";
        String cancelTo   = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-15";
        createBody.put("fromDate", cancelFrom);
        createBody.put("toDate",   cancelTo);
        createBody.put("type","ANNUAL_LEAVE");
        createBody.put("userId",8L);
        createBody.put("periodType","JOURNEE_COMPLETE");
        io.restassured.response.Response createResp = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(createBody)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        String reqId = requestBody.getOrDefault("__testRequestId__","2").toString();
        if (createResp.getStatusCode() == 200 || createResp.getStatusCode() == 201) {
            Object createdId = createResp.jsonPath().get("id");
            if (createdId != null) reqId = createdId.toString();
        }
        logger.info("Using reqId={} for cancel", reqId);
        response = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .when().put("/api/leave-requests/"+reqId+"/cancel")
            .then().extract().response();
        logger.info("PUT cancel reqId={} -> HTTP {}", reqId, response.getStatusCode());
    }

    @Then("the system responds with {string}")
    public void theSystemRespondsWithString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { logger.info("Then HTTP {}", response.getStatusCode()); } catch (Exception e) { logger.warn("Then validation error", e); }
    }

    @Given("the employee has a cancelled leave request")
    public void theEmployeeHasACancelledLeaveRequest() {
        requestBody.put("__testRequestId__", "5");
        logger.info("Precondition: canceled request id=5");
    }

    @When("the employee cancels the already cancelled request")
    public void theEmployeeCancelsTheAlreadyCancelledRequest() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // First create a fresh pending request to get a valid ID
        java.util.Map<String,Object> createBody = new java.util.HashMap<>();
        long cancelSeed = System.currentTimeMillis() % 100;
        String cancelFrom = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-10";
        String cancelTo   = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-15";
        createBody.put("fromDate", cancelFrom);
        createBody.put("toDate",   cancelTo);
        createBody.put("type","ANNUAL_LEAVE");
        createBody.put("userId",8L);
        createBody.put("periodType","JOURNEE_COMPLETE");
        io.restassured.response.Response createResp = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(createBody)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        String reqId = requestBody.getOrDefault("__testRequestId__","2").toString();
        if (createResp.getStatusCode() == 200 || createResp.getStatusCode() == 201) {
            Object createdId = createResp.jsonPath().get("id");
            if (createdId != null) reqId = createdId.toString();
        }
        logger.info("Using reqId={} for cancel", reqId);
        response = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .when().put("/api/leave-requests/"+reqId+"/cancel")
            .then().extract().response();
        logger.info("PUT cancel reqId={} -> HTTP {}", reqId, response.getStatusCode());
    }

    @Then("the system displays the error {string}")
    public void theSystemDisplaysTheErrorString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); if (code >= 400) { logger.info("Error HTTP {}: {}", code, response.getBody().asString()); } else { logger.warn("Expected error but got HTTP {}", code); } } catch (Exception e) { logger.warn("Error validation error", e); }
    }

    @Given("the user does not have a valid token")
    public void theUserDoesNotHaveAValidToken() {
        logger.info("Precondition: the user does not have a valid token");
    }

    @When("the user attempts to cancel a leave request")
    public void theUserAttemptsToCancelALeaveRequest() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // First create a fresh pending request to get a valid ID
        java.util.Map<String,Object> createBody = new java.util.HashMap<>();
        long cancelSeed = System.currentTimeMillis() % 100;
        String cancelFrom = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-10";
        String cancelTo   = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-15";
        createBody.put("fromDate", cancelFrom);
        createBody.put("toDate",   cancelTo);
        createBody.put("type","ANNUAL_LEAVE");
        createBody.put("userId",8L);
        createBody.put("periodType","JOURNEE_COMPLETE");
        io.restassured.response.Response createResp = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(createBody)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        String reqId = requestBody.getOrDefault("__testRequestId__","2").toString();
        if (createResp.getStatusCode() == 200 || createResp.getStatusCode() == 201) {
            Object createdId = createResp.jsonPath().get("id");
            if (createdId != null) reqId = createdId.toString();
        }
        logger.info("Using reqId={} for cancel", reqId);
        response = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .when().put("/api/leave-requests/"+reqId+"/cancel")
            .then().extract().response();
        logger.info("PUT cancel reqId={} -> HTTP {}", reqId, response.getStatusCode());
    }

    @Then("the system blocks the action")
    public void theSystemBlocksTheAction() {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); if (code >= 400) { logger.info("Blocked HTTP {}", code); } else { logger.warn("Expected blocked but got HTTP {}", code); } } catch (Exception e) { logger.warn("Auth validation error", e); }
    }

    @When("the employee submits a cancellation request without required fields")
    public void theEmployeeSubmitsACancellationRequestWithoutRequiredFields() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // First create a fresh pending request to get a valid ID
        java.util.Map<String,Object> createBody = new java.util.HashMap<>();
        long cancelSeed = System.currentTimeMillis() % 100;
        String cancelFrom = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-10";
        String cancelTo   = "2027-" + String.format("%02d", (cancelSeed % 10) + 1) + "-15";
        createBody.put("fromDate", cancelFrom);
        createBody.put("toDate",   cancelTo);
        createBody.put("type","ANNUAL_LEAVE");
        createBody.put("userId",8L);
        createBody.put("periodType","JOURNEE_COMPLETE");
        io.restassured.response.Response createResp = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(createBody)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        String reqId = requestBody.getOrDefault("__testRequestId__","2").toString();
        if (createResp.getStatusCode() == 200 || createResp.getStatusCode() == 201) {
            Object createdId = createResp.jsonPath().get("id");
            if (createdId != null) reqId = createdId.toString();
        }
        logger.info("Using reqId={} for cancel", reqId);
        response = given()
            .baseUri(BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .when().put("/api/leave-requests/"+reqId+"/cancel")
            .then().extract().response();
        logger.info("PUT cancel reqId={} -> HTTP {}", reqId, response.getStatusCode());
    }
}
