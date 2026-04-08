import os
import httpx
import logging

logger = logging.getLogger("nlu_client")

NLU_URL = os.getenv("NLU_SERVICE_URL", "http://nlu-service:8000")
INTERNAL_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")


async def call_nlu(text: str, session_id: str):
    payload = {
        "text": text,
        "session_id": session_id
    }

    headers = {"X-Internal-Key": INTERNAL_KEY}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{NLU_URL}/parse",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.exception(f"NLU error: {e}")
        return {
            "intent": "unknown",
            "entities": {"PRICE": None},
            "sentiment": "neutral"
        }
