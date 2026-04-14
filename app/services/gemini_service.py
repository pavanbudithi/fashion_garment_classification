import io
import json
import re
from typing import Any

import google.generativeai as genai
from PIL import Image
from pydantic import ValidationError

from app.core.config import Settings
from app.exceptions import AIStructuredOutputError
from app.schemas.garment import ClassificationPayload


CLASSIFICATION_SYSTEM = """You are a fashion design assistant. Analyze garment and street-style images.
Return ONLY valid JSON (no markdown fences, no commentary) with this exact structure:
{
  "description": "rich natural-language description of the outfit and scene",
  "garment_type": "e.g. dress, blazer, sneakers",
  "style": "e.g. minimalist, streetwear, bohemian",
  "material": "inferred dominant materials or textures",
  "color_palette": ["#RRGGBB or color name", "..."],
  "pattern": "e.g. solid, stripes, floral",
  "season": "spring|summer|fall|winter|transitional|unknown",
  "occasion": "e.g. casual, formal, athletic",
  "consumer_profile": "short demographic / psychographic hint if inferable, else null",
  "trend_notes": "short trend or detail notes",
  "location_context": { "continent": null, "country": null, "city": null },
  "time_context": { "year": null, "month": null, "season": null },
  "designer": null
}
Use null for unknown fields. Infer location/time only if visible (signage, architecture, EXIF not available)."""


def _safe_response_text(response: Any) -> str:
    try:
        return (response.text or "").strip()
    except (ValueError, AttributeError):
        chunks: list[str] = []
        for cand in response.candidates or []:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) if content else None
            if not parts:
                continue
            for part in parts:
                t = getattr(part, "text", None)
                if t:
                    chunks.append(t)
        return "\n".join(chunks).strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIStructuredOutputError("No JSON object found in model response")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise AIStructuredOutputError("Model response contained invalid JSON") from e


def _normalize_payload(raw: dict[str, Any]) -> ClassificationPayload:
    if "description" in raw and raw["description"] is not None:
        raw = {**raw, "description": str(raw["description"]).strip()}
    return ClassificationPayload.model_validate(raw)


def classify_garment_image(
    settings: Settings, image_bytes: bytes, mime_type: str
) -> tuple[ClassificationPayload, str]:
    """
    Call Gemini multimodal model; return normalized payload and raw response text.
    """
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    try:
        pil = Image.open(io.BytesIO(image_bytes))
    except OSError as e:
        raise ValueError("Could not decode image bytes") from e

    response = model.generate_content([CLASSIFICATION_SYSTEM, pil])
    raw_text = _safe_response_text(response)
    data = _extract_json_object(raw_text)
    try:
        payload = _normalize_payload(data)
    except ValidationError as e:
        raise AIStructuredOutputError(f"Model JSON failed validation: {e}") from e
    return payload, raw_text
