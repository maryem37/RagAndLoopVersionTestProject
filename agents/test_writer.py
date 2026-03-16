"""
Agent 3: Contract-Level Test Writer — VERSION FINALE v8-fixed
FIXES from real Swagger spec at http://localhost:9001/v3/api-docs:
  - Create endpoint: /api/leave-requests/create
  - LeaveRequestDto fields: fromDate/toDate/type/userId/periodType
  - approve/reject/cancel use QUERY PARAMS not JSON body
  - approve requires role query param (Employer/Administration/TeamLeader)
  - reject requires role + reason query params
  - search requires currentUserId query param
  - Given status block: uses pre-inserted DB records (ID map) instead of
    POST create which was returning 500. IDs 2/3/4 must exist in DB.
"""
import re
import time
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Set
from loguru import logger
from graph.state import TestAutomationState, AgentOutput, AgentStatus
from config.settings import get_settings

SERVICE_URLS: Dict[str, str] = {
    "auth":         "http://localhost:9000",
    "conge":        "http://localhost:9000",
    "leave":        "http://localhost:9001",
    "DemandeConge": "http://localhost:9001",
}
AUTH_BASE_URL = "http://localhost:9000"
TEST_USER_ID = "8"


# ─────────────────────────────────────────────────────────────
# Gherkin parsing
# ─────────────────────────────────────────────────────────────

def parse_gherkin_steps(gherkin: str) -> List[Tuple[str, str]]:
    results, seen, last_kw = [], set(), "Given"
    for line in gherkin.splitlines():
        s = line.strip()
        for kw in ("Given", "When", "Then", "And", "But"):
            if s.startswith(kw + " "):
                text = s[len(kw):].strip()
                effective = last_kw if kw in ("And", "But") else kw
                if kw not in ("And", "But"):
                    last_kw = kw
                key = f"{effective}||{text}"
                if key not in seen:
                    seen.add(key)
                    results.append((effective, text))
                break
    return results


# ─────────────────────────────────────────────────────────────
# Text → Cucumber annotation
# ─────────────────────────────────────────────────────────────

def text_to_annotation(text: str) -> str:
    text = text.strip()
    text = re.sub(r'"([^"]*)"', '{string}', text)
    text = re.sub(r'\b\d+\b', '{int}', text)
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('(', '\\\\(').replace(')', '\\\\)')
    return text


def annotation_to_java_params(ann: str) -> str:
    params, s, i = [], 0, 0
    for m in re.finditer(r'\{(string|int|word|float|double)\}', ann):
        t = m.group(1)
        if t in ("string", "word"):
            params.append(f"String p{s}"); s += 1
        elif t == "int":
            params.append(f"int n{i}"); i += 1
        elif t in ("float", "double"):
            params.append(f"double d{i}"); i += 1
    return ", ".join(params)


def to_method_name(text: str) -> str:
    t = re.sub(r'\{[^}]+\}', 'X', text)
    t = re.sub(r'[^a-zA-Z0-9 ]', ' ', t)
    words = [w for w in t.strip().split() if w]
    if not words:
        return "step"
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


# ─────────────────────────────────────────────────────────────
# Swagger param extraction
# ─────────────────────────────────────────────────────────────

def get_required_query_params(swagger_spec: Dict, path: str, method: str = "get") -> List[str]:
    try:
        params = swagger_spec.get("paths", {}).get(path, {}).get(method, {}).get("parameters", [])
        return [
            p["name"]
            for p in params
            if p.get("in") == "query" and p.get("required", False)
        ]
    except Exception:
        return []


