"""
Shared chat model factory for LLM-backed agents.

Supports:
- Groq via its OpenAI-compatible chat completions API

The returned object is a LangChain Runnable so existing `prompt | llm`
pipelines continue to work.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

import os
import requests
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda


_USAGE_TRACKER: Dict[str, int] = {
    "calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
}


def reset_usage_tracker() -> None:
    for key in list(_USAGE_TRACKER.keys()):
        _USAGE_TRACKER[key] = 0


def get_usage_tracker_snapshot() -> Dict[str, int]:
    return dict(_USAGE_TRACKER)


def _safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except Exception:
        return 0


def _extract_usage(data: Dict[str, Any]) -> Dict[str, int]:
    usage = data.get("usage", {}) if isinstance(data, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    prompt_tokens = _safe_int(usage.get("prompt_tokens"))
    completion_tokens = _safe_int(usage.get("completion_tokens"))
    total_tokens = _safe_int(usage.get("total_tokens")) or (prompt_tokens + completion_tokens)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _record_usage(usage: Dict[str, int]) -> None:
    _USAGE_TRACKER["calls"] += 1
    _USAGE_TRACKER["prompt_tokens"] += _safe_int(usage.get("prompt_tokens"))
    _USAGE_TRACKER["completion_tokens"] += _safe_int(usage.get("completion_tokens"))
    _USAGE_TRACKER["total_tokens"] += _safe_int(usage.get("total_tokens"))


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: List[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    chunks.append(str(item.get("text", "")))
                else:
                    chunks.append(str(item))
            else:
                chunks.append(str(item))
        return "".join(chunks)
    return str(content)


def _to_openai_messages(prompt_value: Any) -> List[Dict[str, str]]:
    if hasattr(prompt_value, "to_messages"):
        messages: Iterable[Any] = prompt_value.to_messages()
    elif isinstance(prompt_value, list):
        messages = prompt_value
    else:
        messages = [prompt_value]

    converted: List[Dict[str, str]] = []
    for message in messages:
        role = getattr(message, "type", None) or getattr(message, "role", None) or "user"
        if role == "human":
            role = "user"
        elif role == "ai":
            role = "assistant"

        content = _content_to_text(getattr(message, "content", message))
        converted.append({"role": str(role), "content": content})
    return converted


def _build_groq_model(
    *,
    api_key: str,
    model_name: str,
    temperature: float,
    max_completion_tokens: int,
    base_url: str,
) -> RunnableLambda:
    endpoint = base_url.rstrip("/") + "/chat/completions"

    def _http_timeout_s() -> float:
        raw = (os.getenv("LLM_HTTP_TIMEOUT_S") or "").strip()
        if not raw:
            return 60.0
        try:
            return max(5.0, float(raw))
        except Exception:
            return 60.0

    def _invoke(prompt_value: Any) -> AIMessage:
        payload = {
            "model": model_name,
            "messages": _to_openai_messages(prompt_value),
            "temperature": max(float(temperature), 1e-8),
            "max_completion_tokens": int(max_completion_tokens),
        }
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=_http_timeout_s(),
        )
        response.raise_for_status()
        data = response.json()
        usage = _extract_usage(data)
        _record_usage(usage)
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return AIMessage(
            content=str(content),
            response_metadata={
                "model_name": model_name,
                "usage": usage,
            },
            usage_metadata={
                "input_tokens": usage["prompt_tokens"],
                "output_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
            },
        )

    return RunnableLambda(_invoke)


def create_chat_model(
    *,
    provider: str,
    api_key: str,
    model_name: str,
    temperature: float,
    max_completion_tokens: int,
    base_url: str,
):
    provider = (provider or "").strip().lower()
    if provider == "groq":
        return _build_groq_model(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            base_url=base_url,
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")
