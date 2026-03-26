# Leave Request Management - Complete Feature Story

**As an** Employee  
**I want to** Submit, manage, and track leave requests  
**So that** I can manage my time off effectively  

## Feature: Leave Request Lifecycle

### Submission & Validation Tests
- Create a valid leave request with start date, end date, and reason
- Reject submission with end date before start date
- Reject request with past dates
- Reject request with invalid leave type
- Reject submission with empty/null fields
- Prevent duplicate requests on same dates
- Validate request status changes to PENDING
- Prevent zero or negative balance updates
- Reject request exceeding maximum continuous days allowed

### Error Scenario Tests
- Employee submits without filling all required fields
- Employee submits with start date later than end date
- Employee submits with zero days requested
- Employee submits overlapping with another request
- Employee submits with insufficient balance
- Employee submits without respecting notice period (48 hours)
- Unauthorized employee attempts to create request

### Approval & Management Tests
- Manager approves pending request
- Manager rejects pending request with reason
- Request status changes to APPROVED/REJECTED
- Cannot approve already processed request
- Cannot approve non-existent request

### Balance & Integration Tests
- Create request and verify balance deducted
- Create request and reject - verify balance unchanged
- Multiple requests for same employee are retrievable
- Concurrent requests handled correctly
- Authorization checks prevent access to other's requests

### Boundary & Edge Case Tests
- Test with minimum 1 day leave
- Test with maximum allowed continuous days
- Test with exact leave balance
- Test with zero balance
- Test with very old and future dates
