import csv
import io

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer
from sqlalchemy.orm import Session

from config import ADMIN_PASSWORD, BASE_URL, FIELDS, SECRET_KEY
from data_loader import get_document_ids, get_model_names
from database import get_db
from models import Rating, ReviewerToken
from randomization import generate_item_order

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")
signer = URLSafeSerializer(SECRET_KEY)

COOKIE_NAME = "admin_session"


def _is_authenticated(request: Request) -> bool:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return False
    try:
        data = signer.loads(cookie)
        return data.get("authenticated") is True
    except Exception:
        return False


def _require_auth(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse("/admin/login", status_code=302)
    return None


def _token_stats(token: ReviewerToken) -> dict:
    total = len(token.item_order)
    rated = len({r.position for r in token.ratings})
    return {
        "id": token.id,
        "token": token.token,
        "reviewer_name": token.reviewer_name,
        "reviewer_email": token.reviewer_email,
        "is_active": token.is_active,
        "created_at": token.created_at,
        "completed_at": token.completed_at,
        "total": total,
        "rated": rated,
        "pct": round(rated / total * 100) if total else 0,
    }


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            request, "admin/login.html", {"error": "Invalid password"}
        )
    response = RedirectResponse("/admin/", status_code=302)
    response.set_cookie(COOKIE_NAME, signer.dumps({"authenticated": True}), httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), generated_url: str = None):
    redirect = _require_auth(request)
    if redirect:
        return redirect

    tokens = db.query(ReviewerToken).order_by(ReviewerToken.created_at.desc()).all()
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "tokens": [_token_stats(t) for t in tokens],
        "base_url": BASE_URL,
        "generated_url": None,
        "token_reviewer": None,
    })


@router.post("/create-token", response_class=HTMLResponse)
async def create_token(
    request: Request,
    db: Session = Depends(get_db),
    reviewer_name: str = Form(...),
    reviewer_email: str = Form(""),
):
    redirect = _require_auth(request)
    if redirect:
        return redirect

    item_order = generate_item_order(get_document_ids(), get_model_names())
    token = ReviewerToken(
        reviewer_name=reviewer_name.strip(),
        reviewer_email=reviewer_email.strip() or None,
        item_order=item_order,
    )
    db.add(token)
    db.commit()

    tokens = db.query(ReviewerToken).order_by(ReviewerToken.created_at.desc()).all()
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "tokens": [_token_stats(t) for t in tokens],
        "base_url": BASE_URL,
        "generated_url": f"{BASE_URL}/review/{token.token}",
        "token_reviewer": token.reviewer_name,
    })


@router.post("/deactivate/{token_id}")
async def deactivate_token(token_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = _require_auth(request)
    if redirect:
        return redirect

    token = db.query(ReviewerToken).filter(ReviewerToken.id == token_id).first()
    if token:
        token.is_active = False
        db.commit()
    return RedirectResponse("/admin/", status_code=302)


@router.post("/reactivate/{token_id}")
async def reactivate_token(token_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = _require_auth(request)
    if redirect:
        return redirect

    token = db.query(ReviewerToken).filter(ReviewerToken.id == token_id).first()
    if token:
        token.is_active = True
        db.commit()
    return RedirectResponse("/admin/", status_code=302)


@router.get("/export")
async def export_csv(request: Request, db: Session = Depends(get_db)):
    """Long-format CSV of all ratings. Model identity is unblinded here only."""
    redirect = _require_auth(request)
    if redirect:
        return redirect

    ratings = (
        db.query(Rating)
        .join(ReviewerToken)
        .order_by(ReviewerToken.id, Rating.position)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "reviewer_name", "reviewer_email", "token", "position", "block",
        "document_id", "model_name", "field", "rating", "created_at", "updated_at",
    ])

    for r in ratings:
        t = r.token
        half = len(t.item_order) // 2
        block = 1 if r.position <= half else 2
        for f in FIELDS:
            writer.writerow([
                t.reviewer_name,
                t.reviewer_email or "",
                t.token,
                r.position,
                block,
                r.document_id,
                r.model_name,
                f["key"],
                getattr(r, f"{f['key']}_rating"),
                r.created_at.isoformat() if r.created_at else "",
                r.updated_at.isoformat() if r.updated_at else "",
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=human_eval_ratings.csv"},
    )
