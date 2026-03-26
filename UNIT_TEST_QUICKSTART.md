# Quick-Start: Writing Unit Tests for 25% Coverage

This guide shows how to write real unit tests that will improve coverage from **17.92% to 25%+** in about 1-2 hours.

## Step 1: Create Your First Service Test

**File**: `C:\Bureau\Bureau\microservices\conge\src\test\java\tn\enis\conge\services\LeaveServiceTest.java`

```java
package tn.enis.conge.services;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import tn.enis.conge.dto.LeaveRequestDTO;
import tn.enis.conge.entity.LeaveRequest;
import tn.enis.conge.repository.LeaveRequestRepository;

public class LeaveServiceTest {
    
    @Mock
    private LeaveRequestRepository leaveRequestRepository;
    
    private LeaveService leaveService;
    
    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        leaveService = new LeaveService(leaveRequestRepository);
    }
    
    // Test 1: Submit valid leave request
    @Test
    void testSubmitValidLeaveRequest() {
        LeaveRequestDTO request = new LeaveRequestDTO();
        request.setUserId(8L);
        request.setFromDate("2026-06-01");
        request.setToDate("2026-06-05");
        request.setType("ANNUAL_LEAVE");
        
        LeaveRequest savedRequest = new LeaveRequest();
        savedRequest.setId(1L);
        when(leaveRequestRepository.save(any())).thenReturn(savedRequest);
        
        LeaveRequest result = leaveService.submitLeaveRequest(request);
        
        assertNotNull(result);
        assertEquals(1L, result.getId());
        verify(leaveRequestRepository).save(any());
    }
    
    // Test 2: Reject invalid date range
    @Test
    void testRejectInvalidDateRange() {
        LeaveRequestDTO request = new LeaveRequestDTO();
        request.setUserId(8L);
        request.setFromDate("2026-06-05");
        request.setToDate("2026-06-01");  // End before start!
        
        assertThrows(IllegalArgumentException.class, () -> {
            leaveService.submitLeaveRequest(request);
        });
    }
    
    // Test 3: Validate leave balance
    @Test
    void testInsufficientLeaveBalance() {
        LeaveRequestDTO request = new LeaveRequestDTO();
        request.setUserId(8L);
        request.setFromDate("2026-06-01");
        request.setToDate("2026-12-31");  // 214 days!
        
        when(leaveRequestRepository.getUserBalance(8L)).thenReturn(20);
        
        assertThrows(IllegalArgumentException.class, () -> {
            leaveService.submitLeaveRequest(request);
        });
    }
    
    // Test 4: Check overlapping requests
    @Test
    void testDetectOverlappingRequests() {
        LeaveRequestDTO request1 = new LeaveRequestDTO();
        request1.setUserId(8L);
        request1.setFromDate("2026-06-01");
        request1.setToDate("2026-06-10");
        
        LeaveRequestDTO request2 = new LeaveRequestDTO();
        request2.setUserId(8L);
        request2.setFromDate("2026-06-05");  // Overlaps with request1
        request2.setToDate("2026-06-15");
        
        // Save first request
        leaveService.submitLeaveRequest(request1);
        
        // Try to save overlapping request
        when(leaveRequestRepository.hasOverlappingRequest(8L, "2026-06-05", "2026-06-15"))
            .thenReturn(true);
        
        assertThrows(IllegalArgumentException.class, () -> {
            leaveService.submitLeaveRequest(request2);
        });
    }
    
    // Test 5: Cancel pending request
    @Test
    void testCancelPendingRequest() {
        LeaveRequest request = new LeaveRequest();
        request.setId(1L);
        request.setStatus("PENDING");
        
        when(leaveRequestRepository.findById(1L)).thenReturn(java.util.Optional.of(request));
        
        leaveService.cancelRequest(1L);
        
        assertEquals("CANCELLED", request.getStatus());
        verify(leaveRequestRepository).save(request);
    }
    
    // Test 6: Approve request
    @Test
    void testApproveRequest() {
        LeaveRequest request = new LeaveRequest();
        request.setId(1L);
        request.setStatus("PENDING");
        
        when(leaveRequestRepository.findById(1L)).thenReturn(java.util.Optional.of(request));
        
        leaveService.approveRequest(1L);
        
        assertEquals("APPROVED", request.getStatus());
        verify(leaveRequestRepository).save(request);
    }
}
```

## Step 2: Create Your First Controller Test

