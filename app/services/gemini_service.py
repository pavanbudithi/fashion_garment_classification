import io
import json
import re
from typing import Any

from google import genai
from google.genai import types
from PIL import Image
from pydantic import ValidationError

from app.core.config import Settings
from app.exceptions import AIStructuredOutputError
from app.schemas.garment import ClassificationPayload


GARMENT_LABELS = [
    "t-shirt",
    "shirt",
    "blouse",
    "top",
    "hoodie",
    "sweatshirt",
    "jacket",
    "blazer",
    "coat",
    "dress",
    "gown",
    "skirt",
    "jeans",
    "trousers",
    "jumpsuit",
    "cardigan",
    "tunic",
    "set",
]

STYLE_LABELS = [
    "casual",
    "streetwear",
    "formal",
    "editorial",
    "avant-garde",
    "minimalist",
    "ethnic",
    "maximalist",
]

MATERIAL_LABELS = [
    "cotton",
    "denim",
    "wool",
    "satin",
    "synthetic",
    "silk",
    "tulle",
    "mesh",
    "jacquard",
    "knit",
    "leather",
    "chiffon",
]

OCCASION_LABELS = [
    "casual",
    "formal",
    "editorial",
    "festive",
    "wedding",
]

PATTERN_LABELS = [
    "solid",
    "striped",
    "floral",
    "graphic print",
    "abstract print",
    "embroidered",
    "textured",
    "colorblock",
    "plaid",
    "houndstooth",
]

SEASON_LABELS = ["spring", "summer", "fall", "winter", "transitional", "unknown"]


CLASSIFICATION_SYSTEM = f"""
You are a fashion design assistant for garment image classification.

Analyze the image and return ONLY valid JSON.
Do not use markdown fences.
Do not add commentary.
Do not add extra keys.

Critical rules:
1. Choose exactly ONE dominant label for garment_type, style, material, occasion, pattern, and season.
2. Never return comma-separated values for those fields.
3. When multiple garments appear, choose the single dominant visible garment for garment_type.
4. Use ONLY the allowed labels below for structured fields.
5. If unsure, choose the closest allowed label instead of inventing a new label.
6. Keep location_context continent/country/city as null unless there is very strong visual evidence.
7. Keep time_context year/month null unless clearly inferable.
8. description can be rich, but structured fields must be tightly normalized.
9. Prefer broad normalized labels over detailed fashion wording.

Allowed labels:
- garment_type: {GARMENT_LABELS}
- style: {STYLE_LABELS}
- material: {MATERIAL_LABELS}
- occasion: {OCCASION_LABELS}
- pattern: {PATTERN_LABELS}
- season: {SEASON_LABELS}

Few-shot examples:

Example 1
Image summary: relaxed indoor look with a hoodie and jeans
Output:
{{
  "description": "A relaxed casual outfit featuring a hoodie with denim bottoms in an indoor setting.",
  "garment_type": "hoodie",
  "style": "streetwear",
  "material": "cotton",
  "color_palette": ["red", "blue"],
  "pattern": "solid",
  "season": "fall",
  "occasion": "casual",
  "consumer_profile": null,
  "trend_notes": "Comfort-focused casual styling.",
  "location_context": {{"continent": null, "country": null, "city": null}},
  "time_context": {{"year": null, "month": null, "season": "fall"}},
  "designer": null
}}

Example 2
Image summary: white bridal gown and veil
Output:
{{
  "description": "A formal bridal look featuring a white gown and veil with a clean elegant silhouette.",
  "garment_type": "gown",
  "style": "formal",
  "material": "chiffon",
  "color_palette": ["white"],
  "pattern": "solid",
  "season": "spring",
  "occasion": "wedding",
  "consumer_profile": null,
  "trend_notes": "Minimal bridal styling.",
  "location_context": {{"continent": null, "country": null, "city": null}},
  "time_context": {{"year": null, "month": null, "season": "spring"}},
  "designer": null
}}

Example 3
Image summary: sharp blazer styling with denim in an indoor setting
Output:
{{
  "description": "A tailored blazer paired with casual separates in an indoor environment.",
  "garment_type": "blazer",
  "style": "casual",
  "material": "wool",
  "color_palette": ["black", "blue", "white"],
  "pattern": "solid",
  "season": "fall",
  "occasion": "formal",
  "consumer_profile": null,
  "trend_notes": "Relaxed blazer styling with denim.",
  "location_context": {{"continent": null, "country": null, "city": null}},
  "time_context": {{"year": null, "month": null, "season": "fall"}},
  "designer": null
}}

Now return JSON in this exact structure:
{{
  "description": "rich natural-language description of the outfit and scene",
  "garment_type": "one allowed label only",
  "style": "one allowed label only",
  "material": "one allowed label only",
  "color_palette": ["#RRGGBB or color name", "..."],
  "pattern": "one allowed label only",
  "season": "one allowed label only",
  "occasion": "one allowed label only",
  "consumer_profile": "short demographic or psychographic hint if inferable, else null",
  "trend_notes": "short trend or detail notes",
  "location_context": {{"continent": null, "country": null, "city": null}},
  "time_context": {{"year": null, "month": null, "season": null}},
  "designer": null
}}
""".strip()


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


