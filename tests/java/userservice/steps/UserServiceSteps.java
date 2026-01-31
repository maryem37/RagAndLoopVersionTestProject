package com.userservice.steps;

import io.cucumber.java.en.*;
import org.assertj.core.api.Assertions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import io.restassured.http.ContentType;
import io.restassured.response.Response;
import static io.restassured.RestAssured.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

public class UserServiceSteps {
    private Response response;
    private static final Logger LOGGER = LoggerFactory.getLogger(UserServiceSteps.class);
    private ObjectMapper objectMapper = new ObjectMapper();

    @Given("I have an authenticated API client")
    public void given_i_have_an_authenticated_api_client() {
        // Authenticate the API client if necessary (not provided in the scenario)
    }

    @When("I send a GET request to \\/leave-requests")
    public void when_i_send_a_get_request_to_leave_requests() {
        response = given().when().get("/leave-requests");
    }

    @Then("the status code should be 200")
    public void then_the_status_code_should_be_200() {
        Assertions.assertThat(response.getStatusCode()).isEqualTo(200);
    }

    @Then("the response body should contain a list of leave requests")
    public void then_the_response_body_should_contain_a_list_of_leave_requests() {
        JsonNode jsonResponse = objectMapper.convertValue(response.getBody(), JsonNode.class);
        Assertions.assertThat(jsonResponse.isArray()).isTrue();
    }

    @Given("I have a valid LeaveRequestCreate object")
    public void given_i_have_a_valid_leave_request_create_object() {
        // Create a valid LeaveRequestCreate object (not provided in the scenario)
    }

    @When("I send a POST request to \\/leave-requests with the LeaveRequestCreate object as JSON body")
    public void when_i_send_a_post_request_to_leave_requests_with_the_leave_request_create_object_as_json_body() {
        given().contentType(ContentType.JSON).body(/* Your LeaveRequestCreate object */).when().post("/leave-requests");
    }

    @Then("the status code should be 201")
    public void then_the_status_code_should_be_201() {
        Assertions.assertThat(response.getStatusCode()).isEqualTo(201);
    }

    @Then("the response body should contain the created leave request")
    public void then_the_response_body_should_contain_the_created_leave_request() {
        JsonNode jsonResponse = objectMapper.convertValue(response.getBody(), JsonNode.class);
        // Assert that the response contains the expected fields for a created leave request (not provided in the scenario)
    }

    @Given("I have an invalid LeaveRequestCreate object")
    public void given_i_have_an_invalid_leave_request_create_object() {
        // Create an invalid LeaveRequestCreate object (not provided in the scenario)
    }

    @When("I send a POST request to \\/leave-requests with the invalid LeaveRequestCreate object as JSON body")
    public void when_i_send_a_post_request_to_leave_requests_with_the_invalid_leave_request_create_object_as_json_body() {
        given().contentType(ContentType.JSON).body(/* Your invalid LeaveRequestCreate object */).when().post("/leave-requests");
    }

    @Then("the status code should be 400")
    public void then_the_status_code_should_be_400() {
        Assertions.assertThat(response.getStatusCode()).isEqualTo(400);
    }

    @Then("the response body should contain error details for the invalid data")
    public void then_the_response_body_should_contain_error_details_for_the_invalid_data() {
        JsonNode jsonResponse = objectMapper.convertValue(response.getBody(), JsonNode.class);
        // Assert that the response contains error details for invalid data (not provided in the scenario)
    }
}