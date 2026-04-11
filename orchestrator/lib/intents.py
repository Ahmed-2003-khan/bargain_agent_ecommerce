"""
Canonical Intent Constants — Single Source of Truth for the Orchestrator.

All intent strings used anywhere in the orchestrator flow MUST be imported
from here. Never hardcode intent strings — use these constants.

Intent values MUST exactly match what the NLU service returns.
See: microservices/nlu-service/app/llm_nlu.py NLUParsed.intent Literal values.
"""

from typing import Final


class Intent:
    # User is greeting the bot (hello, hi, hey)
    GREET: Final = "GREET"

    # User is ending the conversation (bye, goodbye)
    BYE: Final = "BYE"

    # User is explicitly proposing a price ("I offer 150", "how about 180?")
    MAKE_OFFER: Final = "MAKE_OFFER"

    # User is accepting the deal ("deal", "agreed", "I accept")
    DEAL: Final = "DEAL"

    # User is asking about the product or negotiation ("what colour is it?")
    ASK_QUESTION: Final = "ASK_QUESTION"

    # User is asking about a previous offer ("what was your last price?")
    ASK_PREVIOUS_OFFER: Final = "ASK_PREVIOUS_OFFER"

    # Anything the NLU couldn't classify
    UNKNOWN: Final = "UNKNOWN"

    # Intents that require the negotiation Strategy Engine
    NEGOTIATION_INTENTS: Final = frozenset({MAKE_OFFER, DEAL, ASK_PREVIOUS_OFFER})

    # Intents that are purely conversational (no Strategy Engine needed)
    CONVERSATIONAL_INTENTS: Final = frozenset({GREET, BYE, ASK_QUESTION, UNKNOWN})
