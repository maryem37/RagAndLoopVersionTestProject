package com.example.userservice.test;

import io.cucumber.junit.CucumberOptions;
import io.cucumber.junit.Cucumber;
import io.cucumber.spring.CucumberContextConfiguration;
import org.junit.runner.RunWith;

@RunWith(Cucumber.class)
@CucumberOptions(
        features = {"C:\\Bureau\\Bureau\\project_test\\features\\leave-request-management_20260131_193414.feature"},
        glue = {"com.example.userservice.stepdefinitions"},
        plugin = {
                "pretty",
                "html:target/cucumber-reports",
                "json:target/cucumber.json",
                "junit:target/cucumber-results.xml",
                "com.aventstack.extentreports.cucumber.adapter.ExtentCucumberAdapter:"
        },
        monochrome = true,
        dryRun = false
)
@CucumberContextConfiguration(classes = { /* Add your Spring configuration classes here */ })
public class UserServiceTestRunner {
}