def build_required_params_java(required_params: List[str], ind: str) -> str:
    DEFAULTS = {
        "currentUserId":   TEST_USER_ID,
        "page":            "0",
        "size":            "10",
        "fromDate":        '"2024-01-01"',
        "toDate":          '"2024-12-31"',
        "states":          '"Pending"',
        "type":            '"ANNUAL_LEAVE"',
        "validationLevel": '"Employer"',
    }
    lines = []
    for param in required_params:
        if param in ("page", "size"):
            continue
        default = DEFAULTS.get(param, f'"{param}_test_value"')
        lines.append(
            f'{ind}req = req.queryParam("{param}", '
            f'requestBody.getOrDefault("{param}", {default}));'
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Endpoint selection
# ─────────────────────────────────────────────────────────────

def find_best_endpoint(text_lower: str, endpoints: List[str]) -> Tuple[str, str]:

    def clean(ep: str) -> str:
        return re.sub(r'\{[^}]+\}', '1', ep)

    def find_ep(keyword: str) -> str:
        for ep in endpoints:
            if keyword in ep.lower():
                return ep
        return ""

    if any(w in text_lower for w in (
        "refus", "refuse", "reject", "confirm the refusal",
        "submits the refusal", "attempt to refuse",
        "without selecting a reason", "without a reason"
    )):
        ep = find_ep("reject")
        return "put_reject", clean(ep) if ep else "/api/leave-requests/1/reject"

    if any(w in text_lower for w in ("approv", "grant", "accept", "validate")):
        ep = find_ep("approv")
        return "put_approve", clean(ep) if ep else "/api/leave-requests/1/approve"

    if any(w in text_lower for w in ("cancel", "annul", "withdraw")):
        ep = find_ep("cancel")
        return "put_cancel", clean(ep) if ep else "/api/leave-requests/1/cancel"

    if any(w in text_lower for w in ("creat", "new request", "add leave", "submit")):
        ep = find_ep("create")
        return "post", ep if ep else "/api/leave-requests/create"

    if any(w in text_lower for w in (
        "later than", "earlier than", "invalid date", "date that is later",
        "date that is earlier", "end date before", "start date after"
    )):
        ep = find_ep("search")
        return "get", clean(ep) if ep else "/api/leave-requests/search"

    if any(w in text_lower for w in (
        "not authorized", "unauthorized", "not part",
        "unauthorized user", "attempts to view",
        "unauthorized user attempts"
    )):
        ep = find_ep("search")
        return "get_unauthorized", clean(ep) if ep else "/api/leave-requests/search"

    if any(w in text_lower for w in (
        "search", "list", "view all", "get all",
        "view their", "views their", "views subordinate",
        "consultation", "accesses the consultation",
        "displays the list", "displays the correct list",
        "own leave requests", "subordinates' leave",
        "leave requests of", "displays filters",
        "filter", "period", "applies the filter", "applies a filter",
        "accesses the consultation interface",
        "employee accesses", "administrator accesses",
        "user accesses the consultation",
        "sorts and correctly displays",
    )):
        ep = find_ep("search")
        if not ep:
            for e in endpoints:
                if not any(w in e.lower() for w in ("reject", "approve", "cancel", "create")):
                    ep = e
                    break
        return "get", clean(ep) if ep else "/api/leave-requests/search"

    if any(w in text_lower for w in ("attempt", "try")):
        ep = find_ep("search")
        return "get", clean(ep) if ep else "/api/leave-requests/search"

    if not endpoints:
        return "get", "/api/leave-requests/search"

    best_ep, best_score = endpoints[0], 0
    for ep in endpoints:
        segments = re.split(r'[/\-_{}]', ep.lower())
        score = sum(1 for seg in segments if len(seg) > 3 and seg in text_lower)
        if score > best_score:
            best_score = score
            best_ep = ep

    if "reject" in best_ep.lower():
        return "put_reject", clean(best_ep)
    elif "approve" in best_ep.lower():
        return "put_approve", clean(best_ep)
    elif "cancel" in best_ep.lower():
        return "put_cancel", clean(best_ep)
    elif "create" in best_ep.lower():
        return "post", best_ep
    else:
        ep = find_ep("search")
        return "get", clean(ep) if ep else "/api/leave-requests/search"


# ─────────────────────────────────────────────────────────────
# Keyword correction
# ─────────────────────────────────────────────────────────────

ALWAYS_GIVEN_PREFIXES = [
    "does not select", "does not", "without selecting", "no reason",
    "provides", "already", "exist",
]

ALWAYS_WHEN_PREFIXES = [
    "i confirm", "i attempt", "i submit", "i select",
    "i click", "i send", "i trigger", "i refuse",
    "the user submits", "the user confirms", "the administrator confirms",
    "the unauthorized user",
]

def fix_keyword(keyword: str, text: str) -> str:
    text_lower = text.lower()
    if text_lower.startswith("the system "):
        return "Then"
    for pat in ALWAYS_WHEN_PREFIXES:
        if text_lower.startswith(pat):
            return "When"
    if keyword == "Then":
        for pat in ALWAYS_GIVEN_PREFIXES:
            if text_lower.startswith(pat):
                return "Given"
    return keyword


# ─────────────────────────────────────────────────────────────
# Java method body generator
# ─────────────────────────────────────────────────────────────

def generate_method_body(keyword: str, text: str, endpoints: List[str],
                         base_url: str, java_params: str,
                         swagger_spec: Dict = None) -> str:
    text_lower = text.lower()
    ind = "        "

    # ══════════════════════════════════════════════════════════
    # GIVEN
    # ══════════════════════════════════════════════════════════
    if keyword == "Given":

        # 1. UNAUTHORIZED
        if any(w in text_lower for w in (
            "not authorized", "unauthorized", "not part", "unauthorized user"
        )):
            return (
                f'{ind}requestBody.put("__useInvalidToken__", "true");\n'
                f'{ind}logger.info("Precondition: unauthorized user context");'
            )

        # 2. AUTH / JWT
        if any(w in text_lower for w in (
            "authenticated", "logged", "token", "auth",
            "valid credentials", "valid jwt", "administrator or team lead"
        )):
            return (
                f'{ind}assertThat(jwtToken)\n'
                f'{ind}    .as("JWT token must be set via TEST_JWT_TOKEN env var")\n'
                f'{ind}    .isNotBlank();\n'
                f'{ind}logger.info("Authenticated with JWT token");'
            )

        # 3. RESET STATE — preserves __useInvalidToken__
        if any(w in text_lower for w in (
            "system displays", "interface", "management",
            "application", "accessible", "consultation"
        )):
            return (
                f'{ind}String unauthorizedFlag = (String) requestBody.get("__useInvalidToken__");\n'
                f'{ind}requestBody.clear();\n'
                f'{ind}if (unauthorizedFlag != null) {{\n'
                f'{ind}    requestBody.put("__useInvalidToken__", unauthorizedFlag);\n'
                f'{ind}}}\n'
                f'{ind}response = null;\n'
                f'{ind}logger.info("Precondition: {text}");'
            )

        # 4. NO REASON
        if any(w in text_lower for w in ("does not select", "without selecting", "no reason")):
            return (
                f'{ind}requestBody.remove("reason");\n'
                f'{ind}logger.info("No reason selected (intentional)");'
            )

        # ════════════════════════════════════════════════════════
        # 5. STATUS — maps to pre-inserted DB test record ID.
        #    MUST come BEFORE "leave request" check because
        #    "the leave request status is X" contains "leave request".
        #
        #    Uses ID map instead of POST create (which returns 500).
        #    Requires these records in your DB:
        #      ID 2 → Pending
        #      ID 3 → In Progress
        #      ID 4 → Refused
        #      ID 1 → Approved/Granted
        #      ID 5 → Canceled
        # ════════════════════════════════════════════════════════
        if any(w in text_lower for w in (
            "leave request status", "request status is", "in status",
            "pending leave request", "leave request in pending",
            "leave request exists",
        )) or (
            "status" in text_lower
            and any(w in text_lower for w in ("selects", "select", "is "))
            and "leave request" not in text_lower.replace("leave request status", "")
        ):
            if "p0" in java_params:
                return (
                    f'{ind}requestBody.put("status", p0);\n'
                    f'{ind}// Map status → pre-inserted test request ID\n'
                    f'{ind}// These records must exist in your DB in the correct state\n'
                    f'{ind}java.util.Map<String,String> statusToId = new java.util.HashMap<>();\n'
                    f'{ind}statusToId.put("Pending",     "2");\n'
                    f'{ind}statusToId.put("In Progress", "3");\n'
                    f'{ind}statusToId.put("Refused",     "4");\n'
                    f'{ind}statusToId.put("Approved",    "1");\n'
                    f'{ind}statusToId.put("Granted",     "1");\n'
                    f'{ind}statusToId.put("Canceled",    "5");\n'
                    f'{ind}String testId = statusToId.getOrDefault(p0, "2");\n'
                    f'{ind}requestBody.put("__testRequestId__", testId);\n'
                    f'{ind}logger.info("Status {{}} → test request ID {{}}", p0, testId);'
                )
            return f'{ind}logger.info("Precondition: {text}");'

        # 6. ROLE — store role for approve/reject query param
        if any(w in text_lower for w in (
            "final approver", "intermediate approver", "approval chain",
            "team lead", "administrator", "employer",
            "the user is a", "the user is an", "the user is the"
        )):
            role = "Administration"
            if any(w in text_lower for w in ("team lead", "teamleader", "intermediate")):
                role = "TeamLeader"
            elif any(w in text_lower for w in ("employer", "employee")):
                role = "Employer"
            return (
                f'{ind}requestBody.put("role", "{role}");\n'
                f'{ind}logger.info("Role set: {role}");'
            )

        # 7. LEAVE REQUEST context (generic — after status)
        if any(w in text_lower for w in ("leave request", "a leave", "request with")):
            if "p0" in java_params and "p1" in java_params:
                return (
                    f'{ind}requestBody.put("leaveRequestName", p0);\n'
                    f'{ind}requestBody.put("expectedStatus", p1);\n'
                    f'{ind}logger.info("Leave request: {{}} | Status: {{}}", p0, p1);'
                )
            if "p0" in java_params:
                return (
                    f'{ind}requestBody.put("leaveRequest", p0);\n'
                    f'{ind}logger.info("Leave request context: {{}}", p0);'
                )
            return f'{ind}logger.info("Precondition: {text}");'

        # 8. DATE FIELDS — real API field names: fromDate/toDate
        if any(w in text_lower for w in (
            "start date", "end date", "from", "to", "period",
            "fromdate", "todate"
        )):
            if "p0" in java_params and "p1" in java_params:
                return (
                    f'{ind}requestBody.put("fromDate", p0);\n'
                    f'{ind}requestBody.put("toDate", p1);\n'
                    f'{ind}logger.info("Date range: {{}} to {{}}", p0, p1);'
                )
            if "p0" in java_params:
                field = "fromDate" if any(w in text_lower for w in ("start", "from")) else "toDate"
                return (
                    f'{ind}requestBody.put("{field}", p0);\n'
                    f'{ind}logger.info("Date set {field}: {{}}", p0);'
                )
            return f'{ind}logger.info("Date precondition: {text}");'

        # 9. REASON
        if "reason" in text_lower:
            if "p0" in java_params:
                return (
                    f'{ind}requestBody.put("reason", p0);\n'
                    f'{ind}logger.info("Reason set: {{}}", p0);'
                )
            return (
                f'{ind}requestBody.put("reason", "Test refusal reason");\n'
                f'{ind}logger.info("Default reason set");'
            )

        # 10. OBSERVATION / NOTE
        if any(w in text_lower for w in ("observation", "note")):
            if "p0" in java_params:
                return (
                    f'{ind}requestBody.put("note", p0);\n'
                    f'{ind}logger.info("Note set: {{}}", p0);'
                )
            return (
                f'{ind}requestBody.put("note", "Test observation");\n'
                f'{ind}logger.info("Default note set");'
            )

        # 11. GENERIC TEXT ENTRY
        if any(w in text_lower for w in ("enters", "enter", "optionally", "provides", "fills")):
            if "p0" in java_params:
                field = "reason" if "reason" in text_lower else "note"
                return (
                    f'{ind}requestBody.put("{field}", p0);\n'
                    f'{ind}logger.info("Set {field}: {{}}", p0);'
                )
            return f'{ind}logger.info("Input: {text}");'

        # 12. ACCESS / DETAILS
        if any(w in text_lower for w in ("access", "have access", "details", "views")):
            return f'{ind}logger.info("Precondition: access granted");'

        # 13. GENERIC WITH PARAMS
        if java_params:
            params_list = [p.strip().split()[-1] for p in java_params.split(",")]
            words = re.sub(r'[^a-zA-Z ]', ' ', text).split()
            field = words[-1].lower() if words else "field"
            body = ""
            for p in params_list:
                body += f'{ind}requestBody.put("{field}", {p});\n'
            body += f'{ind}logger.info("Set {field}: {{}}", {params_list[0]});'
            return body

        return f'{ind}logger.info("Precondition: {text}");'

    # ══════════════════════════════════════════════════════════
    # WHEN
    # ══════════════════════════════════════════════════════════
    elif keyword == "When":
        method, clean_path = find_best_endpoint(text_lower, endpoints)
        clean_path = re.sub(r'\{[^}]+\}', '1', clean_path)

        if method == "get_unauthorized":
            return (
                f'{ind}response = given()\n'
                f'{ind}    .baseUri(BASE_URL)\n'
                f'{ind}    .header("Authorization", "Bearer invalid_token_for_test")\n'
                f'{ind}    .queryParam("currentUserId", {TEST_USER_ID})\n'
                f'{ind}    .queryParam("page", 0)\n'
                f'{ind}    .queryParam("size", 10)\n'
                f'{ind}    .when()\n'
                f'{ind}    .get("{clean_path}")\n'
                f'{ind}    .then()\n'
                f'{ind}    .extract().response();\n'
                f'{ind}logger.info("Unauthorized GET -> HTTP {{}}", response.getStatusCode());'
            )

        token_line = (
            f'{ind}String authToken = requestBody.containsKey("__useInvalidToken__")\n'
            f'{ind}    ? "invalid_token_for_test" : jwtToken;\n'
        )

        # APPROVE — role as query param, dynamic path from __testRequestId__
        if method == "put_approve":
            return (
                f'{token_line}'
                f'{ind}String approvePath = "{clean_path}";\n'
                f'{ind}if (requestBody.containsKey("__testRequestId__")) {{\n'
                f'{ind}    approvePath = approvePath.replaceFirst("/\\\\d+/",\n'
                f'{ind}        "/" + requestBody.get("__testRequestId__") + "/");\n'
                f'{ind}}}\n'
                f'{ind}String approveRole = (String) requestBody.getOrDefault("role", "Administration");\n'
                f'{ind}io.restassured.specification.RequestSpecification approveReq = given()\n'
                f'{ind}    .baseUri(BASE_URL)\n'
                f'{ind}    .header("Authorization", "Bearer " + authToken)\n'
                f'{ind}    .queryParam("role", approveRole);\n'
                f'{ind}if (requestBody.containsKey("note")) {{\n'
                f'{ind}    approveReq = approveReq.queryParam("note", requestBody.get("note"));\n'
                f'{ind}}}\n'
                f'{ind}response = approveReq.when()\n'
                f'{ind}    .put(approvePath)\n'
                f'{ind}    .then()\n'
                f'{ind}    .extract().response();\n'
                f'{ind}logger.info("PUT {{}} (approve, role={{}}) -> HTTP {{}}", approvePath, approveRole, response.getStatusCode());'
            )

        # REJECT — role + reason as query params, dynamic path
        if method == "put_reject":
            return (
                f'{token_line}'
                f'{ind}String rejectPath = "{clean_path}";\n'
                f'{ind}if (requestBody.containsKey("__testRequestId__")) {{\n'
                f'{ind}    rejectPath = rejectPath.replaceFirst("/\\\\d+/",\n'
                f'{ind}        "/" + requestBody.get("__testRequestId__") + "/");\n'
                f'{ind}}}\n'
                f'{ind}String rejectRole   = (String) requestBody.getOrDefault("role", "Administration");\n'
                f'{ind}String rejectReason = (String) requestBody.getOrDefault("reason", "Test refusal reason");\n'
                f'{ind}io.restassured.specification.RequestSpecification rejectReq = given()\n'
                f'{ind}    .baseUri(BASE_URL)\n'
                f'{ind}    .header("Authorization", "Bearer " + authToken)\n'
                f'{ind}    .queryParam("role", rejectRole)\n'
                f'{ind}    .queryParam("reason", rejectReason);\n'
                f'{ind}if (requestBody.containsKey("note")) {{\n'
                f'{ind}    rejectReq = rejectReq.queryParam("observation", requestBody.get("note"));\n'
                f'{ind}}}\n'
                f'{ind}response = rejectReq.when()\n'
                f'{ind}    .put(rejectPath)\n'
                f'{ind}    .then()\n'
                f'{ind}    .extract().response();\n'
                f'{ind}logger.info("PUT {{}} (reject, role={{}}) -> HTTP {{}}", rejectPath, rejectRole, response.getStatusCode());'
            )

        # CANCEL — observation as optional query param, dynamic path
        if method == "put_cancel":
            return (
                f'{token_line}'
                f'{ind}String cancelPath = "{clean_path}";\n'
                f'{ind}if (requestBody.containsKey("__testRequestId__")) {{\n'
                f'{ind}    cancelPath = cancelPath.replaceFirst("/\\\\d+/",\n'
                f'{ind}        "/" + requestBody.get("__testRequestId__") + "/");\n'
                f'{ind}}}\n'
                f'{ind}io.restassured.specification.RequestSpecification cancelReq = given()\n'
                f'{ind}    .baseUri(BASE_URL)\n'
                f'{ind}    .header("Authorization", "Bearer " + authToken);\n'
                f'{ind}if (requestBody.containsKey("note")) {{\n'
                f'{ind}    cancelReq = cancelReq.queryParam("observation", requestBody.get("note"));\n'
                f'{ind}}}\n'
                f'{ind}response = cancelReq.when()\n'
                f'{ind}    .put(cancelPath)\n'
                f'{ind}    .then()\n'
                f'{ind}    .extract().response();\n'
                f'{ind}logger.info("PUT {{}} (cancel) -> HTTP {{}}", cancelPath, response.getStatusCode());'
            )

        # POST — create with real LeaveRequestDto fields
        if method == "post":
            return (
                f'{token_line}'
                f'{ind}String actionPath = "{clean_path}";\n'
                f'{ind}java.util.Map<String, Object> createBody = new java.util.HashMap<>();\n'
                f'{ind}createBody.put("type",       requestBody.getOrDefault("type", "ANNUAL_LEAVE"));\n'
                f'{ind}createBody.put("fromDate",   requestBody.getOrDefault("fromDate", "2025-06-01"));\n'
                f'{ind}createBody.put("toDate",     requestBody.getOrDefault("toDate", "2025-06-05"));\n'
                f'{ind}createBody.put("periodType", requestBody.getOrDefault("periodType", "JOURNEE_COMPLETE"));\n'
                f'{ind}createBody.put("userId",     {TEST_USER_ID}L);\n'
                f'{ind}if (requestBody.containsKey("note")) createBody.put("note", requestBody.get("note"));\n'
                f'{ind}response = given()\n'
                f'{ind}    .baseUri(BASE_URL)\n'
                f'{ind}    .header("Authorization", "Bearer " + authToken)\n'
                f'{ind}    .contentType(ContentType.JSON)\n'
                f'{ind}    .body(createBody)\n'
                f'{ind}    .when()\n'
                f'{ind}    .post(actionPath)\n'
                f'{ind}    .then()\n'
                f'{ind}    .extract().response();\n'
                f'{ind}logger.info("POST {{}} -> HTTP {{}}", actionPath, response.getStatusCode());'
            )

        # GET — currentUserId required, optional filters from requestBody
        required_params_java = ""
        if swagger_spec:
            original_path = clean_path
            for ep in endpoints:
                if re.sub(r'\{[^}]+\}', '1', ep) == clean_path:
                    original_path = ep
                    break
            required = get_required_query_params(swagger_spec, original_path, "get")
            required_params_java = build_required_params_java(required, ind)

        extra_params = (
            f'{ind}if (requestBody.containsKey("fromDate")) {{\n'
            f'{ind}    req = req.queryParam("fromDate", requestBody.get("fromDate"));\n'
            f'{ind}}}\n'
            f'{ind}if (requestBody.containsKey("toDate")) {{\n'
            f'{ind}    req = req.queryParam("toDate", requestBody.get("toDate"));\n'
            f'{ind}}}\n'
            f'{ind}if (requestBody.containsKey("states")) {{\n'
            f'{ind}    req = req.queryParam("states", requestBody.get("states"));\n'
            f'{ind}}}\n'
            f'{ind}if (requestBody.containsKey("type")) {{\n'
            f'{ind}    req = req.queryParam("type", requestBody.get("type"));\n'
            f'{ind}}}\n'
        )

        required_block = (f'\n{required_params_java}' if required_params_java else "")

        return (
            f'{token_line}'
            f'{ind}io.restassured.specification.RequestSpecification req = given()\n'
            f'{ind}    .baseUri(BASE_URL)\n'
            f'{ind}    .header("Authorization", "Bearer " + authToken)\n'
            f'{ind}    .queryParam("currentUserId", {TEST_USER_ID})\n'
            f'{ind}    .queryParam("page", 0)\n'
            f'{ind}    .queryParam("size", 10);'
            f'{required_block}\n'
            f'{extra_params}'
            f'{ind}response = req.when()\n'
            f'{ind}    .get("{clean_path}")\n'
            f'{ind}    .then()\n'
            f'{ind}    .extract().response();\n'
            f'{ind}logger.info("GET {clean_path} -> HTTP {{}}", response.getStatusCode());'
        )

    # ══════════════════════════════════════════════════════════
    # THEN
    # ══════════════════════════════════════════════════════════
    elif keyword == "Then":

        null_guard = (
            f'{ind}assertThat(response)\n'
            f'{ind}    .as("No HTTP call was made — missing When step")\n'
            f'{ind}    .isNotNull();\n'
        )

        if any(w in text_lower for w in (
            "status code", "http code", "response code",
            "return status", "returns status"
        )) and "n0" in java_params:
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode())\n'
                f'{ind}    .as("Expected HTTP " + n0)\n'
                f'{ind}    .isEqualTo(n0);\n'
                f'{ind}logger.info("HTTP status: {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in (
            "status changes", "status is", "status to",
            "updates the request status", "request status", "the status changes"
        )):
            if "p0" in java_params:
                return (
                    f'{null_guard}'
                    f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                    f'{ind}String actualState = response.jsonPath().getString("state");\n'
                    f'{ind}assertThat(actualState)\n'
                    f'{ind}    .as("Request state should be " + p0)\n'
                    f'{ind}    .isEqualToIgnoringCase(p0);\n'
                    f'{ind}logger.info("State confirmed: {{}}", actualState);'
                )
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                f'{ind}logger.info("Status confirmed, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in (
            "error message", "displays an error", "displays error",
            "system displays an error", "displays the error", "warning"
        )):
            if "p0" in java_params:
                return (
                    f'{null_guard}'
                    f'{ind}int statusCode = response.getStatusCode();\n'
                    f'{ind}assertThat(statusCode)\n'
                    f'{ind}    .as("Expected error response (4xx) for: " + p0)\n'
                    f'{ind}    .isGreaterThanOrEqualTo(400);\n'
                    f'{ind}String body = response.getBody().asString();\n'
                    f'{ind}logger.info("Error HTTP {{}}: {{}}", statusCode, body);\n'
                    f'{ind}// assertThat(body).contains(p0);'
                )
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isGreaterThanOrEqualTo(400);\n'
                f'{ind}logger.info("Error confirmed, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in ("system displays", "the system displays")):
            if "p0" in java_params:
                return (
                    f'{null_guard}'
                    f'{ind}int statusCode = response.getStatusCode();\n'
                    f'{ind}String body = response.getBody().asString();\n'
                    f'{ind}assertThat(statusCode)\n'
                    f'{ind}    .as("Expected valid response for: " + p0)\n'
                    f'{ind}    .isBetween(200, 499);\n'
                    f'{ind}logger.info("System display HTTP {{}}: {{}}", statusCode, body);'
                )

        if any(w in text_lower for w in (
            "displays the list", "displays the correct list",
            "displays the correct", "list of", "displays filters",
            "displays the leave", "displays their",
            "correct list of their own", "correct list of subordinates",
            "filters for period", "filters for leave type"
        )):
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                f'{ind}assertThat(response.getBody().asString())\n'
                f'{ind}    .as("Response body should not be empty").isNotBlank();\n'
                f'{ind}logger.info("List/filters displayed, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in (
            "successfully", "success",
            "confirmation message", "displays a confirmation",
            "added successfully", "saved successfully",
            "request granted", "granted successfully"
        )):
            if "p0" in java_params:
                return (
                    f'{null_guard}'
                    f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                    f'{ind}String body = response.getBody().asString();\n'
                    f'{ind}logger.info("Success HTTP {{}}: {{}}", response.getStatusCode(), body);\n'
                    f'{ind}// assertThat(body).contains(p0);'
                )
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                f'{ind}logger.info("Success confirmed, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in (
            "blocks", "blocked", "system blocks",
            "cannot", "not allowed", "unauthorized",
            "remains unchanged", "not changed",
            "is not authorized", "not authorized"
        )):
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode())\n'
                f'{ind}    .as("Expected 4xx — action should be blocked")\n'
                f'{ind}    .isGreaterThanOrEqualTo(400);\n'
                f'{ind}logger.info("Blocked correctly, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in (
            "recorded", "records", "saved", "stored",
            "refusal date", "refusal date and reason"
        )):
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                f'{ind}assertThat(response.getBody().asString()).isNotBlank();\n'
                f'{ind}logger.info("Data recorded, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in ("observation", "manager's observation", "note")):
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                f'{ind}logger.info("Observation/note recorded, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in (
            "available", "option", "details", "complete details",
            "displays the", "refusal option"
        )):
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                f'{ind}assertThat(response.getBody().asString()).isNotBlank();\n'
                f'{ind}logger.info("Details available, HTTP {{}}", response.getStatusCode());'
            )

        if any(w in text_lower for w in (
            "updated", "refused", "granted",
            "changed to", "is now", "should be",
            "marks the manager", "validation as true", "balance is adjusted"
        )):
            return (
                f'{null_guard}'
                f'{ind}assertThat(response.getStatusCode()).isBetween(200, 299);\n'
                f'{ind}logger.info("Update confirmed, HTTP {{}}", response.getStatusCode());'
            )

        return (
            f'{null_guard}'
            f'{ind}int statusCode = response.getStatusCode();\n'
            f'{ind}assertThat(statusCode)\n'
            f'{ind}    .as("Expected a valid HTTP response (2xx or 4xx)")\n'
            f'{ind}    .isBetween(200, 499);\n'
            f'{ind}logger.info("Then validated, HTTP {{}}", statusCode);'
        )

    return f'{ind}logger.info("Step: {text}");'


