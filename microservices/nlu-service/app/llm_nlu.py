"""
LLM-Based NLU Parser using LangChain + Groq.

Uses ChatGroq with structured output (Pydantic) for type-safe,
deterministic NLU extraction. LangChain handles prompt templating,
output parsing, and retries automatically.

Model: llama-3.1-8b-instant (fastest, cheapest Groq model)
Temperature: 0.0 (fully deterministic)
"""

import logging
from typing import Optional, Literal

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured Output Schema — LangChain forces the LLM to match this exactly
# ---------------------------------------------------------------------------
class NLUParsed(BaseModel):
    """Structured NLU output that LangChain will enforce via tool calling."""

    intent: Literal[
        "GREET", "BYE", "MAKE_OFFER", "DEAL",
        "ASK_QUESTION", "ASK_PREVIOUS_OFFER", "UNKNOWN", "INVALID"
    ] = Field(description="The user's intent classification")

    price: Optional[float] = Field(
        default=None,
        description="The price the user is offering. Only set if intent is MAKE_OFFER, otherwise null."
    )

    sentiment: Literal["positive", "neutral", "negative"] = Field(
        default="neutral",
        description="The user's emotional sentiment"
    )

    language: Literal["english", "roman_urdu", "urdu", "other"] = Field(
        default="english",
        description="The language the user is writing in."
    )

    error_message: Optional[str] = Field(
        default=None,
        description="If intent is INVALID, explain politely why the input was not accepted."
    )


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a strict NLU parser and offer validator for a price negotiation chatbot.
Your job is BOTH to classify intent AND to act as a smart gatekeeper — blocking any offer that is not a genuine, usable monetary value.

Intent classification rules:
- GREET: user is greeting (hi, hello, hey, good morning, etc.)
- BYE: user is saying goodbye (bye, see you, later, goodbye, etc.)
- MAKE_OFFER: user is proposing a VALID price — must be a clear, positive, realistic monetary number (e.g. "I'll give you 150", "how about $200", "a hundred bucks")
- DEAL: user is accepting/agreeing to a price (deal, accepted, agreed, I agree, let's do it, etc.)
- INVALID: use this when the offer or input is not genuinely usable. This includes:
    * Mathematical expressions or ratios (8/3, 4+4, x=2)
    * Negative or zero amounts (-500, 0)
    * Non-monetary offers ("I'll pay with my car", "my soul")
    * Gibberish or random characters ("asdfgh", "$$$$$")
    * Unrealistically large numbers above 10 million
    * Any other input that cannot be acted upon as a real offer
  When selecting INVALID, you MUST write a unique, polite, contextual error_message that explains exactly what was wrong and guides the user to fix it. Never use a generic or repetitive message.
- ASK_PREVIOUS_OFFER: user is asking about a previous/earlier offer or counter
- ASK_QUESTION: user is asking any other question about the product
- UNKNOWN: cannot understand, but not clearly invalid

A pre-check hint may be provided in brackets at the start of the message like [HINT: math_detected].
If a hint is provided, use it as strong evidence but still write a UNIQUE, CONTEXT-AWARE error_message based on the actual message content.

Price extraction rules:
- ONLY set price when intent is MAKE_OFFER
- Extract any explicitly mentioned price format into just the number, removing commas. Do not infer prices that aren't stated.
- Handle natural language: "a hundred and fifty" → 150.0, "1.5k" → 1500.0
- If NO price offer is being made, price MUST be null

Sentiment rules:
- positive: user seems happy, enthusiastic, or satisfied
- negative: user seems frustrated, angry, or dissatisfied
- neutral: everything else

Language detection rules:
- english: message is written in standard English
- roman_urdu: message is Urdu written in Roman/Latin letters (e.g. 'aap ka kia hal hai', 'deal karte hain')
- urdu: message is written in Urdu script (e.g. 'آپ کیسے ہیں')
- other: any other language (Arabic, Spanish, French, etc.)
"""


# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{text}"),
])


# ---------------------------------------------------------------------------
# Build the chain (called once at startup)
# ---------------------------------------------------------------------------
def build_nlu_chain(groq_api_key: str):
    """
    Build a LangChain chain that:
    1. Formats the user message into the prompt
    2. Calls Groq's llama3-8b-8192
    3. Forces structured output via with_structured_output(NLUParsed)
    4. Returns a validated NLUParsed Pydantic object

    This is the "structured output" pattern — LangChain uses tool calling
    under the hood to guarantee the LLM returns exactly the fields we need.
    """
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        max_tokens=150,
        api_key=groq_api_key,
    )

    # with_structured_output forces the LLM output to match our Pydantic model
    structured_llm = llm.with_structured_output(NLUParsed)

    # chain: prompt → structured LLM → NLUParsed object
    chain = prompt | structured_llm

    return chain


async def parse(text: str, chain, hint: str = "") -> dict:
    """
    Run the NLU chain on the user's text.

    Args:
        text:  The raw user message.
        chain: The LangChain chain to invoke.
        hint:  Optional Layer-1 pre-check reason (e.g. 'math_detected').
               Prepended to the message so the LLM uses it as strong evidence.

    Returns:
        dict with keys: intent, price, sentiment, language, error_message

    Raises:
        Exception on any LangChain/Groq failure → caller uses regex fallback.
    """
    # Prepend hint if Layer 1 detected something
    annotated_text = f"[HINT: {hint}] User message: {text}" if hint else f"User message: {text}"

    logger.info("[LLM NLU] Parsing: %r (hint=%r)", text, hint)

    result: NLUParsed = await chain.ainvoke({"text": annotated_text})

    logger.info("[LLM NLU] Parsed: intent=%s, price=%s, sentiment=%s, language=%s",
                result.intent, result.price, result.sentiment, result.language)

    return {
        "intent": result.intent,
        "price": result.price,
        "sentiment": result.sentiment,
        "language": result.language,
        "error_message": result.error_message,
    }
