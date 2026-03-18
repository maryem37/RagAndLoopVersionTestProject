package com.example.leave;

import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = {"classpath:features/leave-request-service_02_employee-leave-request-management_20260318_162016.feature"},
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
