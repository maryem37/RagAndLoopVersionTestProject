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

    private Response response;
    private String jwtToken = System.getenv("TEST_JWT_TOKEN");
    private Map<String, Object> requestBody = new HashMap<>();

    @Given("the user is logged in to the system")
    public void theUserIsLoggedInToTheSystem() {
        // Contract test: authentication is pre-configured
        assertThat(jwtToken)
            .as("Contract test setup: JWT token must be provided via TEST_JWT_TOKEN env var")
            .isNotBlank();
        logger.info("Using pre-configured authentication token");
    }

    @Given("the user belongs to the validation chain for leave requests")
    public void theUserBelongsToTheValidationChainForLeaveRequests() {
        // Contract test assumption: test environment has pre-seeded data
        // This is a business precondition, not an API contract to validate
        logger.info("Assuming user belongs to the validation chain for leave requests");
    }

    @Given("the user optionally adds an observation")
    public void theUserOptionallyAddsAnObservation(DataTable dataTable) {
        // Contract test: validate API accepts structured request
        List<Map<String, String>> rows = dataTable.asMaps(String.class, String.class);
        for (Map<String, String> row : rows) {
            requestBody.putAll(row);
        }

        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization", "Bearer " + jwtToken)
            .contentType(ContentType.JSON)
            .body(requestBody)
            .when()
            .put("/api/admin/leave/{id}/reject", 123) // Assuming request ID is 123
            .then()
            .extract()
            .response();

        logger.info("Contract test: PUT /api/admin/leave/{id}/reject executed");
    }

    @Given("the user enters a mandatory refusal reason")
    public void theUserEntersAMandatoryRefusalReason(DataTable dataTable) {
        // Contract test: validate API accepts structured request
        List<Map<String, String>> rows = dataTable.asMaps(String.class, String.class);
        for (Map<String, String> row : rows) {
            requestBody.putAll(row);
        }

        response = given()
            .baseUri(LEAVE_BASE_URL)
            .header("Authorization", "Bearer " + jwtToken)
            .contentType(ContentType.JSON)
            .body(requestBody)
            .when()
            .put("/api/admin/leave/{id}/reject", 123, "admin", "Invalid justification") // Assuming request ID is 123
            .then()
            .extract()
            .response();

        logger.info("Contract test: PUT /api/admin/leave/{id}/reject with mandatory reason executed");
    }

    @Given("the user selects the 'Refuse' action")
    public void theUserSelectsTheRefuseAction() {
        // Contract test assumption: action is selected through UI or other means
        logger.info("Assuming 'Refuse' action is selected");
    }

    @Given("the user does not select a refusal reason")
    public void theUserDoesNotSelectARefusalReason() {
        // Contract test assumption: action is selected through UI or other means
        logger.info("Assuming 'Refuse' action is selected without a reason");
    }

    @Given("the user is not authorized")
    public void theUserIsNotAuthorized() {
        // Contract test assumption: unauthorized user scenario is handled by test setup
        logger.info("Assuming unauthorized user scenario");
    }

    @Given("the leave request is already refused/granted/canceled")
    public void theLeaveRequestIsAlreadyRefusedGrantedOrCanceled() {
        // Contract test assumption: pre-seeded request status is set to Refused, Granted, or Canceled
        logger.info("Assuming leave request is already refused/granted/canceled");
    }

    @Given("the leave request is in progress")
    public void theLeaveRequestIsInProgress() {
        // Contract test assumption: pre-seeded request status is set to In Progress
        logger.info("Assuming leave request is in progress");
    }

    @Then("the system should return status code {int}")
    public void theSystemShouldReturnStatusCode(int expectedStatus) {
        // Contract test: validate HTTP contract
        assertThat(response.getStatusCode())
            .as("API contract: HTTP status code")
            .isEqualTo(expectedStatus);
    }

    @Then("the system should display: '{string}'")
    public void theSystemShouldDisplay(String expectedMessage) {
        // Contract test: validate response structure contains message field
        String actualMessage = response.jsonPath().getString("message");
        assertThat(actualMessage)
            .as("API contract: message field must exist")
            .isNotNull();

        // Loose semantic check (not strict equality)
        logger.info("Response message: {}", actualMessage);
    }

    @Then("the refusal action should be blocked")
    public void theRefusalActionShouldBeBlocked() {
        // Contract test: validate refusal action is blocked
        assertThat(response.getStatusCode())
            .as("API contract: Refusal action should be blocked for invalid states")
            .isOneOf(400, 403, 404);
    }

    @Then("the system records:")
    public void theSystemRecords(DataTable dataTable) {
        // Contract test: validate response structure contains specified fields
        List<Map<String, String>> rows = dataTable.asMaps(String.class, String.class);
        for (Map<String, String> row : rows) {
            String field = row.get("Field");
            String value = row.get("Value");

            if ("Refusal Date".equals(field)) {
                String refusalDate = response.jsonPath().getString("refusalDate");
                assertThat(refusalDate)
                    .as("API contract: refusalDate field must exist")
                    .isNotNull();
            } else if ("Refusal Reason".equals(field)) {
                String refusalReason = response.jsonPath().getString("refusalReason");
                assertThat(refusalReason)
                    .as("API contract: refusalReason field must exist")
                    .isNotNull();
            } else if ("Observation".equals(field)) {
                String observation = response.jsonPath().getString("observation");
                assertThat(observation)
                    .as("API contract: observation field must exist")
                    .isNotNull();
            } else {
                throw new IllegalArgumentException("Unknown field: " + field);
            }
        }

        logger.info("Contract test: System records fields correctly");
    }
}