**File**: `C:\Bureau\Bureau\microservices\conge\src\test\java\tn\enis\conge\controller\LeaveControllerTest.java`

```java
package tn.enis.conge.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.MockBean;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.mockito.Mockito.*;

import tn.enis.conge.services.LeaveService;
import tn.enis.conge.dto.LeaveRequestDTO;

@WebMvcTest(LeaveController.class)
public class LeaveControllerTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @MockBean
    private LeaveService leaveService;
    
    // Test 1: GET all leave requests
    @Test
    void testGetAllRequests() throws Exception {
        mockMvc.perform(get("/api/leave-requests"))
            .andExpect(status().isOk());
    }
    
    // Test 2: GET pending requests
    @Test
    void testGetPendingRequests() throws Exception {
        mockMvc.perform(get("/api/leave-requests?status=PENDING"))
            .andExpect(status().isOk());
    }
    
    // Test 3: POST create leave request
    @Test
    void testCreateLeaveRequest() throws Exception {
        String requestJson = """
            {
                "userId": 8,
                "fromDate": "2026-06-01",
                "toDate": "2026-06-05",
                "type": "ANNUAL_LEAVE"
            }
        """;
        
        mockMvc.perform(post("/api/leave-requests/create")
            .contentType("application/json")
            .content(requestJson))
            .andExpect(status().isOk());
    }
    
    // Test 4: PUT cancel request
    @Test
    void testCancelRequest() throws Exception {
        mockMvc.perform(put("/api/leave-requests/1/cancel")
            .contentType("application/json")
            .content("{}"))
            .andExpect(status().isOk());
    }
    
    // Test 5: PUT approve request
    @Test
    void testApproveRequest() throws Exception {
        mockMvc.perform(put("/api/leave-requests/1/approve"))
            .andExpect(status().isOk());
    }
    
    // Test 6: Error case - missing required field
    @Test
    void testCreateRequestMissingField() throws Exception {
        String invalidJson = """
            {
                "userId": 8
            }
        """;
        
        mockMvc.perform(post("/api/leave-requests/create")
            .contentType("application/json")
            .content(invalidJson))
            .andExpect(status().isBadRequest());
    }
}
```

## Step 3: Run Tests and Check Coverage

```powershell
# Navigate to microservice
cd C:\Bureau\Bureau\microservices\conge

# Clean and test
mvn clean test

# Generate JaCoCo report
mvn jacoco:report

# View report (Windows)
Start-Process "target\site\jacoco\index.html"
```

## Step 4: Expected Results

After adding these 12 tests:
- **Service tests**: 12 methods → ~40% service coverage
- **Controller tests**: 6 endpoints → ~30% controller coverage
- **Overall**: ~25-30% total coverage

## Tips for Reaching 60%

| Coverage Level | What to Test | Estimated Tests Needed |
|---|---|---|
| **25%** (Quick wins) | Services + Controllers | 20-30 tests |
| **40%** | Add DTO/Entity tests | 40-50 tests |
| **60%** | Add Exception paths | 60-80 tests |

### High-Value Test Cases for Quick Coverage Gains

1. **LeaveService** - Core business logic (10-15 tests)
   - Valid submissions
   - Invalid dates
   - Balance checks
   - Overlaps

2. **LeaveController** - HTTP endpoints (6-8 tests)
   - CRUD operations
   - Query parameters
   - Error cases

3. **LeaveDTO/Mapper** - Object conversion (8-12 tests)
   - Valid objects
   - Null handling
   - Edge cases

4. **Utility Classes** - Helper methods (5-10 tests)
   - Date calculations
   - String formats
   - Validators

**Total**: 30-45 tests = ~30-40% coverage

---

## Running Both Microservices

After implementing service tests:

```powershell
# Test Leave service
cd C:\Bureau\Bureau\microservices\conge
mvn clean test jacoco:report

# Test Auth service  
cd ..\DemandeConge
mvn clean test jacoco:report

# View combined results
```

## Next Steps

1. ✅ Create `LeaveServiceTest.java` (above)
2. ✅ Create `LeaveControllerTest.java` (above)
3. ⏳ Run `mvn clean test` - verify tests pass
4. ⏳ Run `mvn jacoco:report` - check coverage
5. ⏳ Create 20-30 more test methods for 60% coverage
6. ⏳ Update both microservices (conge + DemandeConge)

---

**Estimated time to 60% coverage**: 3-4 hours of writing tests

Start with the service layer - it usually gives the best coverage ROI!
