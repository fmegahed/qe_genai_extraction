import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

# Must be set before app modules create the engine
os.environ["DATABASE_URL"] = f"sqlite:///{APP_DIR / 'tests' / 'test.db'}"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["BASE_URL"] = "http://testserver"

import pytest
from fastapi.testclient import TestClient

from database import Base, SessionLocal, engine
from main import app
from models import ReviewerToken


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin(client):
    resp = client.post("/admin/login", data={"password": "test-password"}, follow_redirects=False)
    assert resp.status_code == 302
    return client


@pytest.fixture()
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def create_reviewer(admin, name="Test Reviewer", email="reviewer@example.com") -> str:
    """Create a reviewer via the admin route and return the token string."""
    resp = admin.post("/admin/create-token", data={"reviewer_name": name, "reviewer_email": email})
    assert resp.status_code == 200
    session = SessionLocal()
    try:
        reviewer = (
            session.query(ReviewerToken)
            .filter(ReviewerToken.reviewer_name == name)
            .order_by(ReviewerToken.id.desc())
            .first()
        )
        return reviewer.token
    finally:
        session.close()