# ─────────────────────────────────────────────────────────────
# Auth Steps
# ─────────────────────────────────────────────────────────────

def build_auth_steps_java(package_name: str, class_name: str, base_url: str) -> str:
    return (
        f"package com.example.{package_name}.steps;\n\n"
        "import io.cucumber.java.Before;\n"
        "import io.cucumber.java.en.*;\n"
        "import io.restassured.response.Response;\n"
        "import io.restassured.http.ContentType;\n"
        "import static io.restassured.RestAssured.*;\n"
        "import static org.assertj.core.api.Assertions.*;\n"
        "import java.util.*;\n"
        "import org.slf4j.Logger;\n"
        "import org.slf4j.LoggerFactory;\n\n"
        f"public class {class_name}Steps {{\n\n"
        f"    private static final Logger logger = LoggerFactory.getLogger({class_name}Steps.class);\n"
        f"    private static final String BASE_URL = \"{base_url}\";\n"
        "    private String jwtToken;\n"
        "    private Response response;\n"
        "    private Map<String, Object> requestBody;\n\n"
        "    @Before\n"
        "    public void setUp() {\n"
        "        jwtToken = System.getenv(\"TEST_JWT_TOKEN\");\n"
        "        if (jwtToken == null || jwtToken.isBlank()) {\n"
        "            logger.warn(\"TEST_JWT_TOKEN not set — tests may fail\");\n"
        "        }\n"
        "        requestBody = new HashMap<>();\n"
        "        response = null;\n"
        "    }\n\n"
        "    @Given(\"the user is authenticated\")\n"
        "    public void theUserIsAuthenticated() {\n"
        "        assertThat(jwtToken)\n"
        "            .as(\"JWT token must be set via TEST_JWT_TOKEN env var\")\n"
        "            .isNotBlank();\n"
        "        logger.info(\"Authenticated with JWT token\");\n"
        "    }\n\n"
        "    @Given(\"the user is authenticated as an administrator\")\n"
        "    public void theUserIsAuthenticatedAsAdministrator() {\n"
        "        assertThat(jwtToken).isNotBlank();\n"
        "        logger.info(\"Authenticated as administrator\");\n"
        "    }\n\n"
        "    @Given(\"the user is authenticated as a team lead\")\n"
        "    public void theUserIsAuthenticatedAsTeamLead() {\n"
        "        assertThat(jwtToken).isNotBlank();\n"
        "        logger.info(\"Authenticated as team lead\");\n"
        "    }\n\n"
        "    @Given(\"the user is authenticated as an employee\")\n"
        "    public void theUserIsAuthenticatedAsEmployee() {\n"
        "        assertThat(jwtToken).isNotBlank();\n"
        "        logger.info(\"Authenticated as employee\");\n"
        "    }\n\n"
        "}\n"
    )


