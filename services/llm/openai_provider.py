"""OpenAI chat completions provider."""

from __future__ import annotations

from openai import OpenAI

from services.llm.base import LLMProviderError


class OpenAILLMProvider:
    name = "openai"

    def __init__(self, api_key: str, *, model: str = "gpt-4o-mini") -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
            )
        except Exception as exc:
            raise LLMProviderError(f"OpenAI completion failed: {exc}") from exc
        content = response.choices[0].message.content
        if not content:
            raise LLMProviderError("OpenAI returned an empty response.")
        return content.strip()
