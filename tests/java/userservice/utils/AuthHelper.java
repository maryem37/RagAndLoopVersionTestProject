package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.response.Response;
import static io.restassured.RestAssured.*;

public class AuthHelper {
    public static Response authenticate(String username, String password) {
        return given()
                .contentType(ContentType.JSON)
                .body("{\"username\": \"" + username + "\", \"password\": \"" + password + "\"}")
                .when()
                .post("/auth");
    }
}