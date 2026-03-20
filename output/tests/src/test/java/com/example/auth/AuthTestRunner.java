package com.example.auth;

import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "classpath:features",
    glue = "com.example.auth.steps",
    plugin = {
        "pretty",
        "html:target/cucumber-reports/auth/cucumber.html",
        "json:target/cucumber-reports/auth/cucumber.json"
    },
    monochrome = true
)
public class AuthTestRunner {
}
