package com.example.userservice.test;

import io.cucumber.junit.CucumberOptions;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.runner.ArgumentTypesCucumberOptions;
import net.serenitybdd.cucumber.CucumberWithSerenity;
import org.junit.runner.RunWith;

@RunWith(CucumberWithSerenity.class)
@CucumberOptions(
        features = {"C:\\Bureau\\Bureau\\project_test\\features\\leave-request-management_20260201_200336.feature"},
        glue = {"com.example.userservice.stepdefinitions"},
        plugin = {
                "pretty",
                "html:target/cucumber-reports",
                "json:target/cucumber.json",
                "junit:target/cucumber-results.xml"
        },
        monochrome = true,
        strict = true
)
public class UserServiceTestRunner {
}
In this example, the package is `com.example.userservice.test`. The feature file location is specified in the `features` array. The step definitions should be placed in the `com.example.userservice.stepdefinitions` package.

Make sure to replace the package name and step definition package with your project's structure. Also, ensure that you have added the necessary dependencies for Cucumber and JUnit 5 in your build configuration (Maven or Gradle).