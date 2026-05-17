# Purpose: Isolates all external LLM API logic.
# Primary: OpenAI GPT-4o | Fallback: Groq llama-3.3-70b-versatile

import os
import logging
from typing import Optional

from openai import AsyncOpenAI
from groq import AsyncGroq
from .schemas import PhraserInput
from .prompt_templates import get_formatted_prompt

logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_PHRASER_MODEL", "gpt-4o")
GROQ_MODEL = os.getenv("GROQ_PHRASER_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))


async def _call_openai(
    system_prompt: str, user_prompt: str, client: AsyncOpenAI
) -> str:
    """Call OpenAI GPT-4o and return the response text."""
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=LLM_TEMPERATURE,
        max_tokens=512,
    )
    return response.choices[0].message.content or ""


async def _call_groq(
    system_prompt: str, user_prompt: str, client: AsyncGroq
) -> str:
    """Call Groq as fallback and return the response text."""
    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=LLM_TEMPERATURE,
        max_tokens=512,
    )
    return response.choices[0].message.content or ""


async def generate_llm_response(
    input_data: PhraserInput,
    openai_client: Optional[AsyncOpenAI] = None,
    groq_client: Optional[AsyncGroq] = None,
) -> str:
    """
    Generate a persuasive response using LLM.
    Strategy: OpenAI GPT-4o primary → Groq fallback → static fallback.
    """
    system_prompt, user_prompt = get_formatted_prompt(input_data)

    logger.info("Generating phrase for key: %s", input_data.response_key)

    # --- Primary: OpenAI GPT-4o ---
    if openai_client:
        try:
            response_text = await _call_openai(system_prompt, user_prompt, openai_client)
            if response_text:
                logger.info("[Phraser] OpenAI response generated successfully")
                return response_text
        except Exception as e:
            logger.warning("[Phraser] OpenAI failed (%s) — falling back to Groq", e)

    # --- Fallback: Groq ---
    if groq_client:
        try:
            response_text = await _call_groq(system_prompt, user_prompt, groq_client)
            if response_text:
                logger.info("[Phraser] Groq fallback response generated successfully")
                return response_text
        except Exception as e:
            logger.error("[Phraser] Groq fallback also failed: %s", e)

    # --- Static fallback ---
    logger.error("[Phraser] All LLM providers failed — returning static fallback")
    return "Let me think about that for a moment. Could you please try again?"
