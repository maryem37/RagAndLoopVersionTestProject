# tools/swagger_parser.py
#Lire Swagger → dictionnaire exploitable
import json
import yaml
from pathlib import Path
from typing import Dict

def load_swagger_file(file_path: str) -> Dict:
    """
    Load a Swagger/OpenAPI specification (JSON or YAML) and return as Python dict.
    """
    path = Path(file_path)  # use the parameter
    if not path.exists():
        raise FileNotFoundError(f"Swagger file not found: {file_path}")

    if path.suffix in ['.yaml', '.yml']:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    elif path.suffix == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise ValueError("Swagger file must be .json or .yaml")

def get_api_context(swagger_spec: Dict) -> str:
    """
    Convert Swagger spec into formatted string for Test Writer.
    """
    if not swagger_spec or "paths" not in swagger_spec:
        return "No API specification provided"

    context = "API ENDPOINTS:\n"
    for path, methods in swagger_spec.get("paths", {}).items():
        for method, details in methods.items():
            summary = details.get("summary", "")
            params = details.get("parameters", [])
            request_body = details.get("requestBody", {})
            responses = details.get("responses", {})

            context += f"\n{method.upper()} {path}\n"
            context += f"  Summary: {summary}\n"

            if params:
                context += "  Parameters:\n"
                for param in params:
                    param_type = param.get("schema", {}).get("type", "string")
                    context += f"    - {param.get('name')}: {param_type}\n"

            if request_body:
                schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
                context += f"  Request Body: {schema}\n"

            if responses:
                context += "  Responses:\n"
                for status, resp in responses.items():
                    desc = resp.get("description", "")
                    context += f"    {status}: {desc}\n"

    return context
