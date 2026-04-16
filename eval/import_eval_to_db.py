from __future__ import annotations

import json
import mimetypes
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.models.garment import GarmentImage

LABELS_FILE = PROJECT_ROOT / "eval" / "labeled_dataset_normalized.json"
IMAGES_DIR = PROJECT_ROOT / "data" / "fash_pics"

DESIGNERS = [
    "Rahul Mishra",
    "Sabyasachi",
    "Alexander McQueen",
    "Dior",
    "Gucci",
]

LOCATIONS = [
    {"continent": "Asia", "country": "India", "city": "Mumbai"},
    {"continent": "Europe", "country": "France", "city": "Paris"},
    {"continent": "North America", "country": "USA", "city": "New York"},
    {"continent": "Europe", "country": "Italy", "city": "Milan"},
    {"continent": "Asia", "country": "Japan", "city": "Tokyo"},
]


def build_description(expected: dict) -> str:
    garment_type = expected.get("garment_type") or "garment"
    style = expected.get("style") or "unknown style"
    occasion = expected.get("occasion") or "unknown occasion"
    season = expected.get("time_season") or "unknown season"

    return (
        f"Manually imported evaluation image showing a {garment_type} "
        f"in {style} style, suitable for {occasion}, with a {season} context."
    )


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "image/jpeg"


def main() -> None:
    settings = get_settings()
    uploads_dir = settings.resolved_upload_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)

    if not LABELS_FILE.exists():
        raise FileNotFoundError(f"Missing labels file: {LABELS_FILE}")

    if not IMAGES_DIR.exists():
        raise FileNotFoundError(f"Missing images directory: {IMAGES_DIR}")

    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if not isinstance(dataset, list):
        raise ValueError("labeled_dataset_normalized.json must be a JSON list")

    init_db()
    db = SessionLocal()

    created = 0
    updated = 0
    skipped_missing = 0

    try:
        for idx, item in enumerate(dataset):
            filename = item["filename"]
            expected = item["expected"]

            src_path = IMAGES_DIR / filename
            if not src_path.exists():
                print(f"Skipping missing image: {filename}")
                skipped_missing += 1
                continue

            designer_value = DESIGNERS[idx % len(DESIGNERS)]
            location_value = LOCATIONS[idx % len(LOCATIONS)]

            dest_name = filename
            dest_path = uploads_dir / dest_name

            if not dest_path.exists():
                shutil.copy2(src_path, dest_path)

            stored_path = f"data/uploads/{dest_name}"
            mime_type = guess_mime(dest_path)
            file_size_bytes = dest_path.stat().st_size

            row = (
                db.query(GarmentImage)
                .filter(GarmentImage.original_filename == filename)
                .first()
            )

            row_data = {
                "original_filename": filename,
                "stored_path": stored_path,
                "mime_type": mime_type,
                "file_size_bytes": file_size_bytes,
                "description": build_description(expected),
                "garment_type": expected.get("garment_type"),
                "style": expected.get("style"),
                "material": expected.get("material"),
                "pattern": expected.get("pattern"),
                "season": expected.get("time_season"),
                "occasion": expected.get("occasion"),
                "consumer_profile": None,
                "trend_notes": "Imported from manually labeled evaluation dataset.",
                "color_palette": None,
                "location_continent": location_value["continent"],
                "location_country": location_value["country"],
                "location_city": location_value["city"],
                "capture_year": None,
                "capture_month": None,
                "time_season": expected.get("time_season"),
                "designer": designer_value,
                "structured_metadata": {
                    "source": "manual_eval_import",
                    "expected": expected,
                    "designer_seeded": designer_value,
                    "location_seeded": location_value,
                },
                "ai_raw_text": "Imported from eval/labeled_dataset_normalized.json",
            }

            if row is None:
                row = GarmentImage(**row_data)
                db.add(row)
                created += 1
            else:
                for key, value in row_data.items():
                    setattr(row, key, value)
                updated += 1

        db.commit()

    finally:
        db.close()

    print("\nImport complete")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Skipped missing: {skipped_missing}")


if __name__ == "__main__":
    main()