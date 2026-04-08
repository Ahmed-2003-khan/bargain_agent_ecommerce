"""
INA Orchestrator — Main Application

Auth Model:
    The monolith backend validates tenant API keys and creates sessions
    in Redis. The session_id returned to the tenant frontend acts as the
    auth token. On every /chat request, the orchestrator validates this
    session_id exists in Redis and has the correct structure.

    Flow: Tenant → Monolith (API key) → Redis session → Orchestrator (session_id)
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from orchestrator.lib import state_manager
from orchestrator.graph.workflow import build_workflow
from orchestrator.session_schemas import SessionData

# ---------------------- Logging ----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")

# 🔥 Build Graph Once (Startup Time)
graph_app = build_workflow()


# ---------------------- Lifespan ----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("INA Orchestrator starting up...")
    yield
    logger.info("INA Orchestrator shutting down...")
    await state_manager.close_redis()


# ---------------------- App Init ----------------------
app = FastAPI(title="INA Orchestrator", lifespan=lifespan)

# ---------------------- CORS ----------------------
# Allowed origins — comma-separated in env, default "*" for development.
# Production mein specific tenant domains set karo:
#   ALLOWED_ORIGINS=https://tenant1.com,https://tenant2.com
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    ["*"] if _raw_origins.strip() == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------- Schemas ----------------------
class ChatInput(BaseModel):
    session_id: str
    message: str


class ChatOutput(BaseModel):
    response: str


# =====================================================
# 🔐 AUTH DEPENDENCY — Session Validation
# =====================================================
async def validate_session(payload: ChatInput) -> SessionData:
    """
    FastAPI dependency that validates the session from Redis.

    Auth logic:
        1. Session ID se Redis mein session fetch karo.
        2. Agar session nahi mili → 401 Unauthorized (invalid/expired).
        3. Agar session structure corrupt hai → 401 Unauthorized (invalid data).
        4. Valid session return karo as a Pydantic SessionData object.

    Usage:
        @app.post("/ina/v1/chat")
        async def chat(payload: ChatInput, session: SessionData = Depends(validate_session)):
            # session is guaranteed to be valid here
    """
    redis_key = f"session:{payload.session_id}"

    # 1. Fetch session from Redis
    raw_session = await state_manager.get_session(redis_key)

    if raw_session is None:
        logger.warning(
            "Auth failed: session not found — session_id=%s", payload.session_id
        )
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or expired session ID.",
        )

    # 2. Validate session structure
    try:
        session = SessionData(**raw_session)
    except ValidationError as e:
        logger.warning(
            "Auth failed: corrupt session data — session_id=%s errors=%s",
            payload.session_id,
            e.errors(),
        )
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Session data is invalid or incomplete.",
        )

    return session


# ---------------------- Health ----------------------
@app.get("/")
async def home():
    return {"message": "Orchestrator is running!"}


@app.get("/ping-redis")
async def ping_redis():
    ok = await state_manager.ping_redis()
    if not ok:
        raise HTTPException(status_code=503, detail="Redis not reachable")

    test_sid = "ping-test-session"
    success = await state_manager.set_session(test_sid, {"hello": "redis"})
    data = await state_manager.get_session(test_sid)

    return {"redis_ping": ok, "write_ok": success, "read_data": data}


@app.get("/health")
async def health_check():
    redis_ok = await state_manager.ping_redis()
    return {"status": "ok" if redis_ok else "degraded"}


# =====================================================
# 🔥 MAIN CHAT ENDPOINT (Session-Authenticated)
# =====================================================
@app.post("/ina/v1/chat", response_model=ChatOutput)
async def chat_endpoint(
    payload: ChatInput,
    session: SessionData = Depends(validate_session),
):
    """
    Main chat endpoint. Auth is handled by the validate_session dependency —
    if we reach this function body, the session is guaranteed to be valid.
    """

    try:
        redis_key = f"session:{payload.session_id}"

        # ------------------------------------------------
        # 1️⃣ Read business inputs from validated session
        # ------------------------------------------------
        mam = session.mam
        asking_price = session.asking_price

        # ------------------------------------------------
        # 2️⃣ Append user message to history
        # ------------------------------------------------
        # Work with the raw list from the session model
        history = list(session.messages)
        history.append({
            "from": "user",
            "text": payload.message,
        })

        # ------------------------------------------------
        # 3️⃣ LangGraph Execution
        # ------------------------------------------------
        try:
            state = {
                "session_id": redis_key,
                "mam": mam,
                "asking_price": asking_price,
                "user_input": payload.message,
                "history": history,
            }

            result = await graph_app.ainvoke(state)

            ai_response = result.get(
                "final_response",
                "Let me think about that for a moment.",
            )
            brain_action = result.get("brain_action")
            brain_key = result.get("response_key")

        except Exception:
            logger.exception("Graph failed, using safe fallback")
            ai_response = (
                "Let me think about that for a moment. "
                "Could you please try again?"
            )
            brain_action = "FALLBACK"
            brain_key = "GRAPH_FAIL"

        # ------------------------------------------------
        # 4️⃣ Save updated history back to Redis
        # ------------------------------------------------
        history.append({
            "from": "ina",
            "text": ai_response,
            "brain_action": brain_action,
            "brain_key": brain_key,
        })

        # Rebuild the full session dict for Redis storage
        updated_session = session.model_dump()
        updated_session["messages"] = history
        await state_manager.set_session(redis_key, updated_session)

        return ChatOutput(response=ai_response)

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            "Unexpected error for session %s: %s", payload.session_id, e
        )
        raise HTTPException(status_code=500, detail="Internal server error")
