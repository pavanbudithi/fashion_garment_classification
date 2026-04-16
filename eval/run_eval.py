from __future__ import annotations

import json
import mimetypes
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.core.config import get_settings
from app.services.gemini_service import classify_garment_image

LABELS_FILE = PROJECT_ROOT / "eval" / "labeled_dataset_normalized.json"
IMAGES_DIR = PROJECT_ROOT / "data" / "fash_pics"
OUTPUT_FILE = PROJECT_ROOT / "eval" / "eval_results.json"

EVAL_FIELDS = [
    "garment_type",
    "style",
    "material",
    "occasion",
    "location_context",
]


def _pick_first(value: str | None) -> str | None:
    if value is None:
        return None
    parts = [p.strip() for p in str(value).split(",") if p.strip()]
    return parts[0] if parts else None


def _norm_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip().lower()
    return value or None


def canon_garment(value: str | None) -> str | None:
    v = _norm_text(_pick_first(value))
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
    return v


def canon_style(value: str | None) -> str | None:
    v = _norm_text(_pick_first(value))
    if not v:
        return None

    mapping = {
        "smart-casual": "casual",
        "smart casual": "casual",
        "bridal": "formal",
        "bohemian": "ethnic",
        "runway": "editorial",
    }
    return mapping.get(v, v)


def canon_material(value: str | None) -> str | None:
    v = _norm_text(_pick_first(value))
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
    return v


def canon_occasion(value: str | None) -> str | None:
    v = _norm_text(_pick_first(value))
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
    return mapping.get(v, v)


def canon_location(continent: str | None, country: str | None, city: str | None) -> str | None:
    # coarse normalized location for fairer matching
    if city or country or continent:
        return "outdoor"
    return "unknown"


def build_predicted_map(payload) -> dict[str, str | None]:
    loc = payload.location_context
    return {
        "garment_type": canon_garment(payload.garment_type),
        "style": canon_style(payload.style),
        "material": canon_material(payload.material),
        "occasion": canon_occasion(payload.occasion),
        "location_context": canon_location(
            loc.continent if loc else None,
            loc.country if loc else None,
            loc.city if loc else None,
        ),
    }


def build_expected_map(expected: dict) -> dict[str, str | None]:
    return {
        "garment_type": canon_garment(expected.get("garment_type")),
        "style": canon_style(expected.get("style")),
        "material": canon_material(expected.get("material")),
        "occasion": canon_occasion(expected.get("occasion")),
        "location_context": canon_location(
            expected.get("location_continent"),
            expected.get("location_country"),
            expected.get("location_city"),
        ),
    }


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "image/jpeg"


def load_dataset() -> list[dict]:
    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("labeled_dataset_normalized.json must be a JSON list")
    return data


def build_image_lookup() -> dict[str, Path]:
    return {p.name.lower(): p for p in IMAGES_DIR.iterdir() if p.is_file()}


def load_existing_results() -> list[dict]:
    if not OUTPUT_FILE.exists():
        return []
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("results", [])
    except Exception:
        return []


def is_completed(result: dict) -> bool:
    return "comparisons" in result and result["comparisons"] is not None


def rebuild_summary(results: list[dict]) -> tuple[dict, dict]:
    field_correct = defaultdict(int)
    field_total = defaultdict(int)

    processed = 0
    skipped_missing = 0
    failed_classification = 0

    for item in results:
        if "comparisons" in item:
            processed += 1
            for field in EVAL_FIELDS:
                comp = item["comparisons"][field]
                field_total[field] += 1
                if comp["match"]:
                    field_correct[field] += 1
        elif item.get("error") == "image file not found":
            skipped_missing += 1
        elif "error" in item:
            failed_classification += 1

    summary = {}
    for field in EVAL_FIELDS:
        total = field_total[field]
        correct = field_correct[field]
        accuracy = round(correct / total, 4) if total else 0.0
        summary[field] = {
            "correct": correct,
            "total": total,
            "accuracy": accuracy,
        }

    counts = {
        "processed": processed,
        "skipped_missing": skipped_missing,
        "failed_classification": failed_classification,
    }
    return summary, counts


