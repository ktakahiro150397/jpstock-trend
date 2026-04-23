from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import Base, engine, get_db
from app.models import AnalysisResult
from app.services.ingest_service import ingest_market_data
from app.services.signal_service import run_analysis
from app.services.test_data_service import delete_test_ticker_data, generate_test_price_bars

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        client_kwargs={"scope": "openid email profile"},
    )


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def require_login(request: Request) -> dict:
    if settings.auth_skip_enabled:
        return {"email": settings.auth_skip_email, "name": settings.auth_skip_name}
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="login required")
    return user


def parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="as_of_date must be YYYY-MM-DD") from exc


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    as_of_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_login),
):
    stmt = select(AnalysisResult)
    selected_date: date | None = None
    if as_of_date:
        selected_date = parse_iso_date(as_of_date)
        stmt = stmt.where(AnalysisResult.as_of_date == selected_date)
    rows = db.scalars(stmt.order_by(AnalysisResult.analyzed_at.desc()).limit(100)).all()
    latest_by_ticker: dict[str, AnalysisResult] = {}
    for row in rows:
        if row.ticker not in latest_by_ticker:
            latest_by_ticker[row.ticker] = row
    ranked = sorted(latest_by_ticker.values(), key=lambda x: x.total_score, reverse=True)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "results": ranked,
            "selected_date": selected_date,
            "auth_skip_enabled": settings.auth_skip_enabled,
        },
    )


@app.get("/symbols/{ticker}", response_class=HTMLResponse)
def symbol_detail(ticker: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_login)):
    rows = db.scalars(
        select(AnalysisResult).where(AnalysisResult.ticker == ticker).order_by(AnalysisResult.analyzed_at.desc()).limit(20)
    ).all()
    return templates.TemplateResponse(
        "symbol.html", {"request": request, "user": user, "ticker": ticker, "rows": rows}
    )


@app.post("/jobs/analyze")
def trigger_analysis(
    _: Request,
    as_of_date: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_login),
):
    parsed_date = parse_iso_date(as_of_date) if as_of_date else None
    results = run_analysis(db, run_type="manual", as_of_date=parsed_date)
    return {"count": len(results), "candidates": [r.ticker for r in results if r.status == "entry_candidate"]}


@app.post("/jobs/ingest")
def trigger_ingest(
    _: Request,
    as_of_date: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_login),
):
    parsed_date = parse_iso_date(as_of_date) if as_of_date else None
    result = ingest_market_data(db, as_of_date=parsed_date)
    return result


@app.post("/jobs/test-data/generate")
def generate_test_data(
    _: Request,
    ticker: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    start_price: float = Form(default=1000.0),
    drift: float = Form(default=0.0002),
    volatility: float = Form(default=0.02),
    seed: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_login),
):
    del user
    try:
        result = generate_test_price_bars(
            db,
            ticker=ticker.strip().upper(),
            start_date=parse_iso_date(start_date),
            end_date=parse_iso_date(end_date),
            start_price=start_price,
            drift=drift,
            volatility=volatility,
            seed=seed,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/jobs/test-data/delete")
def delete_test_data(
    _: Request,
    ticker: str = Form(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_login),
):
    del user
    return delete_test_ticker_data(db, ticker=ticker.strip().upper())


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/login")
async def login(request: Request):
    if settings.auth_skip_enabled:
        request.session["user"] = {"email": settings.auth_skip_email, "name": settings.auth_skip_name}
        return RedirectResponse(url="/", status_code=302)
    if "google" not in oauth:
        raise HTTPException(status_code=500, detail="google oauth is not configured")
    redirect_uri = settings.google_oauth_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    if "google" not in oauth:
        raise HTTPException(status_code=500, detail="google oauth is not configured")
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    email = (user_info or {}).get("email", "").lower()
    if settings.allowed_email_list and email not in settings.allowed_email_list:
        raise HTTPException(status_code=403, detail="not allowed")
    request.session["user"] = {"email": email, "name": (user_info or {}).get("name", email)}
    return RedirectResponse(url="/", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
