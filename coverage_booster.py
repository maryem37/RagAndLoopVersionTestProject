import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    base_url: str
    spec_path: Path


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    # Only supports local refs like: #/components/schemas/Foo
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    node: Any = spec
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def _example_for_schema(
    spec: Dict[str, Any],
    schema: Dict[str, Any],
    depth: int,
    visited_refs: Optional[set[str]] = None,
) -> Any:
    if visited_refs is None:
        visited_refs = set()
    if depth <= 0:
        return None

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in visited_refs:
            return None
        visited_refs.add(ref)
        resolved = _resolve_ref(spec, ref)
        return _example_for_schema(spec, resolved, depth - 1, visited_refs)

    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]

    schema_type = schema.get("type")
    schema_format = schema.get("format")

    if schema_type == "string":
        if schema_format == "date":
            return "2030-01-10"
        if schema_format == "time":
            return "09:00:00"
        if schema_format == "date-time":
            return "2030-01-10T09:00:00Z"
        return "test"

    if schema_type == "integer":
        # Prefer a likely-existing user/entity id in seeded demo DBs.
        return 2

    if schema_type == "number":
        return 1.0

    if schema_type == "boolean":
        return True

    if schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            return [_example_for_schema(spec, items, depth - 1, visited_refs)]
        return []

    if schema_type == "object" or "properties" in schema:
        props = schema.get("properties")
        if not isinstance(props, dict):
            return {}
        obj: Dict[str, Any] = {}
        for key, value_schema in props.items():
            if isinstance(value_schema, dict):
                obj[key] = _example_for_schema(spec, value_schema, depth - 1, visited_refs)
        return obj

    return None


def _build_url(
    base_url: str,
    path_template: str,
    path_params: List[Dict[str, Any]],
    query_params: List[Dict[str, Any]],
    spec: Dict[str, Any],
) -> str:
    path = path_template
    for p in path_params:
        name = p.get("name")
        schema = p.get("schema") if isinstance(p.get("schema"), dict) else {}
        if not name:
            continue
        value = _example_for_schema(spec, schema, depth=2)
        if value is None:
            value = 1
        path = path.replace("{" + str(name) + "}", urllib.parse.quote(str(value)))

    query: Dict[str, str] = {}
    for p in query_params:
        if not p.get("required"):
            continue
        name = p.get("name")
        schema = p.get("schema") if isinstance(p.get("schema"), dict) else {}
        if not name:
            continue
        value = _example_for_schema(spec, schema, depth=2)
        if value is None:
            value = "test"
        query[str(name)] = str(value)

    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return url


def _request(method: str, url: str, jwt: str, body: Optional[Dict[str, Any]]) -> Tuple[int, str, str]:
    headers = {"Accept": "application/json"}
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"

    data: Optional[bytes] = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.getcode(), resp.reason or "", raw
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        return e.code, str(e.reason), raw
    except Exception as e:
        return 0, type(e).__name__, ""


def _make_request(method: str, url: str, jwt: str, body: Optional[Dict[str, Any]]) -> Tuple[int, str]:
    status, reason, _raw = _request(method, url, jwt, body)
    return status, reason


def _try_login_for_jwt(base_url: str, email: str, password: str) -> str:
    """Attempt to log in and extract a JWT token from the response."""
    login_url = base_url.rstrip("/") + "/api/auth/login"
    status, _reason, raw = _request(
        method="POST",
        url=login_url,
        jwt="",
        body={"email": email, "password": password},
    )
    if not (200 <= status < 300):
        return ""

    try:
        payload = json.loads(raw)
    except Exception:
        return ""

    # Common token keys
    for key in ("token", "accessToken", "jwt", "jwtToken", "id_token", "access_token"):
        value = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(value, str) and len(value) > 20:
            return value
    return ""


def _iter_operations(spec: Dict[str, Any]) -> Iterable[Tuple[str, str, Dict[str, Any]]]:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not isinstance(op, dict):
                continue
            yield path, method.upper(), op


def _priority_for_op(service_name: str, path: str, method: str) -> int:
    # Run create/init operations first so we can reuse created IDs.
    if service_name == "leave":
        if path == "/api/leave-requests/create" and method == "POST":
            return 0
        if path.startswith("/api/balances/init/") and method == "POST":
            return 1
        if path == "/api/admin/holidays" and method == "POST":
            return 2
    if service_name == "auth":
        if path == "/api/admin/departments/create" and method == "POST":
            return 0
    return 10


