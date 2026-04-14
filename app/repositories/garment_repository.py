from sqlalchemy.orm import Session

from app.models.garment import GarmentImage
from app.schemas.garment import ClassificationPayload


def classification_to_row_fields(payload: ClassificationPayload) -> dict:
    loc = payload.location_context
    tim = payload.time_context
    structured = payload.model_dump(mode="json")
    return {
        "description": payload.description or None,
        "garment_type": payload.garment_type,
        "style": payload.style,
        "material": payload.material,
        "pattern": payload.pattern,
        "season": payload.season,
        "occasion": payload.occasion,
        "consumer_profile": payload.consumer_profile,
        "trend_notes": payload.trend_notes,
        "color_palette": payload.color_palette or None,
        "location_continent": loc.continent if loc else None,
        "location_country": loc.country if loc else None,
        "location_city": loc.city if loc else None,
        "capture_year": tim.year if tim else None,
        "capture_month": tim.month if tim else None,
        "time_season": tim.season if tim else None,
        "designer": payload.designer,
        "structured_metadata": structured,
    }


def create_garment_image(
    db: Session,
    *,
    original_filename: str,
    stored_path: str,
    mime_type: str,
    file_size_bytes: int,
    payload: ClassificationPayload,
    ai_raw_text: str,
) -> GarmentImage:
    fields = classification_to_row_fields(payload)
    row = GarmentImage(
        original_filename=original_filename,
        stored_path=stored_path,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        ai_raw_text=ai_raw_text,
        **fields,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
