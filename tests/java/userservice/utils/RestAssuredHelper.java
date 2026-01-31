package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.response.Response;
import static io.restassured.RestAssured.*;

public class RestAssuredHelper {
    public static void given() {
        baseURI = "http://localhost:8080"; // Replace with your API base URL
    }

    public static SpecifiedRequestSpecification when() {
        return given();
    }

    public static Response then() {
        return get();
    }

    public static Response post(Object requestBody) {
        return given().contentType(ContentType.JSON).body(requestBody).when().post("/leave-requests");
    }
}