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
Simple Configuration Settings for Test Automation System
"""

from types import SimpleNamespace
from pathlib import Path
from dotenv import load_dotenv
import os
import functools


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

    # Backend ports
    auth_port = int(os.getenv("AUTH_SERVICE_PORT", 9000))
    leave_port = int(os.getenv("LEAVE_SERVICE_PORT", 9001))

    return SimpleNamespace(

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
    pom_source=base_dir / "output" / "tests" / "pom.xml"   # ← ADD THIS
),

        # ================= BACKEND =================
        backend=SimpleNamespace(
            auth_service=SimpleNamespace(
                port=auth_port,
                base_url=f"http://localhost:{auth_port}",
                health="/actuator/health"
            ),
            leave_service=SimpleNamespace(
                port=leave_port,
                base_url=f"http://localhost:{leave_port}",
                health="/actuator/health"
            )
        ),

        # ================= DOCKER (OPTIONAL) =================
        docker=SimpleNamespace(
            use_docker=os.getenv("USE_DOCKER", "false").lower() == "true",
            compose_file=base_dir / "docker-compose.yml"
        ),

        # ================= TEST EXECUTION =================
        test_execution=SimpleNamespace(
            jwt_token=os.getenv("TEST_JWT_TOKEN"),
            cucumber_tags=os.getenv("CUCUMBER_TAGS", "@contract"),
            test_timeout=int(os.getenv("TEST_TIMEOUT", 300))
        )
    )
