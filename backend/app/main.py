import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_generate import router as generate_router
from app.api.routes_images import router as images_router
from app.api.routes_models import router as models_router
from app.api.routes_ws import router as ws_router
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.deps import init_all
    logger.info("image-gen-agent backend starting")
    init_all()
    yield
    logger.info("image-gen-agent backend stopping")


app = FastAPI(title="image-gen-agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(generate_router)
app.include_router(chat_router)
app.include_router(images_router)
app.include_router(models_router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
