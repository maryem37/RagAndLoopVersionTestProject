package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.http.Header;
import static io.restassured.RestAssured.*;

public class TestContext {
    private static final ThreadLocal<Object> CONTEXT = new ThreadLocal<>();

    public static void set(Object value) {
        CONTEXT.set(value);
    }

    public static Object get() {
        return CONTEXT.get();
    }

    public static void remove() {
        CONTEXT.remove();
    }
}