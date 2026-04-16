import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.garment import GarmentImage

# ── Test DB ──────────────────────────────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test_filters.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ── Seed fixture ─────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def seed_db():
    db = TestSessionLocal()
    db.query(GarmentImage).delete()
    db.add_all([
        GarmentImage(
            original_filename="download.jpg",
            stored_path="/download.jpg",
            mime_type="image/jpeg",
            file_size_bytes=102400,
            description="A woman in a bright blue puffer coat",
            garment_type="puffer coat",
            style="casual",
            material="nylon",
            pattern="solid",
            occasion="casual",
            time_season="winter",          # ← correct column name
            consumer_profile="young adult",
            trend_notes="Puffer coats trending this winter",
            designer=None,
            location_continent="North America",  # ← correct column name
            location_country="USA",
            location_city="New York",
            capture_year=2024,             # ← correct column name
            capture_month=1,
        ),
        GarmentImage(
            original_filename="kurta.jpg",
            stored_path="/images/kurta.jpg",
            mime_type="image/jpeg",
            file_size_bytes=98304,
            description="Floral embroidered kurta from artisan market",
            garment_type="kurta",
            style="ethnic",
            material="cotton",
            pattern="floral",
            occasion="festive",
            time_season="summer",
            consumer_profile="women",
            trend_notes="Embroidered necklines gaining popularity",
            designer="Anita Dongre",
            location_continent="Asia",
            location_country="India",
            location_city="Mumbai",
            capture_year=2023,
            capture_month=6,
        ),
    ])
    db.commit()
    db.close()
    yield
    db = TestSessionLocal()
    db.query(GarmentImage).delete()
    db.commit()
    db.close()


# ── Tests: GET /garments/filters/ ────────────────────────────────────────────
class TestGetAllFilters:
    def test_status_200(self):
        assert client.get("/garments/filters/").status_code == 200

    def test_top_level_keys(self):
        data = client.get("/garments/filters/").json()
        assert "garment_attributes" in data
        assert "context" in data

    def test_garment_types_present(self):
        types = client.get("/garments/filters/").json()["garment_attributes"]["garment_types"]
        assert "puffer coat" in types
        assert "kurta" in types

    def test_styles_present(self):
        styles = client.get("/garments/filters/").json()["garment_attributes"]["styles"]
        assert "casual" in styles
        assert "ethnic" in styles

    def test_seasons_present(self):
        seasons = client.get("/garments/filters/").json()["context"]["seasons"]
        assert "winter" in seasons
        assert "summer" in seasons

    def test_locations_present(self):
        ctx = client.get("/garments/filters/").json()["context"]
        assert "North America" in ctx["continents"]
        assert "USA" in ctx["countries"]
        assert "New York" in ctx["cities"]

    def test_no_null_values(self):
        data = client.get("/garments/filters/").json()
        for section in data.values():
            for values in section.values():
                assert None not in values

    def test_values_are_sorted(self):
        data = client.get("/garments/filters/").json()
        for section in data.values():
            for values in section.values():
                assert values == sorted(values, key=lambda x: str(x))

    def test_designers_excludes_null(self):
        designers = client.get("/garments/filters/").json()["garment_attributes"]["designers"]
        assert None not in designers
        assert "Anita Dongre" in designers


# ── Tests: individual filter endpoints ───────────────────────────────────────
class TestIndividualFilterEndpoints:
    def test_garment_types(self):
        r = client.get("/garments/filters/garment_types")
        assert r.status_code == 200
        assert "garment_types" in r.json()

    def test_styles(self):
        r = client.get("/garments/filters/styles")
        assert "styles" in r.json()

    def test_materials(self):
        r = client.get("/garments/filters/materials")
        assert "materials" in r.json()
        assert "nylon" in r.json()["materials"]

    def test_patterns(self):
        r = client.get("/garments/filters/patterns")
        assert "patterns" in r.json()
        assert "floral" in r.json()["patterns"]

    def test_occasions(self):
        r = client.get("/garments/filters/occasions")
        assert "occasions" in r.json()

    def test_seasons(self):
        r = client.get("/garments/filters/seasons")
        assert "seasons" in r.json()
        assert "winter" in r.json()["seasons"]

    def test_locations(self):
        r = client.get("/garments/filters/locations")
        data = r.json()
        assert "continents" in data
        assert "countries" in data
        assert "cities" in data
        assert "Asia" in data["continents"]
        assert "India" in data["countries"]
        assert "Mumbai" in data["cities"]


# ── Tests: empty DB edge case ─────────────────────────────────────────────────
class TestEmptyDB:
    @pytest.fixture(autouse=True)
    def clear_db(self):
        db = TestSessionLocal()
        db.query(GarmentImage).delete()
        db.commit()
        db.close()

    def test_all_filters_empty_lists(self):
        data = client.get("/garments/filters/").json()
        for section in data.values():
            for values in section.values():
                assert values == []

    def test_locations_empty(self):
        r = client.get("/garments/filters/locations")
        data = r.json()
        assert data["continents"] == []
        assert data["countries"] == []
        assert data["cities"] == []