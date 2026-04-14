from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    continent: str | None = None
    country: str | None = None
    city: str | None = None


class TimeContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    year: int | None = None
    month: int | None = None
    season: str | None = None

    @field_validator("year", "month", mode="before")
    @classmethod
    def coerce_optional_int(cls, v: object) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(float(v))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None


class ClassificationPayload(BaseModel):
    """Expected shape from Gemini (parsed and normalized)."""

    model_config = ConfigDict(extra="ignore")

    description: str = ""
    garment_type: str | None = None
    style: str | None = None
    material: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    pattern: str | None = None
    season: str | None = None
    occasion: str | None = None
    consumer_profile: str | None = None
    trend_notes: str | None = None
    location_context: LocationContext | None = None
    time_context: TimeContext | None = None
    designer: str | None = None

    @field_validator("location_context", "time_context", mode="before")
    @classmethod
    def coerce_nested_dict(cls, v: object) -> dict | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        return None

    @field_validator("color_palette", mode="before")
    @classmethod
    def coerce_color_palette(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, str):
            return [v]
        return []


class GarmentImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    stored_path: str
    mime_type: str
    file_size_bytes: int
    description: str | None
    garment_type: str | None
    style: str | None
    material: str | None
    pattern: str | None
    season: str | None
    occasion: str | None
    consumer_profile: str | None
    trend_notes: str | None
    color_palette: list | None
    location_continent: str | None
    location_country: str | None
    location_city: str | None
    capture_year: int | None
    capture_month: int | None
    time_season: str | None
    designer: str | None
    created_at: datetime


class UploadResponse(BaseModel):
    image: GarmentImageRead
    message: str = "Upload and classification completed."
