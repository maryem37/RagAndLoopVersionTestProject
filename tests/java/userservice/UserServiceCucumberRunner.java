package com.example.userservice.test;
import io.cucumber.junit.CucumberOptions;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.runner.AbstractCucumberRunner;
import org.junit.runner.RunWith;

@RunWith(Cucumber.class)
@CucumberOptions(
        features = {"C:\\Bureau\\Bureau\\project_test\\features\\leave-request-management_20260201_195516.feature"},
        plugin = {
                "pretty",
                "html:target/cucumber-reports",
                "json:target/cucumber-reports/cucumber.json",
                "junit:target/cucumber-reports/cucumber.xml"
        },
        monochrome = true,
        strict = true,
        dryRun = false
)
public class UserServiceCucumberRunner extends AbstractCucumberRunner {
}
//This code creates a test runner named `UserServiceCucumberRunner`, which is annotated with `@RunWith(Cucumber.class)`. The Cucumber options are set using the `@CucumberOptions` annotation, including the feature file location, plugins for generating reports in different formats, and other configurations like strict mode and dry run.