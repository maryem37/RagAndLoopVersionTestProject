package com.userservice.steps;

import io.cucumber.java.en.*;
import org.assertj.core.util.Lists;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import io.cucumber.datatable.DataTable;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import static io.restassured.RestAssured.*;
import static org.assertj.core.api.Assertions.*;


public class UserServiceSteps {
    private Response response;
    private Logger log = LoggerFactory.getLogger(UserServiceSteps.class);

    @Given("I have an authenticated API client")
    public void givenAuthenticatedApiClient() {
        // Assuming authentication is handled outside of this class
    }

    @When("I send a GET request to \\/leave-requests")
    public void whenSendGetRequestToLeaveRequests() {
        response = get("/leave-requests");
    }

    @Then("the status code should be 200")
    public void thenStatusCodeShouldBe200() {
        assertThat(response.getStatusCode()).isEqualTo(200);
    }

    @Then("the response body should contain a list of leave requests")
    public void thenResponseBodyShouldContainAListOfLeaveRequests() {
        List<Object> leaveRequests = response.asList(Object.class);
        assertThat(leaveRequests).isNotEmpty();
        // Add more assertions based on the actual structure of the leave request object
    }

    @When("I send a POST request to \\/leave-requests with the LeaveRequestCreate object as JSON body")
    public void whenSendPostRequestToLeaveRequestsWithLeaveRequestCreateObjectAsJsonBody(DataTable dataTable) {
        String json = new JSONObject(dataTable.asMap()).toString();
        response = given()
                .contentType(ContentType.JSON)
                .body(json)
                .when()
                .post("/leave-requests");
    }

    @Then("the status code should be 201")
    public void thenStatusCodeShouldBe201() {
        assertThat(response.getStatusCode()).isEqualTo(201);
    }

    @Then("the response body should contain the created leave request")
    public void thenResponseBodyShouldContainTheCreatedLeaveRequest() {
        // Add more assertions based on the actual structure of the leave request object
    }

    @When("I send a POST request to \\/leave-requests with an invalid LeaveRequestCreate object as JSON body")
    public void whenSendPostRequestToLeaveRequestsWithInvalidLeaveRequestCreateObjectAsJsonBody(DataTable dataTable) {
        String json = new JSONObject(dataTable.asMap()).toString();
        response = given()
                .contentType(ContentType.JSON)
                .body(json)
                .when()
                .post("/leave-requests");
    }

    @Then("the status code should be 400")
    public void thenStatusCodeShouldBe400() {
        assertThat(response.getStatusCode()).isEqualTo(400);
    }

    @Then("the response body should contain error details for the invalid data")
    public void thenResponseBodyShouldContainErrorDetailsForTheInvalidData() {
        // Add more assertions based on the actual structure of the error response
    }

    public String toJson(Object object) {
        return new JSONObject(object).toString();
    }
}
 I have also created a simple `LeaveRequestCreate` POJO:

package com.userservice;

public class LeaveRequestCreate {
    private String title;
    private String description;
    // Add more fields as needed

    public LeaveRequestCreate(String title, String description) {
        this.title = title;
        this.description = description;
    }

    // Getters and setters
}