def _pick_first(value: str | None) -> str | None:
    if value is None:
        return None
    parts = [p.strip() for p in str(value).split(",") if p.strip()]
    return parts[0] if parts else None


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip().lower()
    return value or None


def _normalize_color_palette(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = [str(x) for x in value if x is not None]
    else:
        return []

    seen = set()
    cleaned: list[str] = []
    for item in items:
        token = item.strip().lower()
        if not token:
            continue
        if token not in seen:
            seen.add(token)
            cleaned.append(token)
    return cleaned[:5]


def _canon_garment(value: str | None) -> str | None:
    v = _normalize_string(_pick_first(value))
    if not v:
        return None

    checks = [
        ("hoodie", "hoodie"),
        ("hooded sweatshirt", "hoodie"),
        ("sweatshirt", "sweatshirt"),
        ("crewneck", "sweatshirt"),
        ("pullover", "sweatshirt"),
        ("sweater", "sweatshirt"),
        ("blazer", "blazer"),
        ("jacket", "jacket"),
        ("coat", "coat"),
        ("gown", "gown"),
        ("wedding dress", "gown"),
        ("dress", "dress"),
        ("jumpsuit", "jumpsuit"),
        ("cardigan", "cardigan"),
        ("tunic", "tunic"),
        ("skirt", "skirt"),
        ("jeans", "jeans"),
        ("denim pants", "jeans"),
        ("trousers", "trousers"),
        ("pants", "trousers"),
        ("blouse", "blouse"),
        ("t-shirt", "t-shirt"),
        ("tee", "t-shirt"),
        ("shirt", "shirt"),
        ("top", "top"),
        ("set", "set"),
        ("matching set", "set"),
    ]

    for needle, label in checks:
        if needle in v:
            return label

    return v if v in GARMENT_LABELS else None


def _canon_style(value: str | None) -> str | None:
    v = _normalize_string(_pick_first(value))
    if not v:
        return None

    mapping = {
        "smart-casual": "casual",
        "smart casual": "casual",
        "bohemian": "ethnic",
        "bridal": "formal",
        "runway": "editorial",
    }
    v = mapping.get(v, v)
    return v if v in STYLE_LABELS else None


def _canon_material(value: str | None) -> str | None:
    v = _normalize_string(_pick_first(value))
    if not v:
        return None

    mapping = {
        "cotton blend": "cotton",
        "wool blend": "wool",
        "synthetic blend": "synthetic",
        "faux fur": "synthetic",
        "faux leather": "synthetic",
        "cotton knit": "knit",
        "sheer": "mesh",
        "mesh blend": "mesh",
        "rope embellishment": "cotton",
        "twill": "cotton",
    }
    v = mapping.get(v, v)

    checks = [
        ("denim", "denim"),
        ("cotton", "cotton"),
        ("wool", "wool"),
        ("satin", "satin"),
        ("synthetic", "synthetic"),
        ("silk", "silk"),
        ("tulle", "tulle"),
        ("mesh", "mesh"),
        ("jacquard", "jacquard"),
        ("knit", "knit"),
        ("leather", "leather"),
        ("chiffon", "chiffon"),
    ]

    for needle, label in checks:
        if needle in v:
            return label

    return v if v in MATERIAL_LABELS else None


def _canon_occasion(value: str | None) -> str | None:
    v = _normalize_string(_pick_first(value))
    if not v:
        return None

    mapping = {
        "workwear": "formal",
        "office": "formal",
        "bridal": "wedding",
        "party": "festive",
        "ceremony": "formal",
        "runway": "editorial",
    }
    v = mapping.get(v, v)
    return v if v in OCCASION_LABELS else None


def _canon_pattern(value: str | None) -> str | None:
    v = _normalize_string(_pick_first(value))
    if not v:
        return "solid"

    checks = [
        ("graphic", "graphic print"),
        ("abstract", "abstract print"),
        ("embroider", "embroidered"),
        ("stripe", "striped"),
        ("floral", "floral"),
        ("textured", "textured"),
        ("texture", "textured"),
        ("colorblock", "colorblock"),
        ("plaid", "plaid"),
        ("houndstooth", "houndstooth"),
        ("solid", "solid"),
    ]
    for needle, label in checks:
        if needle in v:
            return label

    return v if v in PATTERN_LABELS else "solid"


def _canon_season(value: str | None) -> str:
    v = _normalize_string(_pick_first(value))
    if not v:
        return "unknown"

    mapping = {
        "autumn": "fall",
    }
    v = mapping.get(v, v)
    return v if v in SEASON_LABELS else "unknown"


def _normalize_location_context(raw: dict[str, Any]) -> dict[str, Any]:
    loc = raw.get("location_context")
    if not isinstance(loc, dict):
        raw["location_context"] = {"continent": None, "country": None, "city": None}
        return raw

    raw["location_context"] = {
        "continent": loc.get("continent"),
        "country": loc.get("country"),
        "city": loc.get("city"),
    }
    return raw


def _normalize_time_context(raw: dict[str, Any]) -> dict[str, Any]:
    tim = raw.get("time_context")
    if not isinstance(tim, dict):
        raw["time_context"] = {"year": None, "month": None, "season": None}
        return raw

    raw["time_context"] = {
        "year": tim.get("year"),
        "month": tim.get("month"),
        "season": _canon_season(tim.get("season")),
    }
    return raw


def _normalize_payload(raw: dict[str, Any]) -> ClassificationPayload:
    raw = dict(raw)

    if raw.get("description") is not None:
        raw["description"] = str(raw["description"]).strip()

    raw["garment_type"] = _canon_garment(raw.get("garment_type"))
    raw["style"] = _canon_style(raw.get("style"))
    raw["material"] = _canon_material(raw.get("material"))
    raw["occasion"] = _canon_occasion(raw.get("occasion"))
    raw["pattern"] = _canon_pattern(raw.get("pattern"))
    raw["season"] = _canon_season(raw.get("season"))
    raw["color_palette"] = _normalize_color_palette(raw.get("color_palette"))

    raw = _normalize_location_context(raw)
    raw = _normalize_time_context(raw)

    return ClassificationPayload.model_validate(raw)


def classify_garment_image(
    settings: Settings, image_bytes: bytes, mime_type: str
) -> tuple[ClassificationPayload, str]:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        pil = Image.open(io.BytesIO(image_bytes))
    except OSError as e:
        raise ValueError("Could not decode image bytes") from e

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            CLASSIFICATION_SYSTEM,
            pil,
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
        ),
    )

    raw_text = (response.text or "").strip()
    data = _extract_json_object(raw_text)

    try:
        payload = _normalize_payload(data)
    except ValidationError as e:
        raise AIStructuredOutputError(f"Model JSON failed validation: {e}") from e

    return payload, raw_text