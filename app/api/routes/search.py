from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.garment import GarmentImage
from app.schemas.garment import GarmentImageRead

router = APIRouter()

SEARCH_FIELDS = [
    GarmentImage.description,
    GarmentImage.trend_notes,
    GarmentImage.garment_type,
    GarmentImage.style,
    GarmentImage.material,
    GarmentImage.pattern,
    GarmentImage.occasion,
    GarmentImage.consumer_profile,
    GarmentImage.location_country,
    GarmentImage.location_city,
    GarmentImage.designer,
]

SYNONYM_MAP = {
    "embroidered": ["embroidery", "embroider", "needlework", "threadwork"],
    "embroidery": ["embroidered", "needlework", "threadwork"],
    "neckline": ["neck", "collar", "yoke"],
    "artisan": ["handmade", "craft", "crafted", "traditional"],
    "market": ["bazaar", "marketplace", "street market", "souk"],
    "wedding": ["bridal", "ceremony"],
    "bridal": ["wedding", "ceremony"],
    "casual": ["everyday", "relaxed"],
    "formal": ["dressy", "elegant"],
    "streetwear": ["urban", "street style"],
    "jacket": ["outerwear", "coat", "blazer"],
    "blazer": ["jacket", "tailored jacket"],
    "dress": ["gown"],
    "gown": ["dress"],
    "knit": ["knitted", "sweater"],
    "denim": ["jeans"],
    "floral": ["flower print"],
    "graphic": ["graphic print"],
    "striped": ["stripes"],
    "textured": ["texture"],
}


def expand_query_terms(query: str) -> list[str]:
    raw = query.strip().lower()
    if not raw:
        return []

    terms: list[str] = [raw]
    tokens = [token.strip() for token in raw.split() if token.strip()]

    for token in tokens:
        if token not in terms:
            terms.append(token)
        for synonym in SYNONYM_MAP.get(token, []):
            if synonym not in terms:
                terms.append(synonym)

    for phrase, synonyms in SYNONYM_MAP.items():
        if phrase in raw:
            for synonym in synonyms:
                if synonym not in terms:
                    terms.append(synonym)

    return terms


def apply_natural_query(query_obj, q: str):
    terms = expand_query_terms(q)
    if not terms:
        return query_obj

    conditions = []
    for term in terms:
        for field in SEARCH_FIELDS:
            conditions.append(field.ilike(f"%{term}%"))

    return query_obj.filter(or_(*conditions))


@router.get("/search")
def search_garments(
    q: Optional[str] = Query(None, description="Natural language search on image metadata"),
    garment_type: Optional[str] = None,
    style: Optional[str] = None,
    material: Optional[str] = None,
    pattern: Optional[str] = None,
    occasion: Optional[str] = None,
    consumer_profile: Optional[str] = None,
    designer: Optional[str] = None,
    season: Optional[str] = None,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(GarmentImage)

    if q:
        query = apply_natural_query(query, q)

    if garment_type:
        query = query.filter(GarmentImage.garment_type.ilike(f"%{garment_type}%"))
    if style:
        query = query.filter(GarmentImage.style.ilike(f"%{style}%"))
    if material:
        query = query.filter(GarmentImage.material.ilike(f"%{material}%"))
    if pattern:
        query = query.filter(GarmentImage.pattern.ilike(f"%{pattern}%"))
    if occasion:
        query = query.filter(GarmentImage.occasion.ilike(f"%{occasion}%"))
    if consumer_profile:
        query = query.filter(GarmentImage.consumer_profile.ilike(f"%{consumer_profile}%"))
    if designer:
        query = query.filter(GarmentImage.designer.ilike(f"%{designer}%"))
    if continent:
        query = query.filter(GarmentImage.location_continent.ilike(f"%{continent}%"))
    if country:
        query = query.filter(GarmentImage.location_country.ilike(f"%{country}%"))
    if city:
        query = query.filter(GarmentImage.location_city.ilike(f"%{city}%"))
    if season:
        query = query.filter(GarmentImage.time_season.ilike(f"%{season}%"))
    if year:
        query = query.filter(GarmentImage.capture_year == year)
    if month:
        query = query.filter(GarmentImage.capture_month == month)

    total = query.count()
    results = (
        query.order_by(GarmentImage.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "results": [GarmentImageRead.model_validate(row).model_dump(mode="json") for row in results],
    }