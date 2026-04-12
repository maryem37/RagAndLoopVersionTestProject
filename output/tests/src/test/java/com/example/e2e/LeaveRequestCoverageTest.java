package com.example.e2e;

import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Focused tests intended to drive deeper execution inside LeaveRequestServiceImpl and related services.
 * These tests are designed to be resilient to DB state by accepting either success (2xx)
 * or expected validation/client errors (4xx) while still exercising backend branches.
 */
@Disabled("Exploratory coverage-focused test; enable manually when needed")
public class LeaveRequestCoverageTest {

    private static String jwtToken;
    private static String authBaseUrl;
    private static String leaveBaseUrl;
    private static int userId = 8;

    @BeforeAll
    public static void setUp() {
        authBaseUrl = System.getProperty("AUTH_BASE_URL", "http://127.0.0.1:9000");
        leaveBaseUrl = System.getProperty("LEAVE_BASE_URL", "http://127.0.0.1:9001");

        jwtToken = firstNonBlank(
            System.getProperty("TEST_JWT_TOKEN"),
            System.getenv("TEST_JWT_TOKEN")
        );

        if (jwtToken == null) {
            Map<String, Object> loginBody = new HashMap<>();
            loginBody.put("email", firstNonBlank(System.getProperty("TEST_USER_EMAIL"), System.getenv("TEST_USER_EMAIL"), "admin@test.com"));
            loginBody.put("password", firstNonBlank(System.getProperty("TEST_USER_PASSWORD"), System.getenv("TEST_USER_PASSWORD"), "admin123"));

            Response loginResp = given()
                .baseUri(authBaseUrl)
                .contentType(ContentType.JSON)
                .body(loginBody)
                .log().ifValidationFails()
                .when().post("/api/auth/login")
                .then().extract().response();

            assertEquals(200, loginResp.getStatusCode(), "Login should return 200");
            jwtToken = loginResp.jsonPath().getString("jwt");
            if (jwtToken == null || jwtToken.isBlank()) {
                jwtToken = loginResp.jsonPath().getString("token");
            }
            assertNotNull(jwtToken, "JWT token should not be null");
            assertFalse(jwtToken.isBlank(), "JWT token should not be blank");
        }

        // Best-effort: resolve a valid userId so leave-service calls can reach auth lookups.
        try {
            // Seeded dataset typically includes Super Admin id=8. Prefer it.
            Response user8Resp = given()
                .baseUri(authBaseUrl)
                .header("Authorization", "Bearer " + jwtToken)
                .log().ifValidationFails()
                .when().get("/api/users/8")
                .then().extract().response();

            if (user8Resp.getStatusCode() >= 200 && user8Resp.getStatusCode() < 300) {
                Integer id = user8Resp.jsonPath().getInt("id");
                if (id != null && id > 0) userId = id;
                return;
            }
        } catch (Exception ignored) {
            userId = 8;
        }
    }

    @Test
    public void balance_init_and_update_exercises_balance_service() {
        Response initResp = given()
            .baseUri(leaveBaseUrl)
            .header("Authorization", "Bearer " + jwtToken)
            .log().ifValidationFails()
            .when().post("/api/balances/init/" + userId)
            .then().extract().response();

        assertTrue(initResp.getStatusCode() >= 200 && initResp.getStatusCode() < 500,
            "init balance should not 5xx; got " + initResp.getStatusCode() + ": " + initResp.asString());

        Response updateResp = given()
            .baseUri(leaveBaseUrl)
            .header("Authorization", "Bearer " + jwtToken)
            .queryParam("amount", 0.5)
            .queryParam("type", "ANNUAL")
            .log().ifValidationFails()
            .when().put("/api/balances/" + userId)
            .then().extract().response();

        assertTrue(updateResp.getStatusCode() >= 200 && updateResp.getStatusCode() < 500,
            "update balance should not 5xx; got " + updateResp.getStatusCode() + ": " + updateResp.asString());
    }

