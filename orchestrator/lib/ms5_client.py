import os
import httpx
import logging

logger = logging.getLogger("ms5_client")

LLM_PHRASER_URL = os.getenv("LLM_PHRASER_URL", "http://llm-phraser:8000")
INTERNAL_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")


async def call_mouth(brain_output: dict):

    ms5_payload = {
        "action": brain_output.get("action"),
        "response_key": brain_output.get("response_key"),
        "counter_price": brain_output.get("counter_price") or 0,

        "policy_type": brain_output.get("policy_type", "rule-based"),
        "policy_version": brain_output.get("policy_version", "v1"),
        "decision_metadata": brain_output.get("decision_metadata", {}),
    }

    headers = {"X-Internal-Key": INTERNAL_KEY}

    logger.info(f"[MS5] Sending payload → Mouth: {ms5_payload}")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{LLM_PHRASER_URL}/phrase",
                json=ms5_payload,
                headers=headers,
            )

            resp.raise_for_status()
            data = resp.json()

            logger.info(f"[MS5] RAW RESPONSE ← {data}")

            return data

    except Exception as e:
        logger.exception(f"MS5 error: {e}")
        return {
            "response_text": "Let me think about that for a moment."
        }
