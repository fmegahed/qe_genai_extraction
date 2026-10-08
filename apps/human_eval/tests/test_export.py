import csv
import io

from conftest import create_reviewer
from database import SessionLocal
from models import ReviewerToken


def test_export_unblinds_and_matches_ratings(admin):
    token = create_reviewer(admin, name="Bob", email="bob@example.com")

    session = SessionLocal()
    try:
        reviewer = session.query(ReviewerToken).filter(ReviewerToken.token == token).first()
        item_order = list(reviewer.item_order)
    finally:
        session.close()

    # Rate positions 1 (block 1) and 31 (block 2) with distinct values
    admin.post(f"/review/{token}/item/1",
               data={"manufacturer_rating": 5, "models_rating": 4, "model_years_rating": 3})
    admin.post(f"/review/{token}/item/31",
               data={"manufacturer_rating": 1, "models_rating": 2, "model_years_rating": 3})

    resp = admin.get("/admin/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) == 6  # 2 rated items x 3 fields

    pos1 = {r["field"]: r for r in rows if r["position"] == "1"}
    assert pos1["manufacturer"]["rating"] == "5"
    assert pos1["models"]["rating"] == "4"
    assert pos1["model_years"]["rating"] == "3"
    assert pos1["manufacturer"]["block"] == "1"
    assert pos1["manufacturer"]["reviewer_name"] == "Bob"
    # Unblinded: model name in export matches the token's stored order
    assert pos1["manufacturer"]["model_name"] == item_order[0][1]
    assert pos1["manufacturer"]["document_id"] == str(item_order[0][0])

    pos31 = {r["field"]: r for r in rows if r["position"] == "31"}
    assert pos31["manufacturer"]["rating"] == "1"
    assert pos31["manufacturer"]["block"] == "2"
    assert pos31["manufacturer"]["model_name"] == item_order[30][1]


def test_export_empty_when_no_ratings(admin):
    create_reviewer(admin)
    resp = admin.get("/admin/export")
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert rows == []
