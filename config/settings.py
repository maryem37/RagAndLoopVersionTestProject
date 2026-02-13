from types import SimpleNamespace
from pathlib import Path
from dotenv import load_dotenv
import os

def get_settings():
    base_dir = Path(__file__).parent.parent
    load_dotenv(base_dir / ".env")

    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

    return SimpleNamespace(
        huggingface=SimpleNamespace(
            api_token=hf_token,
            gherkin_generator=SimpleNamespace(
                model_name=os.getenv("HF_MODEL_GHERKIN_GENERATOR", "mistralai/Mistral-7B-Instruct-v0.2"),
                temperature=float(os.getenv("HF_TEMP_GHERKIN_GENERATOR", 0.2))
            ),
            gherkin_validator=SimpleNamespace(
                model_name=os.getenv("HF_MODEL_GHERKIN_VALIDATOR", "mistralai/Mistral-7B-Instruct-v0.2"),
                temperature=float(os.getenv("HF_TEMP_GHERKIN_VALIDATOR", 0.0))
            ),
            test_writer_agent=SimpleNamespace(
                model_name=os.getenv("HF_MODEL_TESTWRITER_AGENT", "google/gemma-2b-it"),
                temperature=float(os.getenv("HF_TEMP_TESTWRITER_AGENT", 0.2))
            )
        ),
        gherkin=SimpleNamespace(
            use_gherkin_lint=True,
            lint_config_file=base_dir / ".gherkin-lintrc"
        ),
        paths=SimpleNamespace(
            features_dir=base_dir / "features",
            tests_dir=base_dir / "tests"
        )
    )
