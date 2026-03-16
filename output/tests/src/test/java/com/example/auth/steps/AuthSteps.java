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

    @Given("the user is authenticated as an administrator")
    public void theUserIsAuthenticatedAsAdministrator() {
        assertThat(jwtToken).isNotBlank();
        logger.info("Authenticated as administrator");
    }

    @Given("the user is authenticated as a team lead")
    public void theUserIsAuthenticatedAsTeamLead() {
        assertThat(jwtToken).isNotBlank();
        logger.info("Authenticated as team lead");
    }

    @Given("the user is authenticated as an employee")
    public void theUserIsAuthenticatedAsEmployee() {
        assertThat(jwtToken).isNotBlank();
        logger.info("Authenticated as employee");
    }

}
