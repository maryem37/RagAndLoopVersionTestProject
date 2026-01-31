Feature: User Login

Scenario: Successful login with valid credentials
  Given a registered user
  And the user has valid credentials
  When the user enters correct username and password
  Then the system should allow access to the dashboard

Scenario: Failed login due to incorrect password
  Given a registered user
  And the user has invalid credentials (incorrect password)
  When the user enters incorrect password
  Then the system should display "Invalid credentials" error message