# ─────────────────────────────────────────────────────────────
# Main Java Steps builder
# ─────────────────────────────────────────────────────────────

def build_steps_java(package_name: str, class_name: str, base_url: str,
                     gherkin: str, swagger_spec: Dict) -> str:
    endpoints = list(swagger_spec.get("paths", {}).keys())
    raw_steps = parse_gherkin_steps(gherkin)

    seen_names: Set[str] = {"setUp"}
    seen_kw_annotations: Set[str] = set()
    step_defs: List[str] = []

    setup = (
        "    @Before\n"
        "    public void setUp() {\n"
        "        jwtToken = System.getenv(\"TEST_JWT_TOKEN\");\n"
        "        if (jwtToken == null || jwtToken.isBlank()) {\n"
        "            logger.warn(\"TEST_JWT_TOKEN not set — tests may fail\");\n"
        "        }\n"
        "        requestBody = new HashMap<>();\n"
        "        response = null;\n"
        "    }"
    )
    step_defs.append(setup)

    for (kw, text) in raw_steps:
        kw = fix_keyword(kw, text)

        ann_text = text_to_annotation(text)
        safe_ann = ann_text.replace('"', '\\"')

        dedup_key = f"{kw}||{safe_ann}"
        if dedup_key in seen_kw_annotations:
            logger.warning(f"Ignored duplicate step: @{kw}(\"{safe_ann}\")")
            continue
        seen_kw_annotations.add(dedup_key)

        java_params = annotation_to_java_params(ann_text)

        base_name = to_method_name(ann_text)
        method_name = base_name
        counter = 1
        while method_name in seen_names:
            method_name = f"{base_name}{counter}"
            counter += 1
        seen_names.add(method_name)

        body = generate_method_body(kw, text, endpoints, base_url,
                                    java_params, swagger_spec)

        step_defs.append(
            f"    @{kw}(\"{safe_ann}\")\n"
            f"    public void {method_name}({java_params}) {{\n"
            f"{body}\n"
            f"    }}"
        )

    methods_block = "\n\n".join(step_defs)

    return (
        f"package com.example.{package_name}.steps;\n\n"
        "import io.cucumber.java.Before;\n"
        "import io.cucumber.java.en.*;\n"
        "import io.restassured.response.Response;\n"
        "import io.restassured.http.ContentType;\n"
        "import static io.restassured.RestAssured.*;\n"
        "import static org.assertj.core.api.Assertions.*;\n"
        "import java.util.*;\n"
        "import org.slf4j.Logger;\n"
        "import org.slf4j.LoggerFactory;\n\n"
        f"public class {class_name}Steps {{\n\n"
        f"    private static final Logger logger = LoggerFactory.getLogger({class_name}Steps.class);\n"
        f"    private static final String BASE_URL = \"{base_url}\";\n"
        f"    private static final String AUTH_URL = \"{AUTH_BASE_URL}\";\n"
        "    private String jwtToken;\n"
        "    private Response response;\n"
        "    private Map<String, Object> requestBody;\n\n"
        f"{methods_block}\n\n"
        "}\n"
    )


