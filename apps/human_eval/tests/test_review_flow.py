from conftest import create_reviewer
from database import SessionLocal
from models import Rating, ReviewerToken


def _get_reviewer(token):
    session = SessionLocal()
    try:
        reviewer = session.query(ReviewerToken).filter(ReviewerToken.token == token).first()
        session.expunge(reviewer)
        return reviewer
    finally:
        session.close()


def _rate(client, token, position, m=5, mo=4, my=3):
    return client.post(
        f"/review/{token}/item/{position}",
        data={"manufacturer_rating": m, "models_rating": mo, "model_years_rating": my},
        follow_redirects=False,
    )


def test_invalid_token_shows_error_page(client):
    resp = client.get("/review/not-a-real-token")
    assert resp.status_code == 200
    assert "not valid" in resp.text


def test_landing_page(admin):
    token = create_reviewer(admin, name="Alice")
    resp = admin.get(f"/review/{token}")
    assert resp.status_code == 200
    assert "Alice" in resp.text
    assert "60" in resp.text
    assert "Start Review" in resp.text


def test_token_gets_balanced_item_order(admin):
    token = create_reviewer(admin)
    reviewer = _get_reviewer(token)
    assert len(reviewer.item_order) == 60
    docs_block1 = sorted(d for d, _ in reviewer.item_order[:30])
    docs_block2 = sorted(d for d, _ in reviewer.item_order[30:])
    assert docs_block1 == docs_block2 == list(range(1, 31))


def test_next_redirects_to_first_unrated(admin):
    token = create_reviewer(admin)
    resp = admin.get(f"/review/{token}/next", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"/review/{token}/item/1"


def test_item_page_shows_recall_text_but_never_model_name(admin):
    token = create_reviewer(admin)
    reviewer = _get_reviewer(token)
    for position in (1, 31):
        resp = admin.get(f"/review/{token}/item/{position}")
        assert resp.status_code == 200
        # Blinding: raw model identifiers must not leak into the page
        assert "gemma" not in resp.text.lower()
        assert "gpt-5" not in resp.text.lower()
        assert f"Extraction {position} of 60" in resp.text


def test_manufacturer_shown_verbatim_but_models_split(admin):
    # Doc 1 / gpt-5.4-nano: manufacturer contains ";" and must NOT be split;
    # its models field ("Salem; Wildwood") must still render as separate items.
    token = create_reviewer(admin)
    reviewer = _get_reviewer(token)
    position = reviewer.item_order.index([1, "gpt-5.4-nano"]) + 1

    resp = admin.get(f"/review/{token}/item/{position}")
    assert resp.status_code == 200
    assert "Forest River, Inc.; Forest River" in resp.text
    assert "<li>Salem</li>" in resp.text
    assert "<li>Wildwood</li>" in resp.text


def test_submit_stores_rating_and_advances(admin):
    token = create_reviewer(admin)
    reviewer = _get_reviewer(token)
    resp = _rate(admin, token, 1)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"/review/{token}/next"

    session = SessionLocal()
    try:
        rating = session.query(Rating).filter(Rating.token_id == reviewer.id, Rating.position == 1).one()
        assert rating.manufacturer_rating == 5
        assert rating.models_rating == 4
        assert rating.model_years_rating == 3
        assert [rating.document_id, rating.model_name] == reviewer.item_order[0]
        assert rating.updated_at is None
    finally:
        session.close()

    resp = admin.get(f"/review/{token}/next", follow_redirects=False)
    assert resp.headers["location"] == f"/review/{token}/item/2"


def test_resubmit_updates_rating(admin):
    token = create_reviewer(admin)
    reviewer = _get_reviewer(token)
    _rate(admin, token, 1, m=5, mo=5, my=5)
    _rate(admin, token, 1, m=2, mo=1, my=3)

    session = SessionLocal()
    try:
        ratings = session.query(Rating).filter(Rating.token_id == reviewer.id, Rating.position == 1).all()
        assert len(ratings) == 1
        assert ratings[0].manufacturer_rating == 2
        assert ratings[0].updated_at is not None
    finally:
        session.close()


def test_out_of_range_rating_not_stored(admin):
    token = create_reviewer(admin)
    reviewer = _get_reviewer(token)
    resp = _rate(admin, token, 1, m=6)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"/review/{token}/item/1"

    session = SessionLocal()
    try:
        assert session.query(Rating).filter(Rating.token_id == reviewer.id).count() == 0
    finally:
        session.close()


def test_break_shown_exactly_at_end_of_block1(admin):
    token = create_reviewer(admin)
    for position in range(1, 30):
        resp = _rate(admin, token, position)
        assert resp.headers["location"] == f"/review/{token}/next"

    resp = _rate(admin, token, 30)
    assert resp.headers["location"] == f"/review/{token}/break"

    break_page = admin.get(f"/review/{token}/break")
    assert break_page.status_code == 200
    assert "Halfway" in break_page.text

    # Revising a block-1 item later does not re-trigger the break
    _rate(admin, token, 31)
    resp = _rate(admin, token, 15)
    assert resp.headers["location"] == f"/review/{token}/next"


def test_completion_sets_timestamp_and_shows_thank_you(admin):
    token = create_reviewer(admin)
    for position in range(1, 61):
        _rate(admin, token, position)

    reviewer = _get_reviewer(token)
    assert reviewer.completed_at is not None

    resp = admin.get(f"/review/{token}/next", follow_redirects=False)
    assert resp.headers["location"] == f"/review/{token}/thank-you"

    page = admin.get(f"/review/{token}/thank-you")
    assert "Thank you" in page.text


def test_deactivated_token_rejected(admin):
    token = create_reviewer(admin)
    reviewer = _get_reviewer(token)
    admin.post(f"/admin/deactivate/{reviewer.id}", follow_redirects=False)

    resp = admin.get(f"/review/{token}")
    assert "not valid" in resp.text
    resp = _rate(admin, token, 1)
    assert resp.headers["location"] == f"/review/{token}"


def test_admin_requires_login(client):
    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/admin/login"
    resp = client.get("/admin/export", follow_redirects=False)
    assert resp.status_code == 302
