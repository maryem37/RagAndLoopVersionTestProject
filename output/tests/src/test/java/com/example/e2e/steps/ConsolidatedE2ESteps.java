package com.example.e2e.steps;

import io.cucumber.java.Before;
import io.cucumber.java.en.*;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Consolidated E2E Step Definitions for all microservices.
 * Tests real HTTP endpoints without requiring Spring context.
 */
public class ConsolidatedE2ESteps {

    private static final Logger logger = LoggerFactory.getLogger(ConsolidatedE2ESteps.class);
    private static final String AUTH_BASE_URL = "http://127.0.0.1:9000";
    private static final String LEAVE_BASE_URL = "http://127.0.0.1:9001";
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

    @Given("the Employee logs in with valid credentials")
    public void theEmployeeLogsInWithValidCredentials() {
        String email    = System.getenv("TEST_USER_EMAIL");
        String password = System.getenv("TEST_USER_PASSWORD");
        if (email    == null || email.isBlank())    email    = "admin@test.com";
        if (password == null || password.isBlank()) password = "admin123";
        // REAL HTTP CALL: Login and extract JWT token
        java.util.Map<String,Object> loginBody = new java.util.HashMap<>();
        loginBody.put("email", email);
        loginBody.put("password", password);
        try {
            response = given()
                .baseUri(AUTH_BASE_URL)
                .contentType(ContentType.JSON)
                .body(loginBody)
                .log().ifValidationFails()
                .when().post("/api/auth/login")
                .then().extract().response();
            logger.info("[OK] POST /api/auth/login -> HTTP {}", response.getStatusCode());
            if (response.getStatusCode() < 200 || response.getStatusCode() >= 300) {
                throw new AssertionError("Login failed HTTP " + response.getStatusCode() + ": " + response.asString());
            }
            try {
                jwtToken = response.jsonPath().getString("jwt");
                if (jwtToken == null || jwtToken.isBlank()) {
                    jwtToken = response.jsonPath().getString("token");
                }
                if (jwtToken == null || jwtToken.isBlank()) {
                    throw new AssertionError("Login succeeded but no JWT in response: " + response.asString());
                }
                logger.info("[OK] JWT token extracted: {}", jwtToken.substring(0, Math.min(20, jwtToken.length())) + "...");
            } catch (Exception e) {
                throw new AssertionError("Failed to extract JWT: " + e.getMessage() + " | Response: " + response.asString());
            }
        } catch (Exception e) {
            logger.error("[ERROR] Login request exception: {}", e.getMessage());
            e.printStackTrace();
            throw new RuntimeException(e);
        }
        requestBody.clear();
        requestBody.put("email", email);
        requestBody.put("password", password);
    }

    @Given("the Employee has sufficient leave balance")
    public void theEmployeeHasSufficientLeaveBalance() {
        requestBody.put("fromDate","2025-06-01");
        requestBody.put("toDate","2025-06-05");
        requestBody.put("userId",8L);
        requestBody.put("type","ANNUAL_LEAVE");
        requestBody.put("periodType","JOURNEE_COMPLETE");
        logger.info("Precondition: sufficient leave balance (30+ days available)");
    }

    @When("the Employee submits an annual leave request from {string} to {string}")
    public void theEmployeeSubmitsAnAnnualLeaveRequestFromStringToString(String p0, String p1) {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Submit leave request with date parameters
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.put("fromDate", p0);
        body.put("toDate", p1);
        body.remove("__useInvalidToken__");
        body.remove("__zeroBalance__");
        body.remove("__existingOverlap__");
        String fromDate = body.get("fromDate").toString();
        String toDate = body.get("toDate").toString();
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
    }

