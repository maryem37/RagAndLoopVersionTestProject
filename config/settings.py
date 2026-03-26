# from types import SimpleNamespace
# from pathlib import Path
# from dotenv import load_dotenv
# import os

# def get_settings():
#     base_dir = Path(__file__).parent.parent
#     load_dotenv(base_dir / ".env")

#     hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

#     return SimpleNamespace(
#         huggingface=SimpleNamespace(
#             api_token=hf_token,
#             gherkin_generator=SimpleNamespace(
#                 model_name=os.getenv("HF_MODEL_GHERKIN_GENERATOR", "mistralai/Mistral-7B-Instruct-v0.2"),
#                 temperature=float(os.getenv("HF_TEMP_GHERKIN_GENERATOR", 0.2))
#             ),
#             gherkin_validator=SimpleNamespace(
#                 model_name=os.getenv("HF_MODEL_GHERKIN_VALIDATOR", "mistralai/Mistral-7B-Instruct-v0.2"),
#                 temperature=float(os.getenv("HF_TEMP_GHERKIN_VALIDATOR", 0.0))
#             ),
#             test_writer_agent=SimpleNamespace(
#                 model_name=os.getenv("HF_MODEL_TESTWRITER_AGENT", "Qwen/Qwen2.5-Coder-7B-Instruct"),
#                 temperature=float(os.getenv("HF_TEMP_TESTWRITER_AGENT", 0.2))
#             )
#         ),
#         gherkin=SimpleNamespace(
#             use_gherkin_lint=True,
#             lint_config_file=base_dir / ".gherkin-lintrc"
#         ),
#         paths=SimpleNamespace(
#             features_dir=base_dir / "features",
#             tests_dir=base_dir / "tests"
#         )
#     )


"""
Configuration Settings for Test Automation System
Now uses ServiceRegistry for dynamic microservice configuration
"""

from types import SimpleNamespace
from pathlib import Path
from dotenv import load_dotenv
import os
import functools
from loguru import logger


@functools.lru_cache(maxsize=1)
def get_settings():
    base_dir = Path(__file__).parent.parent
    env_file = base_dir / ".env"

    # Load .env
    if env_file.exists():
        load_dotenv(env_file)
    else:
        raise FileNotFoundError(
            f".env file not found at {env_file}. "
            f"Create it from .env.example."
        )

    # Hugging Face token
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not hf_token:
        raise ValueError("HUGGINGFACEHUB_API_TOKEN not set in .env")

    # Import ServiceRegistry
    from tools.service_registry import get_service_registry
    registry = get_service_registry()
    registry.validate_configuration()

    return SimpleNamespace(

        # ================= SERVICE REGISTRY =================
        service_registry=registry,
        
        # ================= AI CONFIG =================
        huggingface=SimpleNamespace(
            api_token=hf_token,

            gherkin_generator=SimpleNamespace(
                model_name=os.getenv(
                    "HF_MODEL_GHERKIN_GENERATOR",
                    "Qwen/Qwen2.5-Coder-32B-Instruct"
                ),
                temperature=float(os.getenv("HF_TEMP_GHERKIN_GENERATOR", 0.2))
            ),

            gherkin_validator=SimpleNamespace(
                model_name=os.getenv(
                    "HF_MODEL_GHERKIN_VALIDATOR",
                    "mistralai/Mistral-7B-Instruct-v0.2"
                ),
                temperature=float(os.getenv("HF_TEMP_GHERKIN_VALIDATOR", 0.0))
            ),

            test_writer_agent=SimpleNamespace(
                model_name=os.getenv(
                    "HF_MODEL_TESTWRITER_AGENT",
                    "Qwen/Qwen2.5-Coder-7B-Instruct"
                ),
                temperature=float(os.getenv("HF_TEMP_TESTWRITER_AGENT", 0.2))
            )
        ),

        # ================= PATHS =================
        paths=SimpleNamespace(
            base_dir=base_dir,
            features_dir=base_dir / "output" / "features",
            tests_dir=base_dir / "output" / "tests",
            output_dir=base_dir / "output",
            reports_dir=base_dir / "output" / "reports",
            pom_source=base_dir / "output" / "tests" / "pom.xml"
        ),

        # ================= DYNAMIC SERVICES (from ServiceRegistry) =================
        # Instead of hardcoding auth_port and leave_port, use registry
        backend=SimpleNamespace(
            # Will be accessed dynamically via registry
            registry=registry
        ),

        # ================= TEST EXECUTION =================
        test_execution=SimpleNamespace(
            jwt_token=os.getenv("TEST_JWT_TOKEN"),
            cucumber_tags=os.getenv("CUCUMBER_TAGS", "@contract"),
            test_timeout=int(os.getenv("TEST_TIMEOUT", 300))
        )
    )
