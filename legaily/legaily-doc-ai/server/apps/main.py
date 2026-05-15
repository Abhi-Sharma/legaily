from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

from apps.routes import router

# ---------------------------------------------------------------------------
# Startup: pre-warm SLRE singleton so the first user request is instant
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server startup: pre-warming SLRE models...")
    try:
        from apps.services.slre import _get_embeddings, _get_vectorstore
        _get_embeddings()
        vs = _get_vectorstore()
        logger.info("SLRE ready: %d vectors loaded.", vs.index.ntotal)
    except Exception as e:
        logger.warning("SLRE pre-warm failed (non-fatal): %s", e)
    yield  # server runs here
    logger.info("Server shutdown.")

# ✅ Create the FastAPI instance only once
app = FastAPI(
    title="Legaily Doc AI API",
    description="API for OCR, Summarization, and Translation of uploaded documents",
    version="1.0.0",
    lifespan=lifespan,
)

# ✅ CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root route
@app.get("/")
async def root():
    return {"message": "Welcome to Legaily Doc AI API"}

# ✅ Register router with prefix
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
