package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.response.Response;
import static io.restassured.RestAssured.*;

public class TestDataBuilder {
    private static final ObjectMapper objectMapper = new ObjectMapper();

    public static String asJsonString(Object obj) throws Exception {
        return objectMapper.writeValueAsString(obj);
    }
}