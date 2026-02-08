package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.http.Header;
import static io.restassured.RestAssured.*;

public class TestDataBuilder {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    public static String asJsonString(Object obj) throws Exception {
        return OBJECT_MAPPER.writeValueAsString(obj);
    }
}