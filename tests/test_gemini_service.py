from app.services.gemini_service import _extract_json_object, _normalize_payload


def test_extract_json_object_from_fenced_json():
    raw = """
    ```json
    {
      "description": "A bridal look with a white gown and veil.",
      "garment_type": "wedding dress",
      "style": "bridal",
      "material": "chiffon",
      "color_palette": ["White", "white"],
      "pattern": "solid",
      "season": "spring",
      "occasion": "bridal",
      "consumer_profile": null,
      "trend_notes": "Minimal bridal silhouette.",
      "location_context": {"continent": null, "country": null, "city": null},
      "time_context": {"year": null, "month": null, "season": "spring"},
      "designer": null
    }
    ```
    """
    parsed = _extract_json_object(raw)

    assert parsed["garment_type"] == "wedding dress"
    assert parsed["style"] == "bridal"
    assert parsed["occasion"] == "bridal"


def test_normalize_payload_canonicalizes_labels():
    raw = {
        "description": "A polished outfit with a tailored outer layer.",
        "garment_type": "hooded sweatshirt, jeans",
        "style": "smart-casual",
        "material": "cotton blend",
        "color_palette": ["Red", "red", "BLUE"],
        "pattern": "embroidered neckline",
        "season": "autumn",
        "occasion": "workwear",
        "consumer_profile": None,
        "trend_notes": "Clean structured styling.",
        "location_context": {"continent": None, "country": None, "city": None},
        "time_context": {"year": None, "month": None, "season": "autumn"},
        "designer": None,
    }

    payload = _normalize_payload(raw)

    assert payload.garment_type == "hoodie"
    assert payload.style == "casual"
    assert payload.material == "cotton"
    assert payload.pattern == "embroidered"
    assert payload.season == "fall"
    assert payload.occasion == "formal"
    assert payload.time_context is not None
    assert payload.time_context.season == "fall"
    assert payload.color_palette == ["red", "blue"]