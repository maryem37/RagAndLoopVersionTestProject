from types import SimpleNamespace
from pathlib import Path

def get_settings():
    base_dir = Path(__file__).parent.parent  # project root

    return SimpleNamespace(
        ollama=SimpleNamespace(
            base_url="http://localhost:11434",
            model="mistral"  # ✅ Changed from "mistral" to "llama3.2"
        ),
        gherkin=SimpleNamespace(
            use_gherkin_lint=True
        ),
        paths=SimpleNamespace(
            features_dir=base_dir / "features",   # folder for .feature files
            tests_dir=base_dir / "tests"          # folder to save generated test files
        )
    )