import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from database import Base, engine
from routes.admin import router as admin_router
from routes.review import router as review_router

logger = logging.getLogger("uvicorn.error")


async def _init_db():
    """Create tables in background with retries so the app starts immediately."""
    for attempt in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return
        except Exception as e:
            logger.warning(f"DB init attempt {attempt + 1}/10 failed: {e}")
            await asyncio.sleep(2)
    logger.error("Failed to initialize database after 10 attempts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_init_db())
    yield


app = FastAPI(title="Recall Extraction Human Evaluation", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(admin_router)
app.include_router(review_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/login")


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
