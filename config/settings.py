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
import sys
import functools
from loguru import logger


# ==============================
# Windows UTF-8 Logging Configuration
# ==============================

def _configure_windows_logging():
    """
    Configure loguru for Windows to avoid UnicodeEncodeError.
    Remove default handler and use ASCII-safe format on Windows.
    """
    if sys.platform == "win32":
        logger.remove()  # Remove default handler
        
        # Use format without emoji and unicode characters
        log_format = (
            "<level>{level: <8}</level> | "
            "{name:40} | "
            "{message}"
        )
        
        logger.add(
            sys.stderr,
            format=log_format,
            level="INFO",
            colorize=False,  # No colors on Windows to avoid encoding issues
            backtrace=True,
            diagnose=False,
        )


# Apply Windows logging fix immediately on import
_configure_windows_logging()


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

    llm_provider = (
        os.getenv("LLM_PROVIDER")
        or ("groq" if os.getenv("GROQ_API_KEY") else "huggingface")
    ).strip().lower()

    groq_api_key = os.getenv("GROQ_API_KEY")
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

    if llm_provider == "groq":
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not set in .env")
        llm_api_key = groq_api_key
        llm_base_url = os.getenv("GROQ_API_BASE_URL", "https://api.groq.com/openai/v1")
    elif llm_provider == "huggingface":
        if not hf_token:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not set in .env")
        llm_api_key = hf_token
        llm_base_url = ""
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {llm_provider}")

    # Import ServiceRegistry
    from tools.service_registry import get_service_registry
    registry = get_service_registry()
    registry.validate_configuration()

    return SimpleNamespace(

        # ================= SERVICE REGISTRY =================
        service_registry=registry,
        
        # ================= AI CONFIG =================
        llm=SimpleNamespace(
            provider=llm_provider,
            api_key=llm_api_key,
            base_url=llm_base_url,

            scenario_designer=SimpleNamespace(
                model_name=os.getenv(
                    "LLM_MODEL_SCENARIO_DESIGNER",
                    os.getenv(
                        "GROQ_MODEL_SCENARIO_DESIGNER",
                        "llama-3.3-70b-versatile"
                    ) if llm_provider == "groq" else os.getenv(
                        "HF_MODEL_SCENARIO_DESIGNER",
                        "Qwen/Qwen2.5-Coder-32B-Instruct"
                    )
                ),
                temperature=float(os.getenv(
                    "LLM_TEMP_SCENARIO_DESIGNER",
                    os.getenv("HF_TEMP_SCENARIO_DESIGNER", 0.1)
                )),
                max_completion_tokens=int(os.getenv("LLM_MAXTOK_SCENARIO_DESIGNER", 2500)),
            ),

            gherkin_generator=SimpleNamespace(
                model_name=os.getenv(
                    "LLM_MODEL_GHERKIN_GENERATOR",
                    os.getenv(
                        "GROQ_MODEL_GHERKIN_GENERATOR",
                        "llama-3.3-70b-versatile"
                    ) if llm_provider == "groq" else os.getenv(
                        "HF_MODEL_GHERKIN_GENERATOR",
                        "Qwen/Qwen2.5-Coder-32B-Instruct"
                    )
                ),
                temperature=float(os.getenv(
                    "LLM_TEMP_GHERKIN_GENERATOR",
                    os.getenv("HF_TEMP_GHERKIN_GENERATOR", 0.2)
                )),
                max_completion_tokens=int(os.getenv("LLM_MAXTOK_GHERKIN_GENERATOR", 2000)),
            ),

            gherkin_validator=SimpleNamespace(
                model_name=os.getenv(
                    "LLM_MODEL_GHERKIN_VALIDATOR",
                    os.getenv(
                        "GROQ_MODEL_GHERKIN_VALIDATOR",
                        "llama-3.1-8b-instant"
                    ) if llm_provider == "groq" else os.getenv(
                        "HF_MODEL_GHERKIN_VALIDATOR",
                        "mistralai/Mistral-7B-Instruct-v0.2"
                    )
                ),
                temperature=float(os.getenv(
                    "LLM_TEMP_GHERKIN_VALIDATOR",
                    os.getenv("HF_TEMP_GHERKIN_VALIDATOR", 0.0)
                )),
                max_completion_tokens=int(os.getenv("LLM_MAXTOK_GHERKIN_VALIDATOR", 1024)),
            ),

            test_writer_agent=SimpleNamespace(
                model_name=os.getenv(
                    "LLM_MODEL_TESTWRITER_AGENT",
                    os.getenv(
                        "GROQ_MODEL_TESTWRITER_AGENT",
                        "llama-3.3-70b-versatile"
                    ) if llm_provider == "groq" else os.getenv(
                        "HF_MODEL_TESTWRITER_AGENT",
                        "Qwen/Qwen2.5-Coder-7B-Instruct"
                    )
                ),
                temperature=float(os.getenv(
                    "LLM_TEMP_TESTWRITER_AGENT",
                    os.getenv("HF_TEMP_TESTWRITER_AGENT", 0.2)
                )),
                max_completion_tokens=int(os.getenv("LLM_MAXTOK_TESTWRITER_AGENT", 2048)),
            ),
        ),

        huggingface=SimpleNamespace(
            api_token=hf_token,

            scenario_designer=SimpleNamespace(
                model_name=os.getenv(
                    "HF_MODEL_SCENARIO_DESIGNER",
                    "Qwen/Qwen2.5-Coder-32B-Instruct"
                ),
                temperature=float(os.getenv("HF_TEMP_SCENARIO_DESIGNER", 0.1))
            ),

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
