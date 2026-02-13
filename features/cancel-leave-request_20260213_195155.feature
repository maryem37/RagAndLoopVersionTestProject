Feature: Cancel Leave Request

  Background:
    Given the employee "John Doe" (ID: 1001) is authenticated
    And required reference data exists for leave types "Annual", "Sick", and "Unpaid"
    And at least one leave type "Annual" is available



  Scenario: Cancel a pending leave request
    Given John Doe submits a leave request for "2023-12-25" to "2023-12-29" with leave type "Annual"
    And the leave request is in "Pending" status
    And enters cancellation observation "Personal reasons"
    Then the system changes the leave request status to "Canceled"
    And the system records cancellation date as "2023-11-15"
    And the system records cancellation observation as "Personal reasons"


  Scenario: Cancel a leave request under validation
    Given John Doe submits a leave request for "2023-11-20" to "2023-11-24" with leave type "Annual"
    And the leave request is in "Under Validation" status
    And enters cancellation observation "Family emergency"
    Then the system changes the leave request status to "Canceled"
    And the system records cancellation date as "2023-11-15"
    And the system records cancellation observation as "Family emergency"


  Scenario: Attempt to cancel a granted leave request
    Given John Doe submits a leave request for "2023-10-10" to "2023-10-14" with leave type "Annual"
    And the leave request is in "Granted" status
    When John Doe clicks "Cancel Request" button
    Then the system displays "This leave request has already been granted and cannot be canceled"


  Scenario: Attempt to cancel a refused leave request
    Given John Doe submits a leave request for "2023-09-05" to "2023-09-09" with leave type "Annual"
    And the leave request is in "Refused" status
    When John Doe clicks "Cancel Request" button
    Then the system displays "This leave request has already been refused and cannot be canceled"


  Scenario: Attempt to cancel a leave request that is already canceled
    Given John Doe submits a leave request for "2023-08-15" to "2023-08-19" with leave type "Annual"
    And the leave request is in "Canceled" status with cancellation date "2023-07-20"
    When John Doe clicks "Cancel Request" button
    Then the system displays "This leave request has already been canceled and cannot be canceled again"


  Scenario: Cancel a leave request without providing an observation
    Given John Doe submits a leave request for "2023-07-01" to "2023-07-05" with leave type "Annual"
    And the leave request is in "Pending" status
    And leaves cancellation observation field empty
    Then the system changes the leave request status to "Canceled"
    And the system records cancellation date as "2023-11-15"
    And the system records cancellation observation as "No observation provided"


  Scenario: Cancel a leave request with a very long observation
    Given John Doe submits a leave request for "2023-06-10" to "2023-06-14" with leave type "Annual"
    And the leave request is in "Pending" status
    And enters cancellation observation "This observation is extremely long and exceeds the maximum allowed length of 500 characters. It should be truncated or rejected by the system to ensure data integrity and proper functionality."
    Then the system changes the leave request status to "Canceled"
    And the system records cancellation date as "2023-11-15"
    And the system records cancellation observation as "This observation is extremely long and exceeds the maximum allowed length of 500 characters. It should be truncated or rejected by the system to ensure data integrity and proper functionality."


  Scenario: Cancel a leave request with special characters in observation
    Given John Doe submits a leave request for "2023-05-20" to "2023-05-24" with leave type "Annual"
    And the leave request is in "Pending" status
