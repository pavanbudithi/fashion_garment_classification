import uuid
from pathlib import Path

from app.core.config import Settings


def safe_extension(filename: str) -> str:
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()[:16]
    return "bin"


def save_upload_bytes(
    settings: Settings, original_filename: str, data: bytes
) -> tuple[str, Path]:
    """Write bytes to disk; return (relative_stored_path, absolute_path)."""
    ext = safe_extension(original_filename)
    name = f"{uuid.uuid4().hex}.{ext}"
    base = settings.resolved_upload_dir()
    base.mkdir(parents=True, exist_ok=True)
    abs_path = base / name
    abs_path.write_bytes(data)
    rel = abs_path.relative_to(settings.project_root).as_posix()
    return rel, abs_path
