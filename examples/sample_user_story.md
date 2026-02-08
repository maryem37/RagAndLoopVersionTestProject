User Story

Microservice: Leave Request Management

Feature: Manage Own Leave Requests
Main User Story — Add Leave Request
As an employee,
I want to create a new leave request,
So that I can submit it for validation based on the selected leave type.
Business Rules — Add Leave Request
Each leave request must be assigned a unique identifier.
All new requests are created with the initial status of "Pending".
The unit of calculation varies based on the request type: days for "Annual" and "Unpaid" leave, and hours for "Authorization" and "Recovery" leave.
Public holidays and weekends are never included in daily leave calculations.
Hourly leave requests must align with the employee's defined working hours.
A request must cover a valid time period where the start date is earlier than or equal to the end date.
A request cannot overlap with another existing request that is either "Pending" or "Active".
Upon submission, the system must verify the available balance corresponding to the selected request type (Annual, Recovery, or Authorization) and block any request exceeding the available balance.
The minimum gap between the creation date and the leave start date must comply with the defined notice period of at least 48 hours.
A new request remains unapproved until both the Administrator and the Line Manager have granted their approval.


When the employee accesses the "Add Leave Request" option, the application automatically displays: first name, last name, employee ID, and the relevant balance based on the leave type.
The application must display the list of available leave types.
Type Selection
When the employee selects a leave type, the application must display the associated information:
Annual balance + pending annual requests (if Annual Leave).
Hours balance (if Recovery).
Only basic info (if other types).
Date / Time Entry
The application must enforce correct data entry:
Half-day selection (morning/afternoon) for half-day leaves.
Start/End time for hourly leaves.
A single date for one-day leaves.
If the selected date is not within the employee's work schedule, the application must display the corresponding error.
Automatic Calculation
Upon complete entry, the application automatically calculates the number of days or hours according to business rules.
The application never displays a negative or zero value (otherwise, it raises an error).
Validation
If mandatory fields are missing → Error message: "Warning! Please check the Employee ID and/or number of days and/or start date and/or end date!"
If Start Date > End Date → Error message: "Warning: 'From' date is later than 'To' date."
If the number of days/hours = 0 → Error message: "Number of days is zero."
If a request overlaps with another request → Error message: "Other requests exist during this period."
If the balance is insufficient → Error message: "Insufficient balance."
If the notice period (48h) is not respected → Error message: "The mandatory 48-hour notice period is not respected."
Creation
Upon validation, the application must:
Automatically generate a unique ID.
Save the status as "Pending".
Correctly record days/hours according to the type.
Set adminApproval = false and managerApproval = false.
Finalize creation in the database.
Confirmation
Once saved, the application must display the message: "Added successfully".

