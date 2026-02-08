package com.example.testutils;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import static io.restassured.RestAssured.*;
import java.util.concurrent.ThreadLocal;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.http.Header;
import static io.restassured.RestAssured.*;

public class AuthHelper {
    public static void authenticate(String accessToken) {
        header("Authorization", "Bearer " + accessToken);
    }
}