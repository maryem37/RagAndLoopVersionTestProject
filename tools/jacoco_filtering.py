"""
Shared JaCoCo exclusion rules for low-signal classes.

These exclusions intentionally remove data-model and bootstrap noise from
coverage reports so branch coverage reflects controller/service logic.
"""

from __future__ import annotations


JACOCO_REPORT_EXCLUDE_PATTERNS = (
    "**/dto/**",
    "**/dtos/**",
    "**/*Dto.class",
    "**/*Dto$*.class",
    "**/*DTO.class",
    "**/*DTO$*.class",
    "**/entity/**",
    "**/entities/**",
    "**/*Entity.class",
    "**/*Entity$*.class",
    "**/config/**",
    "**/configuration/**",
    "**/*Config.class",
    "**/*Config$*.class",
    "**/*Configuration.class",
    "**/*Configuration$*.class",
    "**/*Application.class",
    "**/*Application$*.class",
)

_LOW_SIGNAL_PACKAGE_SEGMENTS = frozenset(
    {"dto", "dtos", "entity", "entities", "config", "configuration"}
)
_LOW_SIGNAL_CLASS_SUFFIXES = (
    "dto",
    "entity",
    "config",
    "configuration",
    "application",
)


def jacoco_report_excludes_xml(indent: str = " " * 20) -> str:
    """Render a Maven JaCoCo <excludes> block with stable indentation."""
    lines = [f"{indent}<excludes>"]
    item_indent = f"{indent}    "
    for pattern in JACOCO_REPORT_EXCLUDE_PATTERNS:
        lines.append(f"{item_indent}<exclude>{pattern}</exclude>")
    lines.append(f"{indent}</excludes>")
    return "\n".join(lines)


def _normalize_path(value: str) -> str:
    return (value or "").replace("\\", "/").strip().strip("/")


def _package_segments(value: str) -> list[str]:
    normalized = _normalize_path(value).replace(".", "/").lower()
    return [segment for segment in normalized.split("/") if segment]


def _type_name(value: str) -> str:
    normalized = _normalize_path(value)
    if not normalized:
        return ""
    leaf = normalized.split("/")[-1]
    if leaf.endswith(".class"):
        leaf = leaf[:-6]
    elif leaf.endswith(".java"):
        leaf = leaf[:-5]
    return leaf.split("$", 1)[0].lower()


def is_low_signal_jacoco_class(
    class_name_or_path: str,
    package_name: str = "",
    source_file: str = "",
) -> bool:
    """Return True when a class should be excluded from branch coverage gates."""
    if any(
        segment in _LOW_SIGNAL_PACKAGE_SEGMENTS
        for segment in _package_segments(class_name_or_path)
    ):
        return True
    if any(
        segment in _LOW_SIGNAL_PACKAGE_SEGMENTS
        for segment in _package_segments(package_name)
    ):
        return True

    for candidate in (class_name_or_path, source_file):
        type_name = _type_name(candidate)
        if type_name.endswith(_LOW_SIGNAL_CLASS_SUFFIXES):
            return True

    return False
