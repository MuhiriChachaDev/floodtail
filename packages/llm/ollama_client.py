"""Ollama HTTP client — chat at temp=0 with health + degrade flag."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 30.0


@dataclass
class OllamaStatus:
    available: bool
    host: str
    model: str
    detail: str = ""
    degraded: bool = False


@dataclass
class ChatResult:
    content: str
    model: str
    degraded: bool = False
    error: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


class OllamaClient:
    """Thin Ollama chat wrapper. Never invents numbers — callers validate."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5:3b-instruct",
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        temperature: float = 0.0,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.temperature = temperature
        self._degraded = False
        self._last_error: Optional[str] = None

    @property
    def degraded(self) -> bool:
        return self._degraded

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def mark_degraded(self, reason: str) -> None:
        self._degraded = True
        self._last_error = reason
        logger.warning("Ollama degraded: %s", reason)

    def health(self) -> OllamaStatus:
        """Probe Ollama tags endpoint; sets degrade flag when down."""
        try:
            with httpx.Client(timeout=min(5.0, self.timeout_s)) as client:
                r = client.get(f"{self.host}/api/tags")
                r.raise_for_status()
                names = [m.get("name", "") for m in r.json().get("models", [])]
                has_model = any(
                    self.model == n or n.startswith(self.model.split(":")[0]) for n in names
                )
                detail = "ok" if has_model else f"reachable; model {self.model!r} may be missing"
                self._degraded = False
                self._last_error = None
                return OllamaStatus(
                    available=True,
                    host=self.host,
                    model=self.model,
                    detail=detail,
                    degraded=False,
                )
        except Exception as exc:  # noqa: BLE001
            self.mark_degraded(str(exc))
            return OllamaStatus(
                available=False,
                host=self.host,
                model=self.model,
                detail=str(exc),
                degraded=True,
            )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> ChatResult:
        """
        Chat completion. On failure returns empty content with degraded=True
        (callers must fall back to templates).
        """
        payload_messages: list[dict[str, str]] = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        body = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "options": {"temperature": self.temperature if temperature is None else temperature},
        }
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.post(f"{self.host}/api/chat", json=body)
                r.raise_for_status()
                data = r.json()
            content = str((data.get("message") or {}).get("content") or "").strip()
            self._degraded = False
            self._last_error = None
            return ChatResult(content=content, model=self.model, raw=data)
        except Exception as exc:  # noqa: BLE001
            self.mark_degraded(str(exc))
            return ChatResult(
                content="",
                model=self.model,
                degraded=True,
                error=str(exc),
            )


_default_client: Optional[OllamaClient] = None


def get_ollama_client(
    host: str = "http://localhost:11434",
    model: str = "qwen2.5:3b-instruct",
    *,
    force_new: bool = False,
) -> OllamaClient:
    global _default_client
    if force_new or _default_client is None:
        _default_client = OllamaClient(host=host, model=model)
        return _default_client
    if host != _default_client.host or model != _default_client.model:
        return OllamaClient(host=host, model=model)
    return _default_client


def reset_ollama_client() -> None:
    global _default_client
    _default_client = None
