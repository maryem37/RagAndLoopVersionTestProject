"""tools/llm_tools.py

Exemples de "tools" LangChain (@tool) adaptés à ce projet.

But:
- Exposer des infos déjà présentes dans `config/services_matrix.yaml`
  via `tools.service_registry.get_service_registry()`.

Remarque:
- Ces tools sont utilisables directement (Python) via `.invoke(...)`.
- Pour que le LLM les appelle automatiquement (tool-calling), il faut un
  modèle/client qui supporte `tool_calls` (pas le cas du wrapper Groq actuel).
"""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool

from tools.service_registry import get_service_registry


@tool
def list_enabled_services() -> List[str]:
    """Retourne la liste des microservices activés dans services_matrix.yaml."""
    registry = get_service_registry()
    return registry.get_service_names(enabled_only=True)


@tool
def get_service_config(service_name: str) -> Dict[str, Any]:
    """Retourne la config complète d'un service (base_url, swagger_url, deps...).

    Args:
        service_name: Nom du service (ex: "auth", "leave").

    Returns:
        Dictionnaire JSON-serializable.
    """
    registry = get_service_registry()
    return registry.get_service_config(service_name.strip().lower())


@tool
def get_service_base_url(service_name: str) -> str:
    """Retourne le base_url (ex: http://localhost:9000) d'un service."""
    registry = get_service_registry()
    service = registry.get_service(service_name.strip().lower())
    if service is None:
        raise ValueError(f"Service not found: {service_name}")
    return service.get_base_url()


@tool
def get_service_swagger_url(service_name: str) -> str:
    """Retourne l'URL Swagger/OpenAPI d'un service (si configurée)."""
    registry = get_service_registry()
    service = registry.get_service(service_name.strip().lower())
    if service is None:
        raise ValueError(f"Service not found: {service_name}")
    if not service.swagger_url:
        raise ValueError(f"No swagger_url configured for service: {service_name}")
    return str(service.swagger_url)
