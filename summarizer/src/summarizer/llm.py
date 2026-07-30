"""Lớp gọi LLM có structured output và retry.

Dùng `chat.completions.parse` với response_format là một Pydantic model để
không phải viết code vá JSON hỏng. Model draft cố tình hẹp — xem `schemas.py`.
"""

from __future__ import annotations

import functools
from typing import Protocol, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from summarizer.config import settings

DraftT = TypeVar("DraftT", bound=BaseModel)

# Chỉ retry lỗi tạm thời. Sai API key hoặc sai schema thì retry vô nghĩa và chỉ
# làm chậm việc phát hiện lỗi.
TRANSIENT = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)


class StructuredLLM(Protocol):
    def parse(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[DraftT],
        temperature: float,
    ) -> DraftT: ...


class EmptyCompletionError(RuntimeError):
    """Model trả về nội dung rỗng hoặc từ chối trả lời."""


class OpenAIStructuredLLM:
    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not settings.openai_api_key:
                raise RuntimeError(
                    "Thiếu OPENAI_API_KEY. Điền vào .env ở gốc repo "
                    "(xem vector-db/.env.example)."
                )
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
                timeout=settings.request_timeout_seconds,
                max_retries=0,  # retry do tenacity lo, tránh nhân đôi backoff
            )
        return self._client

    def parse(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[DraftT],
        temperature: float,
    ) -> DraftT:
        @retry(
            retry=retry_if_exception_type(TRANSIENT),
            wait=wait_exponential(multiplier=2, min=2, max=60),
            stop=stop_after_attempt(settings.max_retries),
            reraise=True,
        )
        def _call() -> DraftT:
            completion = self.client.chat.completions.parse(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=schema,
            )
            message = completion.choices[0].message
            if getattr(message, "refusal", None):
                raise EmptyCompletionError(f"Model từ chối trả lời: {message.refusal}")
            if message.parsed is None:
                raise EmptyCompletionError("Model trả về nội dung rỗng")
            return message.parsed

        return _call()


@functools.lru_cache(maxsize=8)
def _encoding_for(model: str):
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Đếm token thật, dùng cho báo cáo build và cảnh báo section quá dài."""

    return len(_encoding_for(model).encode(text))