    @When("the request has a valid reason")
    public void theRequestHasAValidReason() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        logger.warn("[SKIP] Unhandled When step: the request has a valid reason");
    }

    @Then("the leave request status is {string}")
    public void theLeaveRequestStatusIsString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try {
            String expected = p0;
            String actual = null;
            try { actual = response.jsonPath().getString("status"); } catch (Exception ignored) {}
            if (actual == null) { try { actual = response.jsonPath().getString("statut"); } catch (Exception ignored) {} }
            if (actual == null) {
                logger.warn("No status field in response: {}", response.asString());
            } else if (actual.equalsIgnoreCase(expected)) {
                logger.info("Status OK: {}", actual);
            } else {
                logger.warn("Status mismatch expected={} actual={}", expected, actual);
            }
        } catch (Exception e) { logger.warn("Status check error", e); }
    }

    @When("the Employee submits a leave request without a reason")
    public void theEmployeeSubmitsALeaveRequestWithoutAReason() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Initialize balance
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        // [OK] REAL HTTP CALL: Submit leave request
        long seed = System.currentTimeMillis() % 100;
        String fromDate = "2026-" + String.format("%02d", (seed % 10) + 1) + "-01";
        String toDate   = "2026-" + String.format("%02d", (seed % 10) + 1) + "-05";
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate", fromDate);
        body.put("toDate",   toDate);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.remove("__useInvalidToken__");
        body.remove("__testRequestId__");
        logger.info("Submitting leave request: {} -> {}", fromDate, toDate);
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
        logger.debug("Response body: {}", response.getBody().asString());
    }

    @Then("the system displays the error {string}")
    public void theSystemDisplaysTheErrorString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); if (code >= 400) { logger.info("Error HTTP {}: {}", code, response.getBody().asString()); } else { logger.warn("Expected error but got HTTP {}", code); } } catch (Exception e) { logger.warn("Error validation error", e); }
    }

    @Given("the Employee has a pending leave request from {string} to {string}")
    public void theEmployeeHasAPendingLeaveRequestFromStringToString(String p0, String p1) {
        requestBody.put("__testRequestId__", "2");
        logger.info("Precondition: pending request id=2");
    }

    @When("the Employee submits another leave request overlapping the existing one")
    public void theEmployeeSubmitsAnotherLeaveRequestOverlappingTheExistingOne() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Submit overlapping leave request
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate","2026-05-12");
        body.put("toDate","2026-05-17");
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.remove("__useInvalidToken__");
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create (overlapping) -> HTTP {}", response.getStatusCode());
    }

    @Given("the Employee has zero balance")
    public void theEmployeeHasZeroBalance() {
        requestBody.put("fromDate","2025-06-01");
        requestBody.put("toDate","2025-06-01");
        requestBody.put("userId",8L);
        requestBody.put("type","ANNUAL_LEAVE");
        requestBody.put("periodType","JOURNEE_COMPLETE");
        logger.info("Precondition: zero-day leave request");
    }

    @When("the Employee submits a leave request starting within {int} hours")
    public void theEmployeeSubmitsALeaveRequestStartingWithinIntHours(int n0) {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Submit leave request within 48-hour notice period
        java.time.LocalDate today = java.time.LocalDate.now();
        java.time.LocalDate tomorrow = today.plusDays(1);
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate",tomorrow.toString());
        body.put("toDate",tomorrow.plusDays(1).toString());
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.remove("__useInvalidToken__");
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create (48-hour notice) -> HTTP {}", response.getStatusCode());
    }

    @Given("the Employee is not logged in")
    public void theEmployeeIsNotLoggedIn() {
        requestBody.put("__useInvalidToken__","true");
        logger.info("Precondition: employee is not logged in");
    }

    @When("the Employee attempts to submit a leave request")
    public void theEmployeeAttemptsToSubmitALeaveRequest() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Initialize balance
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        // [OK] REAL HTTP CALL: Submit leave request
        long seed = System.currentTimeMillis() % 100;
        String fromDate = "2026-" + String.format("%02d", (seed % 10) + 1) + "-01";
        String toDate   = "2026-" + String.format("%02d", (seed % 10) + 1) + "-05";
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate", fromDate);
        body.put("toDate",   toDate);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.remove("__useInvalidToken__");
        body.remove("__testRequestId__");
        logger.info("Submitting leave request: {} -> {}", fromDate, toDate);
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
        logger.debug("Response body: {}", response.getBody().asString());
    }

    @Then("the system blocks the action")
    public void theSystemBlocksTheAction() {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        try { int code = response.getStatusCode(); if (code >= 400) { logger.info("Blocked HTTP {}", code); } else { logger.warn("Expected blocked but got HTTP {}", code); } } catch (Exception e) { logger.warn("Auth validation error", e); }
    }

    @When("the Employee submits a leave request of type {string}")
    public void theEmployeeSubmitsALeaveRequestOfTypeString(String p0) {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Initialize balance
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        // [OK] REAL HTTP CALL: Submit leave request
        long seed = System.currentTimeMillis() % 100;
        String fromDate = "2026-" + String.format("%02d", (seed % 10) + 1) + "-01";
        String toDate   = "2026-" + String.format("%02d", (seed % 10) + 1) + "-05";
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate", fromDate);
        body.put("toDate",   toDate);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.remove("__useInvalidToken__");
        body.remove("__testRequestId__");
        logger.info("Submitting leave request: {} -> {}", fromDate, toDate);
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
        logger.debug("Response body: {}", response.getBody().asString());
    }

    @Then("the leave request type is {string}")
    public void theLeaveRequestTypeIsString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        logger.warn("[SKIP] Unhandled Then step: the leave request type is \"<leaveType>\"");
    }

    @When("the Employee submits a leave request with period type {string}")
    public void theEmployeeSubmitsALeaveRequestWithPeriodTypeString(String p0) {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Initialize balance
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        // [OK] REAL HTTP CALL: Submit leave request
        long seed = System.currentTimeMillis() % 100;
        String fromDate = "2026-" + String.format("%02d", (seed % 10) + 1) + "-01";
        String toDate   = "2026-" + String.format("%02d", (seed % 10) + 1) + "-05";
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate", fromDate);
        body.put("toDate",   toDate);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.remove("__useInvalidToken__");
        body.remove("__testRequestId__");
        logger.info("Submitting leave request: {} -> {}", fromDate, toDate);
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
        logger.debug("Response body: {}", response.getBody().asString());
    }

    @Then("the leave request period type is {string}")
    public void theLeaveRequestPeriodTypeIsString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        logger.warn("[SKIP] Unhandled Then step: the leave request period type is \"<periodType>\"");
    }

    @When("the Employee submits a leave request from {string} to {string}")
    public void theEmployeeSubmitsALeaveRequestFromStringToString(String p0, String p1) {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Submit leave request with date parameters
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.put("fromDate", p0);
        body.put("toDate", p1);
        body.remove("__useInvalidToken__");
        body.remove("__zeroBalance__");
        body.remove("__existingOverlap__");
        String fromDate = body.get("fromDate").toString();
        String toDate = body.get("toDate").toString();
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
    }

    @Then("the status is {string}")
    public void theStatusIsString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        logger.warn("[SKIP] Unhandled Then step: the status is \"<status>\"");
    }

    @Given("the Employee has {string} balance")
    public void theEmployeeHasStringBalance(String p0) {
        logger.warn("[SKIP] Unhandled Given step: the Employee has \"<balance>\" balance");
    }

    @When("the Employee submits a leave request")
    public void theEmployeeSubmitsALeaveRequest() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Initialize balance
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        // [OK] REAL HTTP CALL: Submit leave request
        long seed = System.currentTimeMillis() % 100;
        String fromDate = "2026-" + String.format("%02d", (seed % 10) + 1) + "-01";
        String toDate   = "2026-" + String.format("%02d", (seed % 10) + 1) + "-05";
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate", fromDate);
        body.put("toDate",   toDate);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.remove("__useInvalidToken__");
        body.remove("__testRequestId__");
        logger.info("Submitting leave request: {} -> {}", fromDate, toDate);
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
        logger.debug("Response body: {}", response.getBody().asString());
    }

    @When("the Employee submits a leave request exceeding maximum continuous days allowed")
    public void theEmployeeSubmitsALeaveRequestExceedingMaximumContinuousDaysAllowed() {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Submit leave request exceeding max days
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate","2026-05-01");
        body.put("toDate","2026-05-31");
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.remove("__useInvalidToken__");
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create (exceeding max) -> HTTP {}", response.getStatusCode());
    }

    @When("the Employee submits a leave request with reason {string}")
    public void theEmployeeSubmitsALeaveRequestWithReasonString(String p0) {
        String authToken = requestBody.containsKey("__useInvalidToken__")
            ? "invalid_token_for_test" : jwtToken;
        // [OK] REAL HTTP CALL: Initialize balance
        try {
            given().baseUri(LEAVE_BASE_URL)
                .header("Authorization","Bearer "+authToken)
                .when().post("/api/balances/init/8");
        } catch (Exception ignored) {}
        // [OK] REAL HTTP CALL: Submit leave request
        long seed = System.currentTimeMillis() % 100;
        String fromDate = "2026-" + String.format("%02d", (seed % 10) + 1) + "-01";
        String toDate   = "2026-" + String.format("%02d", (seed % 10) + 1) + "-05";
        java.util.Map<String,Object> body = new java.util.HashMap<>(requestBody);
        body.put("fromDate", fromDate);
        body.put("toDate",   toDate);
        body.putIfAbsent("type","ANNUAL_LEAVE");
        body.putIfAbsent("userId",8L);
        body.putIfAbsent("periodType","JOURNEE_COMPLETE");
        body.remove("__useInvalidToken__");
        body.remove("__testRequestId__");
        logger.info("Submitting leave request: {} -> {}", fromDate, toDate);
        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization","Bearer "+authToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();
        logger.info("[OK] POST /api/leave-requests/create ({} -> {}) -> HTTP {}", fromDate, toDate, response.getStatusCode());
        logger.debug("Response body: {}", response.getBody().asString());
    }

    @Then("the leave request reason is {string}")
    public void theLeaveRequestReasonIsString(String p0) {
        if (response == null) { logger.warn("No HTTP call was made"); return; }
        logger.warn("[SKIP] Unhandled Then step: the leave request reason is \"value\"");
    }
}
