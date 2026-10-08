from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import CORRECTNESS_ANCHORS, FIELDS
from data_loader import get_item, get_recall_text
from database import get_db
from models import Rating, ReviewerToken

router = APIRouter(prefix="/review")
templates = Jinja2Templates(directory="templates")


def _get_valid_token(token_str: str, db: Session) -> ReviewerToken | None:
    return (
        db.query(ReviewerToken)
        .filter(ReviewerToken.token == token_str, ReviewerToken.is_active == True)
        .first()
    )


def _rated_positions(token: ReviewerToken) -> set[int]:
    return {r.position for r in token.ratings}


def _first_unrated(token: ReviewerToken) -> int | None:
    rated = _rated_positions(token)
    for pos in range(1, len(token.item_order) + 1):
        if pos not in rated:
            return pos
    return None


def _display_parts(value: str, display: str) -> list[str]:
    """Verbatim fields render as a single line exactly as the model returned
    them; list fields split on ";" into bullets."""
    value = (value or "").strip()
    if display == "verbatim":
        return [value or "(nothing extracted)"]
    parts = [p.strip() for p in value.split(";")]
    return [p for p in parts if p] or ["(nothing extracted)"]


@router.get("/{token}", response_class=HTMLResponse)
async def landing(token: str, request: Request, db: Session = Depends(get_db)):
    reviewer = _get_valid_token(token, db)
    if not reviewer:
        return templates.TemplateResponse(request, "review/invalid_token.html", {})

    total = len(reviewer.item_order)
    rated = len(_rated_positions(reviewer))

    return templates.TemplateResponse(request, "review/landing.html", {
        "token": token,
        "reviewer_name": reviewer.reviewer_name,
        "total_items": total,
        "rated": rated,
        "remaining": total - rated,
        "anchors": CORRECTNESS_ANCHORS,
        "fields": FIELDS,
    })


@router.get("/{token}/next")
async def next_item(token: str, db: Session = Depends(get_db)):
    reviewer = _get_valid_token(token, db)
    if not reviewer:
        return RedirectResponse(f"/review/{token}", status_code=302)

    pos = _first_unrated(reviewer)
    if pos is None:
        return RedirectResponse(f"/review/{token}/thank-you", status_code=302)
    return RedirectResponse(f"/review/{token}/item/{pos}", status_code=302)


@router.get("/{token}/item/{position}", response_class=HTMLResponse)
async def rate_item(token: str, position: int, request: Request, db: Session = Depends(get_db)):
    reviewer = _get_valid_token(token, db)
    if not reviewer:
        return templates.TemplateResponse(request, "review/invalid_token.html", {})

    total = len(reviewer.item_order)
    if position < 1 or position > total:
        return RedirectResponse(f"/review/{token}/next", status_code=302)

    document_id, model_name = reviewer.item_order[position - 1]
    item = get_item(document_id, model_name)
    recall_text = get_recall_text(document_id)

    existing = (
        db.query(Rating)
        .filter(Rating.token_id == reviewer.id, Rating.position == position)
        .first()
    )

    rated = _rated_positions(reviewer)
    fields = []
    for f in FIELDS:
        fields.append({
            **f,
            "parts": _display_parts(item[f["key"]], f["display"]) if item else ["(data unavailable)"],
            "existing_rating": getattr(existing, f"{f['key']}_rating", None) if existing else None,
        })

    return templates.TemplateResponse(request, "review/item.html", {
        "token": token,
        "position": position,
        "total_items": total,
        "block_size": total // 2,
        "recall_text": recall_text,
        "fields": fields,
        "existing": existing is not None,
        "rated_positions": sorted(rated),
        "rated_count": len(rated),
        "progress_pct": len(rated) / total * 100 if total else 0,
        "anchors": CORRECTNESS_ANCHORS,
    })


@router.post("/{token}/item/{position}")
async def submit_rating(
    token: str,
    position: int,
    db: Session = Depends(get_db),
    manufacturer_rating: int = Form(...),
    models_rating: int = Form(...),
    model_years_rating: int = Form(...),
):
    reviewer = _get_valid_token(token, db)
    if not reviewer:
        return RedirectResponse(f"/review/{token}", status_code=302)

    total = len(reviewer.item_order)
    if position < 1 or position > total:
        return RedirectResponse(f"/review/{token}/next", status_code=302)

    values = {
        "manufacturer_rating": manufacturer_rating,
        "models_rating": models_rating,
        "model_years_rating": model_years_rating,
    }
    if not all(1 <= v <= 5 for v in values.values()):
        return RedirectResponse(f"/review/{token}/item/{position}", status_code=302)

    document_id, model_name = reviewer.item_order[position - 1]

    existing = (
        db.query(Rating)
        .filter(Rating.token_id == reviewer.id, Rating.position == position)
        .first()
    )
    if existing:
        for key, val in values.items():
            setattr(existing, key, val)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(Rating(
            token_id=reviewer.id,
            position=position,
            document_id=document_id,
            model_name=model_name,
            **values,
        ))
    db.commit()
    db.refresh(reviewer)

    rated = _rated_positions(reviewer)
    if len(rated) == total and reviewer.completed_at is None:
        reviewer.completed_at = datetime.now(timezone.utc)
        db.commit()

    # Break interstitial: shown once, when block 1 is done and block 2 untouched
    half = total // 2
    block1_done = all(p in rated for p in range(1, half + 1))
    block2_untouched = not any(p in rated for p in range(half + 1, total + 1))
    if block1_done and block2_untouched:
        return RedirectResponse(f"/review/{token}/break", status_code=302)

    return RedirectResponse(f"/review/{token}/next", status_code=302)


@router.get("/{token}/break", response_class=HTMLResponse)
async def halfway_break(token: str, request: Request, db: Session = Depends(get_db)):
    reviewer = _get_valid_token(token, db)
    if not reviewer:
        return templates.TemplateResponse(request, "review/invalid_token.html", {})

    total = len(reviewer.item_order)
    return templates.TemplateResponse(request, "review/break.html", {
        "token": token,
        "half": total // 2,
        "total_items": total,
    })


@router.get("/{token}/thank-you", response_class=HTMLResponse)
async def thank_you(token: str, request: Request, db: Session = Depends(get_db)):
    reviewer = _get_valid_token(token, db)
    if not reviewer:
        return templates.TemplateResponse(request, "review/invalid_token.html", {})

    return templates.TemplateResponse(request, "review/thank_you.html", {
        "token": token,
        "total_items": len(reviewer.item_order),
        "reviewer_name": reviewer.reviewer_name,
    })
