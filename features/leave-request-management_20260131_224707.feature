Feature: Leave Request Management

Scenario: Fetch all leave requests
  Given I have an authenticated API client
  When I send a GET request to "/leave-requests"
  Then the status code should be 200
  And the response body should contain a list of leave requests

Scenario: Create a new leave request with valid data
  Given I have an authenticated API client
  And I have a valid LeaveRequestCreate object
  When I send a POST request to "/leave-requests" with the LeaveRequestCreate object as JSON body
  Then the status code should be 201
  And the response body should contain the created leave request

Scenario: Create a new leave request with invalid data
  Given I have an authenticated API client
  And I have an invalid LeaveRequestCreate object
  When I send a POST request to "/leave-requests" with the invalid LeaveRequestCreate object as JSON body
  Then the status code should be 400
  And the response body should contain error details for the invalid data