def save_output(dataset_len: int, image_lookup: dict[str, Path], results: list[dict]) -> None:
    summary, counts = rebuild_summary(results)

    output = {
        "paths": {
            "labels_file": str(LABELS_FILE),
            "images_dir": str(IMAGES_DIR),
            "output_file": str(OUTPUT_FILE),
        },
        "counts": {
            "labeled_items": dataset_len,
            "image_files_found": len(image_lookup),
            **counts,
        },
        "summary": summary,
        "results": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


def extract_retry_seconds(err: str) -> int:
    patterns = [
        r"Please retry in (\d+)\.(\d+)s",
        r"Please retry in (\d+)s",
        r"retryDelay': '(\d+)s'",
    ]
    for pattern in patterns:
        match = re.search(pattern, err)
        if match:
            return int(match.group(1))
    return 15


def classify_with_retry(settings, image_bytes: bytes, mime_type: str, filename: str):
    max_attempts = 4

    for attempt in range(1, max_attempts + 1):
        try:
            return classify_garment_image(settings, image_bytes, mime_type)
        except Exception as e:
            err = str(e)
            retryable = any(x in err for x in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"])
            if not retryable or attempt == max_attempts:
                raise

            sleep_seconds = extract_retry_seconds(err) + 2
            print(f"Retrying {filename} in {sleep_seconds}s (attempt {attempt}/{max_attempts})")
            time.sleep(sleep_seconds)

    raise RuntimeError("Unexpected retry flow")


def main() -> None:
    settings = get_settings()
    dataset = load_dataset()
    image_lookup = build_image_lookup()
    existing_results = load_existing_results()

    results_by_filename = {
        item["filename"].lower(): item
        for item in existing_results
        if item.get("filename")
    }

    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("LABELS_FILE:", LABELS_FILE)
    print("IMAGES_DIR:", IMAGES_DIR)
    print("OUTPUT_FILE:", OUTPUT_FILE)
    print("Total labeled items:", len(dataset))
    print("Total image files found:", len(image_lookup))
    print("Existing saved results:", len(existing_results))

    for item in dataset:
        filename = item["filename"]
        expected = item["expected"]
        key = filename.lower()

        if key in results_by_filename and is_completed(results_by_filename[key]):
            print(f"Skipping already completed: {filename}")
            continue

        image_path = image_lookup.get(key)
        if image_path is None:
            print(f"Missing file: {filename}")
            results_by_filename[key] = {
                "filename": filename,
                "error": "image file not found",
            }
            save_output(len(dataset), image_lookup, list(results_by_filename.values()))
            continue

        print(f"Processing: {filename}")
        image_bytes = image_path.read_bytes()
        mime_type = guess_mime(image_path)

        try:
            payload, _ = classify_with_retry(settings, image_bytes, mime_type, filename)
        except Exception as e:
            print(f"Classification failed for {filename}: {e}")
            results_by_filename[key] = {
                "filename": filename,
                "error": str(e),
            }
            save_output(len(dataset), image_lookup, list(results_by_filename.values()))
            continue

        predicted_map = build_predicted_map(payload)
        expected_map = build_expected_map(expected)

        comparisons = {}
        for field in EVAL_FIELDS:
            pred = predicted_map[field]
            exp = expected_map[field]
            comparisons[field] = {
                "expected": exp,
                "predicted": pred,
                "match": pred == exp,
            }

        results_by_filename[key] = {
            "filename": filename,
            "comparisons": comparisons,
        }

        save_output(len(dataset), image_lookup, list(results_by_filename.values()))
        time.sleep(3)

    final_results = list(results_by_filename.values())
    save_output(len(dataset), image_lookup, final_results)

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        final_output = json.load(f)

    print("\nCounts:")
    for k, v in final_output["counts"].items():
        print(f"{k}: {v}")

    print("\nPer-attribute accuracy:")
    for field, stats in final_output["summary"].items():
        print(f"{field}: {stats['correct']}/{stats['total']} = {stats['accuracy']:.2%}")

    print(f"\nSaved detailed results to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()