def _extract_params(op: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    params = op.get("parameters")
    if not isinstance(params, list):
        return [], []
    path_params = [p for p in params if isinstance(p, dict) and p.get("in") == "path"]
    query_params = [p for p in params if isinstance(p, dict) and p.get("in") == "query"]
    return path_params, query_params


def _extract_body_schema(spec: Dict[str, Any], op: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return None
    content = rb.get("content")
    if not isinstance(content, dict):
        return None
    app_json = content.get("application/json")
    if not isinstance(app_json, dict):
        # fallback to */*
        app_json = content.get("*/*")
        if not isinstance(app_json, dict):
            return None
    schema = app_json.get("schema")
    return schema if isinstance(schema, dict) else None


def run_service(service: ServiceSpec, jwt: str) -> Dict[str, Any]:
    spec = _load_json(service.spec_path)
    attempted = 0
    ok = 0
    by_status: Dict[int, int] = {}

    context: Dict[str, Any] = {}

    ops = list(_iter_operations(spec))
    ops.sort(key=lambda t: _priority_for_op(service.name, t[0], t[1]))

    def _maybe_remove_id_on_create(body_obj: Optional[Dict[str, Any]], http_method: str) -> Optional[Dict[str, Any]]:
        if body_obj is None:
            return None
        if http_method == "POST":
            body_obj.pop("id", None)
        return body_obj

    def _extract_id_from_payload(payload: Any) -> Optional[int]:
        if isinstance(payload, dict):
            value = payload.get("id")
            if isinstance(value, int):
                return value
            # Sometimes ids come back as strings.
            if isinstance(value, str) and value.isdigit():
                try:
                    return int(value)
                except Exception:
                    return None
        return None

    for path, method, op in ops:
        path_params, query_params = _extract_params(op)

        # Reuse IDs from earlier successful creates.
        if service.name == "leave" and "leave_request_id" in context and "{id}" in path and "leave-requests" in path:
            for p in path_params:
                if p.get("name") == "id":
                    p["schema"] = {"type": "integer"}
            # The URL builder will substitute {id} from schema; override via template replace.
            path = path.replace("{id}", str(context["leave_request_id"]))
        if service.name == "auth" and "department_id" in context and "{id}" in path and "departments" in path:
            path = path.replace("{id}", str(context["department_id"]))
        if service.name == "leave" and "holiday_id" in context and "{id}" in path and "/api/admin/holidays/" in path:
            path = path.replace("{id}", str(context["holiday_id"]))

        url = _build_url(service.base_url, path, path_params, query_params, spec)

        body: Optional[Dict[str, Any]] = None
        body_schema = _extract_body_schema(spec, op)
        if body_schema is not None and method in {"POST", "PUT", "PATCH"}:
            example = _example_for_schema(spec, body_schema, depth=3)
            body = example if isinstance(example, dict) else {}

        body = _maybe_remove_id_on_create(body, method)

        # Service-specific tweaks to reduce 4xx/5xx and enable stateful follow-ups.
        if service.name == "leave" and path == "/api/leave-requests/create" and isinstance(body, dict):
            body.setdefault("userId", 2)
            body.setdefault("fromDate", "2030-01-10")
            body.setdefault("toDate", "2030-01-12")
            body.setdefault("periodType", "JOURNEE_COMPLETE")
            body.setdefault("type", "ANNUAL_LEAVE")
        if service.name == "leave" and path == "/api/admin/holidays" and isinstance(body, dict):
            body.pop("id", None)
            body.setdefault("startDate", "2030-01-01")
            body.setdefault("endDate", "2030-01-02")
            body.setdefault("description", "coverage")

        status, _reason, raw = _request(method, url, jwt, body)
        attempted += 1
        by_status[status] = by_status.get(status, 0) + 1
        if 200 <= status < 300:
            ok += 1

        # Capture created IDs for subsequent calls.
        if 200 <= status < 300 and raw:
            try:
                payload = json.loads(raw)
            except Exception:
                payload = None

            if isinstance(payload, dict):
                if service.name == "leave" and path == "/api/leave-requests/create":
                    created_id = _extract_id_from_payload(payload)
                    if created_id is not None:
                        context["leave_request_id"] = created_id
                if service.name == "auth" and path == "/api/admin/departments/create":
                    created_id = _extract_id_from_payload(payload)
                    if created_id is not None:
                        context["department_id"] = created_id
                if service.name == "leave" and path == "/api/admin/holidays":
                    created_id = _extract_id_from_payload(payload)
                    if created_id is not None:
                        context["holiday_id"] = created_id

        # small delay to avoid overloading startup JVM
        time.sleep(0.05)

    # Extra stateful flows to drive deeper business logic.
    if service.name == "leave":
        def _bump(status_code: int) -> None:
            nonlocal attempted, ok
            attempted += 1
            by_status[status_code] = by_status.get(status_code, 0) + 1
            if 200 <= status_code < 300:
                ok += 1

        base = service.base_url.rstrip("/")

        # Ensure a balance exists for a likely seeded user.
        status, _reason, _raw = _request("POST", f"{base}/api/balances/init/2", jwt, None)
        _bump(status)

        variants = [
            {"type": "ANNUAL_LEAVE", "periodType": "JOURNEE_COMPLETE", "fromDate": "2030-01-10", "toDate": "2030-01-12"},
            {"type": "RECOVERY_LEAVE", "periodType": "PAR_HEURE", "fromDate": "2030-01-15", "toDate": "2030-01-15", "fromTime": "09:00:00", "toTime": "12:00:00"},
        ]

        for v in variants:
            create_body: Dict[str, Any] = {
                "userId": 2,
                "type": v["type"],
                "periodType": v["periodType"],
                "fromDate": v["fromDate"],
                "toDate": v["toDate"],
                "note": "coverage",
            }
            if "fromTime" in v:
                create_body["fromTime"] = v["fromTime"]
            if "toTime" in v:
                create_body["toTime"] = v["toTime"]

            status, _reason, raw = _request("POST", f"{base}/api/leave-requests/create", jwt, create_body)
            _bump(status)

            created_id: Optional[int] = None
            if raw:
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = None
                created_id = _extract_id_from_payload(payload)

            if created_id is None:
                continue

            context["leave_request_id"] = created_id

            # Try various transitions / roles to cover additional branches.
            approve_qs = urllib.parse.urlencode({"role": "TeamLeader", "note": "coverage"})
            status, _reason, _raw = _request(
                "PUT",
                f"{base}/api/leave-requests/{created_id}/approve?{approve_qs}",
                jwt,
                None,
            )
            _bump(status)

            approve_qs = urllib.parse.urlencode({"role": "Employer", "note": "coverage"})
            status, _reason, _raw = _request(
                "PUT",
                f"{base}/api/leave-requests/{created_id}/approve?{approve_qs}",
                jwt,
                None,
            )
            _bump(status)

            reject_qs = urllib.parse.urlencode({"role": "Employer", "reason": "coverage"})
            status, _reason, _raw = _request(
                "PUT",
                f"{base}/api/leave-requests/{created_id}/reject?{reject_qs}",
                jwt,
                None,
            )
            _bump(status)

            cancel_qs = urllib.parse.urlencode({"observation": "coverage"})
            status, _reason, _raw = _request(
                "PUT",
                f"{base}/api/leave-requests/{created_id}/cancel?{cancel_qs}",
                jwt,
                None,
            )
            _bump(status)

    return {
        "service": service.name,
        "attempted": attempted,
        "ok_2xx": ok,
        "status_counts": dict(sorted(by_status.items(), key=lambda kv: kv[0])),
    }


def main() -> int:
    project_dir = Path(__file__).resolve().parent

    jwt = os.getenv("TEST_JWT_TOKEN", "").strip()
    auth_base = os.getenv("AUTH_BASE_URL", "http://127.0.0.1:9000").strip()
    leave_base = os.getenv("LEAVE_BASE_URL", "http://127.0.0.1:9001").strip()

    # Prefer an admin JWT if we can obtain one; this unlocks /api/admin/* endpoints.
    test_email = os.getenv("TEST_USER_EMAIL", "admin@test.com").strip() or "admin@test.com"
    test_password = os.getenv("TEST_USER_PASSWORD", "admin123").strip() or "admin123"
    admin_jwt = _try_login_for_jwt(auth_base, test_email, test_password)
    if admin_jwt:
        jwt = admin_jwt
        print(f"[coverage_booster] Logged in as {test_email}; using fresh JWT")
    else:
        if jwt:
            print("[coverage_booster] Login failed; using existing TEST_JWT_TOKEN")
        else:
            print("[coverage_booster] Login failed and TEST_JWT_TOKEN missing; calls will likely be 401/403")

    services = [
        ServiceSpec("auth", auth_base, project_dir / "examples" / "sample_swagger1.json"),
        ServiceSpec("leave", leave_base, project_dir / "examples" / "sample_swagger2.json"),
    ]

    results = []
    for svc in services:
        if not svc.spec_path.exists():
            print(f"[coverage_booster] Missing spec: {svc.spec_path}")
            continue
        print(f"[coverage_booster] Hitting {svc.name} endpoints from {svc.spec_path.name} @ {svc.base_url}")
        results.append(run_service(svc, jwt))

    print("[coverage_booster] Summary:")
    for r in results:
        print(
            f"  - {r['service']}: attempted={r['attempted']} ok_2xx={r['ok_2xx']} statuses={r['status_counts']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
