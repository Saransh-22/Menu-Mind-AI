"""
Centralized Gemini Service Provider for MenuMind AI.
Standardizes LLM communication, native tool calling, structured JSON output,
model fallback, retries, and telemetry across all agents.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_CHAT_MODEL,
    GEMINI_VISION_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS,
    AGENT_MAX_TOOL_CALLS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Known active models verified against current Gemini API
VERIFIED_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
]


class GeminiService:
    """Central singleton provider for Google GenAI interactions."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        if not self.api_key:
            logger.warning("GeminiService initialized without GEMINI_API_KEY.")
            return
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info("GeminiService: Client initialized successfully.")
        except Exception as exc:
            logger.error("Failed to initialize google.genai client: %s", exc)
            self.client = None

    def is_available(self) -> bool:
        return bool(self.client and self.api_key)

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        retries: int = 2,
    ) -> str:
        """
        Generate natural language content with automatic model fallback & retry logic.
        """
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured or client failed to initialize.")

        selected_model = model or GEMINI_MODEL
        temp = temperature if temperature is not None else GEMINI_TEMPERATURE
        max_tokens = max_output_tokens or GEMINI_MAX_OUTPUT_TOKENS

        config = {
            "temperature": temp,
            "max_output_tokens": max_tokens,
        }
        if system_instruction:
            config["system_instruction"] = system_instruction

        # Attempt with fallback models on 404 or 503
        model_candidates = [selected_model] + [m for m in VERIFIED_MODELS if m != selected_model]

        last_error = None
        for candidate in model_candidates:
            for attempt in range(retries + 1):
                try:
                    logger.debug("Generating content with model: %s (attempt %d)", candidate, attempt + 1)
                    response = self.client.models.generate_content(
                        model=candidate,
                        contents=prompt,
                        config=config,
                    )
                    if response and response.text:
                        return response.text.strip()
                    return ""
                except Exception as exc:
                    last_error = exc
                    err_msg = str(exc)
                    logger.warning("Gemini call failed on %s (attempt %d): %s", candidate, attempt + 1, err_msg[:120])
                    # If 404 model not found or 429 quota exhausted, break to try next candidate model
                    if "404" in err_msg or "NOT_FOUND" in err_msg or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        break
                    # If 503 high demand, short backoff and retry
                    if "503" in err_msg or "UNAVAILABLE" in err_msg:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    break

        raise RuntimeError(f"Gemini generation failed across candidate models. Error: {last_error}")

    def generate_json(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
    ) -> T:
        """
        Generate structured JSON output validated against a Pydantic schema.
        """
        if not self.is_available():
            raise RuntimeError("Gemini API is not configured.")

        # Enrich system instruction with JSON enforcement
        sys_inst = (system_instruction or "") + "\n\nCRITICAL: Respond ONLY with a valid, raw JSON object matching the requested schema. Do not enclose in markdown ```json blocks."

        raw_text = self.generate_content(
            prompt=prompt,
            system_instruction=sys_inst.strip(),
            model=model or GEMINI_MODEL,
            temperature=temperature,
        )

        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except Exception as exc:
            logger.error("JSON parsing or schema validation failed for text: %s. Error: %s", cleaned[:200], exc)
            raise ValueError(f"Failed to parse structured JSON from Gemini: {exc}")

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Multimodal analysis of food images, menus, or receipts.
        """
        if not self.is_available():
            raise RuntimeError("Gemini API is not configured.")

        from google.genai import types

        vision_model = model or GEMINI_VISION_MODEL
        candidates = [vision_model, "gemini-3.5-flash", "gemini-3-flash-preview"]

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ]

        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction

        last_err = None
        for cand in candidates:
            try:
                response = self.client.models.generate_content(
                    model=cand,
                    contents=contents,
                    config=config,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as exc:
                last_err = exc
                logger.warning("Vision analysis error on %s: %s", cand, exc)
                if "404" in str(exc):
                    continue

        raise RuntimeError(f"Vision analysis failed: {last_err}")


# Global Singleton Instance
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Retrieve or create the global GeminiService instance."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
