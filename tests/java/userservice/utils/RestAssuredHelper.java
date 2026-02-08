package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.http.Header;
import static io.restassured.RestAssured.*;

public class RestAssuredHelper {
    public static void given() {
        baseURI = "http://localhost:8080"; // Replace with your API server's base URL
        port = 8080; // Replace with your API server's port number
        basePath = "/api"; // Replace with your API server's base path
    }

    public static SpecifiedRequestBuilder get(String endpoint) {
        return given().when();
    }

    public static Response getResponse(SpecifiedRequestBuilder requestBuilder) {
        return requestBuilder.get();
    }

    public static SpecifiedRequestBuilder post(String endpoint, Object body) {
        return given()
                .contentType(ContentType.JSON)
                .body(body);
    }

    public static Response postResponse(SpecifiedRequestBuilder requestBuilder) {
        return requestBuilder.post();
    }
}