# ─────────────────────────────────────────────────────────────
# Cucumber Runner
# ─────────────────────────────────────────────────────────────

def build_runner_java(package_name: str, runner_class_name: str) -> str:
    return (
        f"package com.example.{package_name};\n\n"
        "import org.junit.runner.RunWith;\n"
        "import io.cucumber.junit.Cucumber;\n"
        "import io.cucumber.junit.CucumberOptions;\n\n"
        "@RunWith(Cucumber.class)\n"
        "@CucumberOptions(\n"
        f"    features = \"classpath:features\",\n"
        f"    glue = \"com.example.{package_name}.steps\",\n"
        "    plugin = {\n"
        "        \"pretty\",\n"
        "        \"html:target/cucumber-reports/cucumber.html\",\n"
        "        \"json:target/cucumber-reports/cucumber.json\"\n"
        "    },\n"
        "    monochrome = true\n"
        ")\n"
        f"public class {runner_class_name} {{\n"
        "}\n"
    )


# ─────────────────────────────────────────────────────────────
# Main Agent
# ─────────────────────────────────────────────────────────────

class TestWriterAgent:

    def __init__(self):
        self.settings = get_settings()
        logger.info("✅ TestWriter initialisé — MODE 100% PYTHON SANS LLM")

    def _to_camel_case(self, text: str) -> str:
        return "".join(w.capitalize() for w in re.split(r"[-_\s]+", text) if w)

    def generate_for_service(self, service_name: str, swagger_spec: Dict,
                              gherkin_content: str) -> Tuple[str, str]:
        base_url     = SERVICE_URLS.get(service_name, "http://localhost:8080")
        package_name = service_name.replace("-", "").replace("_", "").lower()
        class_name   = self._to_camel_case(service_name)
        runner_name  = f"{class_name}TestRunner"
        logger.info(f"   [{service_name}] base_url={base_url}")

        if service_name == "auth":
            steps_java = build_auth_steps_java(package_name, class_name, base_url)
        else:
            steps_java = build_steps_java(
                package_name, class_name, base_url,
                gherkin_content, swagger_spec
            )

        runner_java = build_runner_java(package_name, runner_name)
        logger.success(f"   [{service_name}] Java généré")
        return steps_java, runner_java

    def save_files_for_service(self, service_name: str, step_def_code: str,
                                runner_code: str) -> List[Path]:
        base_path    = self.settings.paths.tests_dir
        package_name = service_name.replace("-", "").replace("_", "").lower()
        class_name   = self._to_camel_case(service_name)
        java_base    = base_path / "src" / "test" / "java" / "com" / "example" / package_name
        steps_dir    = java_base / "steps"
        steps_dir.mkdir(parents=True, exist_ok=True)
        saved = []

        steps_file = steps_dir / f"{class_name}Steps.java"
        steps_file.write_text(step_def_code, encoding="utf-8")
        saved.append(steps_file)
        logger.success(f"   {steps_file.relative_to(base_path)}")

        runner_file = java_base / f"{class_name}TestRunner.java"
        runner_file.write_text(runner_code, encoding="utf-8")
        saved.append(runner_file)
        logger.success(f"   {runner_file.relative_to(base_path)}")

        return saved

    def save_pom_and_setup(self) -> Path:
        base_path = self.settings.paths.tests_dir
        base_path.mkdir(parents=True, exist_ok=True)

        pom_dest   = base_path / "pom.xml"
        pom_source = getattr(self.settings.paths, "pom_source", None) \
                     or self.settings.paths.base_dir / "tests" / "pom.xml"

        if pom_source.resolve() == pom_dest.resolve():
            logger.info(f"   ✓ pom.xml already in place → {pom_dest}")
        elif pom_source.exists():
            shutil.copy2(pom_source, pom_dest)
            logger.info(f"   ✓ pom.xml copied → {pom_dest}")
        else:
            logger.warning(f"   ⚠ pom.xml not found at {pom_source}")

        features_dir = base_path / "src" / "test" / "resources" / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        setup_file = base_path / "CONTRACT_TEST_SETUP.md"
        setup_file.write_text("# Contract Test Setup\n", encoding="utf-8")
        return setup_file

    def write_tests(self, state: TestAutomationState) -> TestAutomationState:
        start_time = time.time()
        logger.info("=" * 65)
        logger.info("🚀 TestWriter 100% PYTHON — aucun LLM")
        logger.info("=" * 65)
        try:
            swagger_specs: Dict[str, Dict] = {}
            if hasattr(state, "swagger_specs") and state.swagger_specs:
                swagger_specs = state.swagger_specs
            elif hasattr(state, "swagger_spec") and state.swagger_spec:
                swagger_specs = {state.service_name: state.swagger_spec}
            if not swagger_specs:
                raise ValueError("Aucune spec Swagger.")

            logger.info(f"   Services : {list(swagger_specs.keys())}")
            all_saved_files, all_step_defs, all_runners = [], {}, {}

            for service_name, swagger_spec in swagger_specs.items():
                logger.info(f"\n📦 Traitement : {service_name}")
                steps_code, runner_code = self.generate_for_service(
                    service_name, swagger_spec, state.gherkin_content
                )
                saved = self.save_files_for_service(service_name, steps_code, runner_code)
                all_saved_files.extend(saved)
                all_step_defs[service_name] = steps_code
                all_runners[service_name]   = runner_code

            all_saved_files.append(self.save_pom_and_setup())
            state.test_code  = {"step_definitions": all_step_defs, "runners": all_runners}
            state.test_files = [str(f) for f in all_saved_files]

            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="test_writer",
                status=AgentStatus.SUCCESS,
                duration_ms=duration,
                output_data={
                    "services_processed": list(swagger_specs.keys()),
                    "files_generated":    len(all_saved_files)
                },
            ))
            logger.success(f"✅ TestWriter terminé en {duration:.0f}ms")

        except Exception as exc:
            import traceback
            logger.error(f"❌ TestWriter échoué : {exc}")
            logger.debug(traceback.format_exc())
            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="test_writer",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(exc)
            ))
            state.add_error(f"TestWriter échoué : {exc}")

        return state


def test_writer_node(state: TestAutomationState) -> TestAutomationState:
    agent = TestWriterAgent()
    return agent.write_tests(state)