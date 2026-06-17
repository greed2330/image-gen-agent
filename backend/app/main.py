import logging

from fastapi import FastAPI

from app.api.routes_chat import router as chat_router
from app.api.routes_generate import router as generate_router
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="image-gen-agent", version="0.1.0")
app.include_router(generate_router)
app.include_router(chat_router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("image-gen-agent backend starting")


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("image-gen-agent backend stopping")
