from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib import request
from urllib.parse import urlparse


class AgentProvider(Protocol):
    def select_plan(self, compact_state: Mapping[str, Any], plans: list[Mapping[str, Any]]) -> dict[str, Any]: ...
    def status(self) -> dict[str, Any]: ...


class DeterministicMockProvider:
    """Zero-network provider used by the one-click product demo and tests."""

    def select_plan(self, compact_state: Mapping[str, Any], plans: list[Mapping[str, Any]]) -> dict[str, Any]:
        selected = str(plans[0].get("plan_id")) if plans else ""
        return {
            "selected_plan_id": selected,
            "rationale": "Deterministic ranking selected the highest-scoring safety-cleared plan.",
            "provider": "mock",
            "llm_calls": 0,
        }

    def status(self) -> dict[str, Any]:
        return {
            "provider": "mock",
            "ready": True,
            "network_required": False,
            "note": "All unambiguous planning work is deterministic; the local LLM is optional for semantic selection and explanation.",
        }


class LlamaServerProvider:
    """Compact localhost-only client for a persistent llama.cpp llama-server."""

    def __init__(self, endpoint: str, cache_path: Path, timeout_seconds: float = 45.0) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The llama-server provider is restricted to localhost.")
        self.endpoint = endpoint.rstrip("/")
        self.cache_path = cache_path
        self.timeout_seconds = timeout_seconds
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            value = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _save_cache(self, cache: Mapping[str, Any]) -> None:
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.cache_path)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}

    def select_plan(self, compact_state: Mapping[str, Any], plans: list[Mapping[str, Any]]) -> dict[str, Any]:
        allowed_ids = [str(item.get("plan_id")) for item in plans]
        prompt = json.dumps(
            {
                "task": "Select one already safety-cleared energy plan. Return JSON only: selected_plan_id, rationale. /no_think",
                "state": compact_state,
                "plans": [
                    {
                        "plan_id": item.get("plan_id"),
                        "score": item.get("score"),
                        "expected_reduction_kva": item.get("expected_reduction_kva"),
                        "action_count": len(list(item.get("actions") or [])),
                        "mean_confidence": item.get("mean_confidence"),
                        "disruption_score": item.get("disruption_score"),
                    }
                    for item in plans
                ],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cache = self._cache()
        if key in cache:
            return {**dict(cache[key]), "provider": "llama_server", "cache_hit": True, "llm_calls": 0}
        payload = {
            "model": "local-agent",
            "messages": [
                {"role": "system", "content": "You are SIMBA's constrained semantic planner. Never invent actions or alter safety calculations. /no_think"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "top_p": 0.8,
            "presence_penalty": 1.5,
            "max_tokens": 160,
            "response_format": {"type": "json_object"},
        }
        http_request = request.Request(
            f"{self.endpoint}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            document = json.loads(response.read().decode("utf-8"))
        content = str(document["choices"][0]["message"]["content"])
        result = self._parse_json(content)
        if str(result.get("selected_plan_id")) not in allowed_ids:
            raise ValueError("llama-server selected a plan outside the deterministic candidate set.")
        compact_result = {
            "selected_plan_id": str(result["selected_plan_id"]),
            "rationale": str(result.get("rationale") or "Local semantic selection."),
        }
        cache[key] = compact_result
        self._save_cache(cache)
        return {**compact_result, "provider": "llama_server", "cache_hit": False, "llm_calls": 1}

    def status(self) -> dict[str, Any]:
        return {
            "provider": "llama_server",
            "ready": True,
            "endpoint": self.endpoint,
            "network_required": False,
            "cache_path": str(self.cache_path),
        }


def build_provider(config: Mapping[str, Any], runtime_dir: Path) -> AgentProvider:
    requested = str(os.getenv("SIMBA_AGENT_PROVIDER") or config.get("default") or "mock").strip().lower()
    if requested == "llama_server":
        endpoint = str(os.getenv("SIMBA_LLAMA_SERVER_URL") or config.get("llama_server_url") or "http://127.0.0.1:8081")
        return LlamaServerProvider(endpoint, runtime_dir / "llm_response_cache.json")
    return DeterministicMockProvider()
