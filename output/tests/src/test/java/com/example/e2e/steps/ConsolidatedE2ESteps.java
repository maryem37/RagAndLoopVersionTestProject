package com.example.e2e.steps;

import io.cucumber.java.Before;
import io.cucumber.java.en.*;
import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ConsolidatedE2ESteps {

    private static final Logger logger = LoggerFactory.getLogger(ConsolidatedE2ESteps.class);
    private static final String BASE_URL = "http://127.0.0.1:9000";
    private String   jwtToken;
    private Response response;
    private Map<String, Object> requestBody;

    @Before
    public void setUp() {
        requestBody = new HashMap<>();
        response = null;

        // Prefer explicit token, otherwise auto-login to get one.
        jwtToken = System.getenv("TEST_JWT_TOKEN");
        if (jwtToken == null || jwtToken.isBlank()) {
            String email    = System.getenv("TEST_USER_EMAIL");
            String password = System.getenv("TEST_USER_PASSWORD");
            if (email == null || email.isBlank()) email = "admin@test.com";
            if (password == null || password.isBlank()) password = "admin123";

            java.util.Map<String,Object> loginBody = new java.util.HashMap<>();
            loginBody.put("email", email);
            loginBody.put("password", password);

            io.restassured.response.Response loginResp = given()
                .baseUri("http://127.0.0.1:9000")
                .contentType(ContentType.JSON)
                .body(loginBody)
                .log().ifValidationFails()
                .when().post("/api/auth/login")
                .then().extract().response();

            int code = loginResp.getStatusCode();
            logger.info("[setup] POST /api/auth/login -> HTTP {}", code);
            if (code < 200 || code >= 300) {
                throw new AssertionError("Auto-login failed HTTP " + code + ": " + loginResp.asString());
            }

            try {
                jwtToken = loginResp.jsonPath().getString("jwt");
                if (jwtToken == null || jwtToken.isBlank()) jwtToken = loginResp.jsonPath().getString("token");
            } catch (Exception ignored) {}

            if (jwtToken == null || jwtToken.isBlank()) {
                throw new AssertionError("Auto-login succeeded but no JWT in response: " + loginResp.asString());
            }
        }
    }


}
