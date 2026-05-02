"""examples/demo_langchain_tools.py

Démonstration minimale de tools LangChain (@tool) adaptés à ce repo.

Exécution (PowerShell):
    ./.venv312/Scripts/python.exe ./examples/demo_langchain_tools.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from pprint import pprint

# Permet d'exécuter ce script depuis `examples/` tout en important `tools/`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

from tools.llm_tools import (
    list_enabled_services,
    get_service_config,
    get_service_base_url,
    get_service_swagger_url,
)


def main() -> None:
    # Appel direct d'un tool (sans LLM) via .invoke
    services = list_enabled_services.invoke({})
    print("Enabled services:")
    pprint(services)

    print("\nAuth base_url:")
    print(get_service_base_url.invoke({"service_name": "auth"}))

    print("\nLeave swagger_url:")
    print(get_service_swagger_url.invoke({"service_name": "leave"}))

    print("\nFull config for leave:")
    cfg = get_service_config.invoke({"service_name": "leave"})
    pprint(cfg)


if __name__ == "__main__":
    main()
