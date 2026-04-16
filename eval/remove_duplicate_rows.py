from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.core.database import SessionLocal, init_db
from app.models.garment import GarmentImage


def file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def resolve_path(stored_path: str) -> Path:
    return (PROJECT_ROOT / stored_path).resolve()


def main() -> None:
    init_db()
    db = SessionLocal()

    try:
        rows = db.query(GarmentImage).order_by(GarmentImage.created_at.asc()).all()
        seen_hashes: dict[str, str] = {}
        deleted = 0

        for row in rows:
            path = resolve_path(row.stored_path)
            digest = file_hash(path)

            if digest is None:
                continue

            if digest in seen_hashes:
                print(f"Deleting duplicate: {row.original_filename}")
                db.delete(row)
                deleted += 1
            else:
                seen_hashes[digest] = row.id

        db.commit()
        print(f"\nDeleted duplicate rows: {deleted}")

    finally:
        db.close()


if __name__ == "__main__":
    main()