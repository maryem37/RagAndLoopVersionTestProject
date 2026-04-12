import io.restassured.response.Response;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.*;

/**
 * LEAVE SERVICE HTTP CALLS
 * Add these to ConsolidatedE2ESteps.java setUp() or use them in step definitions
 */
public class LeaveServiceCalls {

    public static Response createLeaveRequest(String jwtToken, Map<String, Object> requestBody) {
        return given()
            .baseUri("http://127.0.0.1:9001")
            .contentType(ContentType.JSON)
            .header("Authorization", "Bearer " + jwtToken)
            .body(requestBody)
            .log().ifValidationFails()
            .when().post("/api/leave-requests/create")
            .then().extract().response();
    }

    public static Response getLeaveRequest(String jwtToken, int requestId) {
        return given()
            .baseUri("http://127.0.0.1:9001")
            .contentType(ContentType.JSON)
            .header("Authorization", "Bearer " + jwtToken)
            .log().ifValidationFails()
            .when().get("/api/leave-requests/" + requestId)
            .then().extract().response();
    }

    public static Response approveLeaveRequest(String jwtToken, int requestId) {
        return given()
            .baseUri("http://127.0.0.1:9001")
            .contentType(ContentType.JSON)
            .header("Authorization", "Bearer " + jwtToken)
            .log().ifValidationFails()
            .when().put("/api/leave-requests/" + requestId + "/approve")
            .then().extract().response();
    }

    public static Response rejectLeaveRequest(String jwtToken, int requestId) {
        return given()
            .baseUri("http://127.0.0.1:9001")
            .contentType(ContentType.JSON)
            .header("Authorization", "Bearer " + jwtToken)
            .log().ifValidationFails()
            .when().put("/api/leave-requests/" + requestId + "/reject")
            .then().extract().response();
    }

    public static Response listLeaveRequests(String jwtToken) {
        return given()
            .baseUri("http://127.0.0.1:9001")
            .contentType(ContentType.JSON)
            .header("Authorization", "Bearer " + jwtToken)
            .log().ifValidationFails()
            .when().get("/api/leave-requests")
            .then().extract().response();
    }
}
