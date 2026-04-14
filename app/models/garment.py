import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GarmentImage(Base):
    """Stored upload + AI classification metadata."""

    __tablename__ = "garment_images"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_path: Mapped[str] = mapped_column(String(1024))
    mime_type: Mapped[str] = mapped_column(String(128))
    file_size_bytes: Mapped[int] = mapped_column(Integer)

    # Natural-language summary from the model
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured attributes (also duplicated in filter-friendly columns where useful)
    garment_type: Mapped[str | None] = mapped_column(String(256), nullable=True)
    style: Mapped[str | None] = mapped_column(String(256), nullable=True)
    material: Mapped[str | None] = mapped_column(String(256), nullable=True)
    pattern: Mapped[str | None] = mapped_column(String(256), nullable=True)
    season: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occasion: Mapped[str | None] = mapped_column(String(256), nullable=True)
    consumer_profile: Mapped[str | None] = mapped_column(String(512), nullable=True)
    trend_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    color_palette: Mapped[list | None] = mapped_column(SQLiteJSON, nullable=True)

    location_continent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(256), nullable=True)

    capture_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capture_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_season: Mapped[str | None] = mapped_column(String(64), nullable=True)

    designer: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Full structured payload + raw model text for audit/debug
    structured_metadata: Mapped[dict | None] = mapped_column(SQLiteJSON, nullable=True)
    ai_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
