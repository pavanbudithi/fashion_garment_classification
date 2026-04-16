from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import distinct

from app.core.database import get_db
from app.models.garment import GarmentImage  # SQLAlchemy model

router = APIRouter(prefix="/filters", tags=["filters"])


def get_distinct(db: Session, column) -> list:
    return sorted([r[0] for r in db.query(distinct(column)).all() if r[0]])


@router.get("/")
def get_all_filters(db: Session = Depends(get_db)):
    """Dynamically return all filter options derived from actual DB data."""
    return {
        "garment_attributes": {
            "garment_types":     get_distinct(db, GarmentImage.garment_type),
            "styles":            get_distinct(db, GarmentImage.style),
            "materials":         get_distinct(db, GarmentImage.material),
            "patterns":          get_distinct(db, GarmentImage.pattern),
            "occasions":         get_distinct(db, GarmentImage.occasion),
            "consumer_profiles": get_distinct(db, GarmentImage.consumer_profile),
            "designers":         get_distinct(db, GarmentImage.designer),
        },
        "context": {
            "seasons":    get_distinct(db, GarmentImage.time_season),      # time_season
            "continents": get_distinct(db, GarmentImage.location_continent),
            "countries":  get_distinct(db, GarmentImage.location_country),
            "cities":     get_distinct(db, GarmentImage.location_city),
            "years":      get_distinct(db, GarmentImage.capture_year),
            "months":     get_distinct(db, GarmentImage.capture_month),
        },
    }


@router.get("/garment_types")
def get_garment_types(db: Session = Depends(get_db)):
    return {"garment_types": get_distinct(db, GarmentImage.garment_type)}


@router.get("/styles")
def get_styles(db: Session = Depends(get_db)):
    return {"styles": get_distinct(db, GarmentImage.style)}


@router.get("/materials")
def get_materials(db: Session = Depends(get_db)):
    return {"materials": get_distinct(db, GarmentImage.material)}


@router.get("/patterns")
def get_patterns(db: Session = Depends(get_db)):
    return {"patterns": get_distinct(db, GarmentImage.pattern)}


@router.get("/occasions")
def get_occasions(db: Session = Depends(get_db)):
    return {"occasions": get_distinct(db, GarmentImage.occasion)}


@router.get("/seasons")
def get_seasons(db: Session = Depends(get_db)):
    return {"seasons": get_distinct(db, GarmentImage.time_season)}


@router.get("/locations")
def get_locations(db: Session = Depends(get_db)):
    return {
        "continents": get_distinct(db, GarmentImage.location_continent),
        "countries":  get_distinct(db, GarmentImage.location_country),
        "cities":     get_distinct(db, GarmentImage.location_city),
    }