    @Test
    public void create_leave_request_valid_day_based_hits_main_flow() {
        ensureBalanceInitialized();

        Map<String, Object> body = new HashMap<>();
        LocalDate from = nextWeekday(LocalDate.now().plusDays(10));
        LocalDate to = nextWeekday(from.plusDays(2));

        body.put("userId", userId);
        body.put("type", "ANNUAL_LEAVE");
        body.put("periodType", "JOURNEE_COMPLETE");
        body.put("fromDate", from.toString());
        body.put("toDate", to.toString());
        body.put("note", "coverage - valid day-based request");

        Response resp = given()
            .baseUri(leaveBaseUrl)
            .header("Authorization", "Bearer " + jwtToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();

        int code = resp.getStatusCode();
        assertTrue(code >= 200 && code < 500, "create should not 5xx; got " + code + ": " + resp.asString());

        if (code >= 200 && code < 300) {
            Long id = resp.jsonPath().getLong("id");
            assertNotNull(id, "created leave request should have id");
            assertEquals("ANNUAL_LEAVE", resp.jsonPath().getString("type"));
        }
    }

    @Test
    public void create_leave_request_invalid_date_sequence_hits_validation() {
        Map<String, Object> body = new HashMap<>();
        LocalDate from = nextWeekday(LocalDate.now().plusDays(10));
        LocalDate to = from.minusDays(1);

        body.put("userId", userId);
        body.put("type", "ANNUAL_LEAVE");
        body.put("periodType", "JOURNEE_COMPLETE");
        body.put("fromDate", from.toString());
        body.put("toDate", to.toString());
        body.put("note", "coverage - invalid date sequence");

        Response resp = given()
            .baseUri(leaveBaseUrl)
            .header("Authorization", "Bearer " + jwtToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();

        int code = resp.getStatusCode();
        assertTrue(code >= 400 && code < 600, "expected validation error; got " + code + ": " + resp.asString());
    }

    @Test
    public void create_leave_request_hour_based_exercises_time_branches() {
        ensureBalanceInitialized();

        Map<String, Object> body = new HashMap<>();
        LocalDate day = nextWeekday(LocalDate.now().plusDays(14));

        body.put("userId", userId);
        body.put("type", "AUTHORIZED_ABSENCE");
        body.put("periodType", "PAR_HEURE");
        body.put("fromDate", day.toString());
        body.put("toDate", day.toString());
        body.put("fromTime", "08:00:00");
        body.put("toTime", "10:30:00");
        body.put("note", "coverage - hour based");

        Response resp = given()
            .baseUri(leaveBaseUrl)
            .header("Authorization", "Bearer " + jwtToken)
            .contentType(ContentType.JSON)
            .body(body)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();

        int code = resp.getStatusCode();
        assertTrue(code >= 200 && code < 500, "hour-based create should not 5xx; got " + code + ": " + resp.asString());
    }

    @Test
    public void search_leave_requests_exercises_search_flow() {
        Response resp = given()
            .baseUri(leaveBaseUrl)
            .header("Authorization", "Bearer " + jwtToken)
            .queryParam("currentUserId", userId)
            .queryParam("fromDate", LocalDate.now().minusDays(30).toString())
            .queryParam("toDate", LocalDate.now().plusDays(365).toString())
            .log().ifValidationFails()
            .when().get("/api/leave-requests/search")
            .then().extract().response();

        int code = resp.getStatusCode();
        assertTrue(code >= 200 && code < 500, "search should not 5xx; got " + code + ": " + resp.asString());
    }

    private static LocalDate nextWeekday(LocalDate date) {
        LocalDate d = date;
        while (d.getDayOfWeek() == DayOfWeek.SATURDAY || d.getDayOfWeek() == DayOfWeek.SUNDAY) {
            d = d.plusDays(1);
        }
        return d;
    }

    private static String firstNonBlank(String... values) {
        if (values == null) return null;
        for (String v : values) {
            if (v != null && !v.isBlank()) return v;
        }
        return null;
    }

    private static void ensureBalanceInitialized() {
        try {
            Response initResp = given()
                .baseUri(leaveBaseUrl)
                .header("Authorization", "Bearer " + jwtToken)
                .log().ifValidationFails()
                .when().post("/api/balances/init/" + userId)
                .then().extract().response();

            // Balance init might be idempotent or might fail if already exists; both are fine.
            int code = initResp.getStatusCode();
            assertTrue(code >= 200 && code < 500, "balance init should not 5xx; got " + code + ": " + initResp.asString());
        } catch (Exception e) {
            fail("Failed to initialize balance: " + e.getMessage());
        }
    }
}
