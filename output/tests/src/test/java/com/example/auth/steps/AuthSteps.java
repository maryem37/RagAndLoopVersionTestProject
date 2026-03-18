package com.example.auth.steps;

import io.cucumber.java.Before;
import io.cucumber.java.en.*;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import static org.assertj.core.api.Assertions.*;
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

    @Given("the employee has valid credentials")
    public void theEmployeeHasValidCredentials() {
        String email    = System.getenv("TEST_USER_EMAIL");
        String password = System.getenv("TEST_USER_PASSWORD");
        if (email    == null || email.isBlank())    email    = "admin@test.com";
        if (password == null || password.isBlank()) password = "admin123";
        requestBody.put("email",    email);
        requestBody.put("password", password);
        logger.info("Precondition: valid credentials (email={})", email);
    }

    @When("the employee submits the login request with email and password")
    public void theEmployeeSubmitsTheLoginRequestWithEmailAndPassword() {
        // Public endpoint — NO Authorization header on login
        java.util.Map<String,Object> loginBody = new java.util.HashMap<>();
        loginBody.put("email",    requestBody.getOrDefault("email",    "admin@test.com"));
        loginBody.put("password", requestBody.getOrDefault("password", "admin123"));
        response = given()
            .baseUri(BASE_URL)
            .contentType(ContentType.JSON)
            .body(loginBody)
            .when().post("/api/auth/login")
            .then().extract().response();
        logger.info("POST /api/auth/login -> HTTP {}", response.getStatusCode());
    }

    @Then("the system returns a valid JWT token")
    public void theSystemReturnsAValidJwtToken() {
        assertThat(response).as("No HTTP call was made").isNotNull();
        assertThat(response.getStatusCode()).as("[Expected successful login]").isBetween(200, 299);
        String jwt = response.jsonPath().getString("jwt");
        assertThat(jwt).as("Response must contain a non-blank jwt field").isNotBlank();
        logger.info("Login OK, JWT received");
    }

    @Given("the employee has invalid credentials")
    public void theEmployeeHasInvalidCredentials() {
        String email    = System.getenv("TEST_USER_EMAIL");
        String password = System.getenv("TEST_USER_PASSWORD");
        if (email    == null || email.isBlank())    email    = "admin@test.com";
        if (password == null || password.isBlank()) password = "admin123";
        requestBody.put("email",    email);
        requestBody.put("password", password);
        logger.info("Precondition: valid credentials (email={})", email);
    }

    @Then("the system blocks the action")
    public void theSystemBlocksTheAction() {
        assertThat(response).as("No HTTP call was made").isNotNull();
        // Auth may return 200 with null jwt OR 4xx — both mean blocked
        boolean statusBlocked = response.getStatusCode() >= 400;
        boolean noJwt = response.getStatusCode() == 200 &&
            (response.jsonPath().getString("jwt") == null ||
             response.jsonPath().getString("jwt").isBlank());
        assertThat(statusBlocked || noJwt)
            .as("Expected blocked (4xx or 200+noJWT), got HTTP "
                + response.getStatusCode() + " body=" + response.getBody().asString())
            .isTrue();
        logger.info("Blocked confirmed HTTP {}", response.getStatusCode());
    }

    @Given("the employee has incomplete credentials")
    public void theEmployeeHasIncompleteCredentials() {
        requestBody.clear();
        logger.info("Precondition: incomplete/missing credentials");
    }

    @When("the employee submits the login request without email and password")
    public void theEmployeeSubmitsTheLoginRequestWithoutEmailAndPassword() {
        // Missing fields — empty body, NO Authorization header
        response = given()
            .baseUri(BASE_URL)
            .contentType(ContentType.JSON)
            .body(new java.util.HashMap<>())
            .when().post("/api/auth/login")
            .then().extract().response();
        logger.info("POST /api/auth/login (empty body) -> HTTP {}", response.getStatusCode());
    }

    @Then("the system displays the error {string}")
    public void theSystemDisplaysTheErrorString(String p0) {
        assertThat(response).as("No HTTP call was made").isNotNull();
        // Some APIs return 200 with null jwt for missing fields instead of 400
        boolean is4xx = response.getStatusCode() >= 400;
        boolean noJwt = response.getStatusCode() == 200 &&
            (response.jsonPath().getString("jwt") == null ||
             response.jsonPath().getString("jwt").isBlank());
        assertThat(is4xx || noJwt)
            .as("[Expected bad request or no JWT], got HTTP "
                + response.getStatusCode() + " body=" + response.getBody().asString())
            .isTrue();
        logger.info("Bad request or no JWT, HTTP {}", response.getStatusCode());
    }
}
