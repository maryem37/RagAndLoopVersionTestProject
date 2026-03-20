package com.example.leave;

import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "classpath:features",
    glue = "com.example.leave.steps",
    plugin = {
        "pretty",
        "html:target/cucumber-reports/leave/cucumber.html",
        "json:target/cucumber-reports/leave/cucumber.json"
    },
    monochrome = true
)
public class LeaveTestRunner {
}
