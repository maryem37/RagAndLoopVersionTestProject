"""
Swagger/OpenAPI Parser Tools
Provides utilities for loading and extracting API context from Swagger specifications
Supports both single and multi-service architectures
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Optional

from loguru import logger


def load_swagger_file(file_path: str) -> Dict:
    """
    Load a Swagger/OpenAPI specification from JSON or YAML file.
    
    Args:
        file_path: Path to the Swagger spec file (.json, .yaml, or .yml)
    
    Returns:
        Dictionary containing the parsed Swagger specification
    
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Swagger file not found: {file_path}")
    
    logger.info(f"📄 Loading Swagger spec: {path.name}")
    
    if path.suffix in ['.yaml', '.yml']:
        with open(path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
    elif path.suffix == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .json, .yaml, or .yml")
    
    # Log basic info
    info = spec.get("info", {})
    paths_count = len(spec.get("paths", {}))
    logger.info(f"   Title: {info.get('title', 'N/A')}")
    logger.info(f"   Version: {info.get('version', 'N/A')}")
    logger.info(f"   Endpoints: {paths_count}")
    
    return spec


def get_api_context(swagger_spec: Optional[Dict]) -> str:
    """
    Extract API context from a single Swagger specification.
    
    Args:
        swagger_spec: Swagger/OpenAPI specification dictionary
    
    Returns:
        Formatted string containing API endpoints and details
    """
    if not swagger_spec or "paths" not in swagger_spec:
        return "No API specification provided"
    
    context = []
    
    # Add server information
    servers = swagger_spec.get("servers", [])
    if servers:
        base_url = servers[0].get("url", "")
        context.append(f"Base URL: {base_url}")
        context.append("")
    
    # Add API title/info
    info = swagger_spec.get("info", {})
    if info.get("title"):
        context.append(f"API: {info['title']}")
        context.append("")
    
    # Add endpoints
    context.append("ENDPOINTS:")
    for path, methods in swagger_spec.get("paths", {}).items():
        for method, details in methods.items():
            operation_id = details.get("operationId", "N/A")
            summary = details.get("summary", "")
            
            context.append(f"\n{method.upper()} {path}")
            context.append(f"  Operation: {operation_id}")
            if summary:
                context.append(f"  Summary: {summary}")
            
            # Add parameters
            if "parameters" in details:
                context.append("  Parameters:")
                for param in details["parameters"]:
                    param_name = param.get("name", "")
                    param_in = param.get("in", "")
                    param_required = "required" if param.get("required") else "optional"
                    context.append(f"    - {param_name} ({param_in}, {param_required})")
            
            # Add request body info
            if "requestBody" in details:
                content_types = list(details["requestBody"].get("content", {}).keys())
                if content_types:
                    context.append(f"  Request Body: {', '.join(content_types)}")
            
            # Add response info
            if "responses" in details:
                success_codes = [code for code in details["responses"].keys() if code.startswith("2")]
                if success_codes:
                    context.append(f"  Success: {', '.join(success_codes)}")
    
    return "\n".join(context)


def get_api_context_multi(swagger_specs: Dict[str, Dict]) -> str:
    """
    Convert multiple Swagger specifications into structured context for test generation.
    
    This function is critical for microservice architectures where tests need to
    interact with multiple APIs (e.g., Auth Service + Leave Service).
    
    Args:
        swagger_specs: Dictionary mapping service names to their Swagger specs
                      Example: {"auth": {...}, "leave": {...}}
    
    Returns:
        Formatted string containing all API endpoints organized by service
        
    Example Output:
        ===== SERVICE: AUTH =====
        Base URL: http://localhost:9000
        
        POST /api/auth/login
        OperationId: login
        Request Body: application/json
        
        ===== SERVICE: LEAVE =====
        Base URL: http://localhost:9001
        
        POST /api/employer/leave/request
        OperationId: createLeaveRequest
        ...
    """
    if not swagger_specs:
        return "No API specifications provided"
    
    logger.info(f"🔗 Building multi-service API context for {len(swagger_specs)} service(s)")
    
    context_parts = []
    
    for service_name, swagger_spec in swagger_specs.items():
        if not swagger_spec or "paths" not in swagger_spec:
            logger.warning(f"⚠️ Skipping invalid spec for service: {service_name}")
            continue
        
        # Service header
        context_parts.append(f"\n{'='*60}")
        context_parts.append(f"SERVICE: {service_name.upper()}")
        context_parts.append(f"{'='*60}")
        
        # Server/Base URL
        servers = swagger_spec.get("servers", [])
        if servers:
            base_url = servers[0].get("url", "")
            context_parts.append(f"Base URL: {base_url}")
            context_parts.append("")
        
        # API Info
        info = swagger_spec.get("info", {})
        if info.get("title"):
            context_parts.append(f"Title: {info['title']}")
        if info.get("version"):
            context_parts.append(f"Version: {info['version']}")
        context_parts.append("")
        
        # Endpoints
        context_parts.append("ENDPOINTS:")
        
        for path, methods in swagger_spec.get("paths", {}).items():
            for method, details in methods.items():
                context_parts.append("")
                context_parts.append(f"{method.upper()} {path}")
                
                # Operation ID
                operation_id = details.get("operationId", "N/A")
                context_parts.append(f"  OperationId: {operation_id}")
                
                # Summary
                summary = details.get("summary", "")
                if summary:
                    context_parts.append(f"  Summary: {summary}")
                
                # Parameters
                if "parameters" in details:
                    context_parts.append("  Parameters:")
                    for param in details["parameters"]:
                        param_name = param.get("name", "unknown")
                        param_in = param.get("in", "query")
                        param_required = param.get("required", False)
                        param_type = param.get("schema", {}).get("type", "string")
                        
                        required_text = "REQUIRED" if param_required else "optional"
                        context_parts.append(
                            f"    - {param_name} ({param_in}, {param_type}, {required_text})"
                        )
                
                # Request Body
                if "requestBody" in details:
                    content = details["requestBody"].get("content", {})
                    if content:
                        content_types = list(content.keys())
                        context_parts.append(f"  Request Body: {', '.join(content_types)}")
                        
                        # Try to get schema reference
                        for content_type, content_details in content.items():
                            schema = content_details.get("schema", {})
                            if "$ref" in schema:
                                ref = schema["$ref"].split("/")[-1]
                                context_parts.append(f"    Schema: {ref}")
                
                # Response Codes
                if "responses" in details:
                    responses = details["responses"]
                    success_codes = [code for code in responses.keys() if code.startswith("2")]
                    if success_codes:
                        context_parts.append(f"  Success Codes: {', '.join(success_codes)}")
                
                # Tags
                tags = details.get("tags", [])
                if tags:
                    context_parts.append(f"  Tags: {', '.join(tags)}")
        
        context_parts.append("")
    
    result = "\n".join(context_parts)
    
    logger.success(f"✅ Generated API context: {len(result)} characters")
    return result


def extract_endpoints_for_service(swagger_spec: Dict, service_name: str) -> list:
    """
    Extract all endpoints from a Swagger spec as a structured list.
    
    Args:
        swagger_spec: Swagger/OpenAPI specification
        service_name: Name of the service (for logging/identification)
    
    Returns:
        List of dictionaries containing endpoint details
    """
    endpoints = []
    
    if not swagger_spec or "paths" not in swagger_spec:
        return endpoints
    
    base_url = ""
    servers = swagger_spec.get("servers", [])
    if servers:
        base_url = servers[0].get("url", "")
    
    for path, methods in swagger_spec.get("paths", {}).items():
        for method, details in methods.items():
            endpoint = {
                "service": service_name,
                "base_url": base_url,
                "path": path,
                "method": method.upper(),
                "operation_id": details.get("operationId", ""),
                "summary": details.get("summary", ""),
                "parameters": [],
                "has_request_body": "requestBody" in details,
                "success_codes": []
            }
            
            # Extract parameters
            if "parameters" in details:
                for param in details["parameters"]:
                    endpoint["parameters"].append({
                        "name": param.get("name", ""),
                        "in": param.get("in", ""),
                        "required": param.get("required", False),
                        "type": param.get("schema", {}).get("type", "string")
                    })
            
            # Extract success response codes
            if "responses" in details:
                endpoint["success_codes"] = [
                    code for code in details["responses"].keys() 
                    if code.startswith("2")
                ]
            
            endpoints.append(endpoint)
    
    return endpoints


def validate_swagger_spec(swagger_spec: Dict) -> tuple[bool, list]:
    """
    Validate a Swagger specification for completeness.
    
    Args:
        swagger_spec: Swagger/OpenAPI specification dictionary
    
    Returns:
        Tuple of (is_valid: bool, issues: list of strings)
    """
    issues = []
    
    if not swagger_spec:
        return False, ["Swagger spec is None or empty"]
    
    # Check for required top-level fields
    if "openapi" not in swagger_spec and "swagger" not in swagger_spec:
        issues.append("Missing 'openapi' or 'swagger' version field")
    
    if "info" not in swagger_spec:
        issues.append("Missing 'info' section")
    
    if "paths" not in swagger_spec:
        issues.append("Missing 'paths' section")
    elif not swagger_spec["paths"]:
        issues.append("'paths' section is empty")
    
    # Check servers
    if "servers" not in swagger_spec or not swagger_spec["servers"]:
        issues.append("No server URLs defined")
    
    # Validate each path has methods
    paths = swagger_spec.get("paths", {})
    for path, methods in paths.items():
        if not methods:
            issues.append(f"Path '{path}' has no methods defined")
    
    is_valid = len(issues) == 0
    
    return is_valid, issues