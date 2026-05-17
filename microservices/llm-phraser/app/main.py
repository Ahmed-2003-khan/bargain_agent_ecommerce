# Purpose: Initializes the FastAPI application and defines API endpoints.

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from .schemas import PhraserInput, PhraserOutput
from prometheus_fastapi_instrumentator import Instrumentator
from dotenv import load_dotenv

# --- Load environment variables from .env file ---
load_dotenv()

from .llm_client import generate_llm_response

from openai import AsyncOpenAI
from groq import AsyncGroq

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------- Internal Service Key ----------------------
INTERNAL_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")

# --- API Key and Client Management ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set — OpenAI primary will be unavailable.")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not set — Groq fallback will be unavailable.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    app.state.groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    logger.info(
        "LLM clients initialized — OpenAI: %s, Groq: %s",
        "ready" if app.state.openai_client else "unavailable",
        "ready" if app.state.groq_client else "unavailable",
    )
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="INA LLM Phraser (MS 5 - The Mouth)",
    description="This service receives a *command* (not secrets) "
    "and phrases it persuasively using an LLM.",
    version="1.0.0",
    lifespan=lifespan,
)

# Prometheus Instrumentation
Instrumentator().instrument(app).expose(app)


# ---------------------- Auth Middleware ----------------------
@app.middleware("http")
async def verify_internal_key(request: Request, call_next):
    """
    Verify that incoming requests carry the correct X-Internal-Key header.
    Health check endpoint is exempt so Docker/k8s healthchecks still work.
    """
    if request.url.path in ("/health", "/", "/docs", "/openapi.json"):
        return await call_next(request)

    incoming_key = request.headers.get("X-Internal-Key", "")
    if not INTERNAL_KEY or incoming_key != INTERNAL_KEY:
        logger.warning(f"Unauthorized request to {request.url.path} — key mismatch")
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden: Invalid internal service key."},
        )

    return await call_next(request)


# --- Health Check Endpoint ---
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok", "service": "llm-phraser"}


# --- LLM Phrasing Endpoint ---
@app.post("/api/v1/phrase", response_model=PhraserOutput)
async def generate_phrase(input_data: PhraserInput):
    """
    Receives a command from the Strategy Engine (MS 4) and
    generates a persuasive, natural language response.

    Uses OpenAI GPT-4o as primary, falls back to Groq if unavailable.
    """
    try:
        response_text = await generate_llm_response(
            input_data,
            openai_client=app.state.openai_client,
            groq_client=app.state.groq_client,
        )
        return PhraserOutput(response_text=response_text)

    except Exception as e:
        logger.error(f"Unhandled error in /phrase endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal server error occurred."
        )
