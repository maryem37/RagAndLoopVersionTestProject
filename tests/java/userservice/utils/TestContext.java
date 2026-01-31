package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.response.Response;
import static io.restassured.RestAssured.*;

public class TestContext {
    private static final ThreadLocal<String> AUTH_TOKEN = new ThreadLocal<>();

    public static void setAuthToken(String authToken) {
        AUTH_TOKEN.set(authToken);
    }

    public static String getAuthToken() {
        return AUTH_TOKEN.get();
    }
}