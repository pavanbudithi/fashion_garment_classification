from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import filters, search, upload
from app.core.config import get_settings
from app.core.database import init_db

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.resolved_upload_dir().mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="Fashion Garment Inspiration API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(search.router, prefix="/garments", tags=["search"])
app.include_router(filters.router, prefix="/garments", tags=["filters"])

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
settings = get_settings()

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(settings.resolved_upload_dir())), name="uploads")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}