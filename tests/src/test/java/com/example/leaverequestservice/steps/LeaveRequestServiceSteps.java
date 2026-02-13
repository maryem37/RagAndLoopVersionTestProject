package com.example.leaverequestservice.steps;

import io.cucumber.java.en.*;
import io.cucumber.datatable.DataTable;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import static org.assertj.core.api.Assertions.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LeaveRequestServiceSteps {

    private static final Logger logger = LoggerFactory.getLogger(LeaveRequestServiceSteps.class);
    private static final String AUTH_BASE_URL = "http://localhost:9000";
    private static final String LEAVE_BASE_URL = "http://localhost:9001";
    private static final String TEST_JWT_TOKEN = System.getenv("TEST_JWT_TOKEN");

    private Response response;
    private Map<String, Object> requestBody = new HashMap<>();

    @Given("I am logged into the system")
    public void iAmLoggedInToTheSystem() {
        // Contract test: assume authentication is pre-configured
        assertThat(TEST_JWT_TOKEN)
                .as("Contract test setup: JWT token must be provided via TEST_JWT_TOKEN env var")
                .isNotBlank();
        logger.info("Using pre-configured authentication token");
    }

    @Given("I have submitted a leave request")
    public void iHaveSubmittedALeaveRequest() {
        // Contract test: assume data is pre-configured
        logger.info("Assuming leave request is already submitted in test data");
    }

    @When("I provide an observation '(.*)'")
    public void iProvideAnObservation(String observation) {
        // Contract test: validate API accepts structured request
        requestBody.put("observation", observation);

        response = given()
                .baseUri(LEAVE_BASE_URL)
                .header("Authorization", "Bearer " + TEST_JWT_TOKEN)
                .contentType(ContentType.JSON)
                .body(requestBody)
                .put("/api/employer/leave/" + leaveRequestId + "/cancel?observation=" + observation)
                .then()
                .extract()
                .response();

        logger.info("Contract test: PUT /api/employer/leave/{}/cancel executed with observation", leaveRequestId);
    }

    @When("I do not provide an observation")
    public void iDoNotProvideAnObservation() {
        // Contract test: validate API accepts structured request
        response = given()
                .baseUri(LEAVE_BASE_URL)
                .header("Authorization", "Bearer " + TEST_JWT_TOKEN)
                .contentType(ContentType.JSON)
                .body(requestBody)
                .put("/api/employer/leave/" + leaveRequestId + "/cancel")
                .then()
                .extract()
                .response();

        logger.info("Contract test: PUT /api/employer/leave/{}/cancel executed without observation", leaveRequestId);
    }

    @When("I attempt to cancel my leave request that is currently '(.*)'")
    public void iAttemptToCancelMyLeaveRequestThatIsCurrently(String status) {
        // Contract test: validate API accepts structured request
        response = given()
                .baseUri(LEAVE_BASE_URL)
                .header("Authorization", "Bearer " + TEST_JWT_TOKEN)
                .contentType(ContentType.JSON)
                .body(requestBody)
                .put("/api/employer/leave/" + leaveRequestId + "/cancel")
                .then()
                .extract()
                .response();

        logger.info("Contract test: PUT /api/employer/leave/{}/cancel executed for status: {}", leaveRequestId, status);
    }

    @Then("the system should return status code (.*)")
    public void theSystemShouldReturnStatusCode(int expectedStatus) {
        // Contract test: validate HTTP contract
        assertThat(response.getStatusCode())
                .as("API contract: HTTP status code")
                .isEqualTo(expectedStatus);
    }

    @Then("an error message is displayed: '(.*)'")
    public void anErrorMessageIsDisplayed(String errorMessage) {
        // Contract test: validate response structure contains error message field
        String actualMessage = response.jsonPath().getString("message");
        assertThat(actualMessage)
                .as("API contract: error message field must exist")
                .isNotNull()
                .contains(errorMessage);
    }

    @Then("the request status changes to '(.*)'")
    public void theRequestStatusChangesTo(String expectedStatus) {
        // Contract test: validate response structure
        assertThat(response).isNotNull();
        assertThat(response.getStatusCode()).isBetween(200, 299);

        // Validate field exists (contract requirement)
        String actualStatus = response.jsonPath().getString("status");
        assertThat(actualStatus)
                .as("API contract: status field must exist in response")
                .isNotNull()
                .isEqualTo(expectedStatus);

        logger.info("Leave request status from API: {}", actualStatus);
    }

    @Then("the cancellation date is recorded")
    public void theCancellationDateIsRecorded() {
        // Contract test: validate response structure contains cancellation date field
        String cancellationDate = response.jsonPath().getString("cancellationDate");
        assertThat(cancellationDate)
                .as("API contract: cancellationDate field must exist")
                .isNotNull();
    }

    @Then("the provided observation is saved")
    public void theProvidedObservationIsSaved() {
        // Contract test: validate response structure contains observation field
        String observation = response.jsonPath().getString("observation");
        assertThat(observation)
                .as("API contract: observation field must exist")
                .isNotNull()
                .isEqualTo(requestBody.get("observation"));
    }

    @Then("no observation is saved")
    public void noObservationIsSaved() {
        // Contract test: validate response structure does not contain observation field
        String observation = response.jsonPath().getString("observation");
        assertThat(observation)
                .as("API contract: observation field should not exist")
                .isNull();
    }

    @Before("@CancelLeaveRequest")
    public void setUpLeaveRequestId() {
        // Mock or stub to get leave request ID
        leaveRequestId = 123; // Replace with actual method to fetch leave request ID
    }

    private Integer leaveRequestId;
}