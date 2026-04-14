from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.exceptions import AIStructuredOutputError
from app.repositories.garment_repository import create_garment_image
from app.schemas.garment import GarmentImageRead, UploadResponse
from app.services.gemini_service import classify_garment_image
from app.services.image_storage import save_upload_bytes

router = APIRouter(tags=["upload"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB — adjust with reverse proxy limits


@router.post("/upload", response_model=UploadResponse)
async def upload_garment_image(
    file: UploadFile = File(..., description="Garment street-style photo"),
    designer: str | None = Form(
        default=None,
        description="Optional designer name for provenance (overrides AI if provided)",
    ),
    db: Session = Depends(get_db),
) -> UploadResponse:
    settings = get_settings()
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    mime = file.content_type or "application/octet-stream"
    rel_path, _ = save_upload_bytes(settings, file.filename or "upload.bin", data)

    try:
        payload, raw_text = classify_garment_image(settings, data, mime)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AIStructuredOutputError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Classification failed: {e!s}",
        ) from e

    if designer and designer.strip():
        payload.designer = designer.strip()

    row = create_garment_image(
        db,
        original_filename=file.filename or "upload.bin",
        stored_path=rel_path,
        mime_type=mime,
        file_size_bytes=len(data),
        payload=payload,
        ai_raw_text=raw_text,
    )

    return UploadResponse(image=GarmentImageRead.model_validate(row))
