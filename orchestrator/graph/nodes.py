from orchestrator.graph.state import AgentState
from orchestrator.lib.nlu_client import call_nlu
from orchestrator.lib.brain_client import call_brain
from orchestrator.lib.phraser_client import call_phraser
from orchestrator.lib.intents import Intent
import logging

logger = logging.getLogger("orchestrator_nodes")


# ---------- NLU NODE ----------
async def nlu_node(state: AgentState):

    try:
        nlu = await call_nlu(
            state["user_input"],
            session_id=state["session_id"]
        )

    except Exception as e:
        # Safe fallback if NLU fails — use UNKNOWN intent, not a raw string
        nlu = {
            "intent": Intent.UNKNOWN,
            "sentiment": "neutral",
            "entities": {}
        }

    state["intent"] = nlu.get("intent", Intent.UNKNOWN)
    state["sentiment"] = nlu.get("sentiment", "neutral")
    state["user_offer"] = nlu.get("entities", {}).get("PRICE", 0)

    logger.info("NLU RAW: %s", nlu)


    return state


# ---------- BRAIN NODE ----------
async def brain_node(state: AgentState):

    try:
        brain = await call_brain(
            mam=state["mam"],
            asking_price=state["asking_price"],
            user_offer=state.get("user_offer", 0),
            user_intent=state.get("intent", Intent.UNKNOWN),
            user_sentiment=state.get("sentiment", "neutral"),
            session_id=state["session_id"],
            history=state.get("history", []),
        )

    except Exception:
        # Safe fallback if Brain fails
        brain = {
            "action": "COUNTER",
            "counter_price": state["asking_price"],
            "response_key": "SAFE_FALLBACK",
            # 🔥 REQUIRED BY MS5 SCHEMA
            "policy_type": "rule-based",
            "policy_version": "fallback",
            "decision_metadata": {"reason": "brain_failed"}
        }

    # ⭐ Structured state mapping
    state["brain_action"] = brain.get("action")
    state["counter_price"] = brain.get("counter_price")
    state["response_key"] = brain.get("response_key")

    
    # ⭐ Guarantee MS5 contract fields
    brain.setdefault("policy_type", "rule-based")
    brain.setdefault("policy_version", "v1")
    brain.setdefault("decision_metadata", {})

    # ⭐ RAW brain output for Mouth
    state["_brain_raw"] = brain
    logger.info("BRAIN RAW: %s", brain)


    return state

# ----------- MOUTH NODE ----------

async def mouth_node(state: AgentState):

    brain = state.get("_brain_raw")

    if not brain:
        state["final_response"] = "Brain missing. Please repeat."
        return state

    try:
        ms5 = await call_phraser(brain)

        logger.info("PHRASER RAW RESPONSE: %s", ms5)

        # ⭐ UNIVERSAL EXTRACTION
        response_text = (
            ms5.get("response_text")
            or ms5.get("response")
            or ms5.get("text")
            or ms5.get("message")
        )

        # ⭐ Nested extraction
        if not response_text and isinstance(ms5.get("data"), dict):
            response_text = (
                ms5["data"].get("response_text")
                or ms5["data"].get("response")
                or ms5["data"].get("text")
            )

        if not response_text:
            response_text = str(ms5)

        state["final_response"] = response_text

    except Exception as e:
        logger.exception("Mouth Error: %s", e)
        state["final_response"] = "System is thinking. Please try again."

    return state


# ---------- FAST TRACK NODE ----------
async def fast_track_node(state: AgentState):
    """
    Handles conversational intents that do NOT need the Strategy Engine.

    Routes these intents directly to the Phraser using matching response_keys:
        GREET              → GREET_HELLO
        BYE                → BYE_GOODBYE
        DEAL               → DEAL_ACCEPTED
        ASK_PREVIOUS_OFFER → PREVIOUS_OFFER   (passes metadata from history)

    Builds a mock brain dict so the Phraser (mouth_node) can consume it
    using the same code path — no special handling needed in mouth_node.
    """
    intent = state.get("intent", Intent.UNKNOWN)

    # Map each fast-track intent to its Phraser response_key
    FAST_TRACK_MAP = {
        Intent.GREET:              ("GREETING",          "GREET_HELLO"),
        Intent.BYE:                ("FAREWELL",          "BYE_GOODBYE"),
        Intent.DEAL:               ("ACCEPT",            "DEAL_ACCEPTED"),
        Intent.ASK_PREVIOUS_OFFER: ("INFO",              "PREVIOUS_OFFER"),
    }

    action, response_key = FAST_TRACK_MAP.get(intent, ("INFO", "DEFAULT"))

    # For PREVIOUS_OFFER: extract last known user and bot prices from history
    decision_metadata = {}
    if intent == Intent.ASK_PREVIOUS_OFFER:
        history = state.get("history", [])
        last_bot_offer = None
        last_user_offer = None
        for turn in reversed(history):
            if not last_bot_offer and turn.get("from") in ("ina", "bot", "assistant"):
                if turn.get("brain_key") in ("STANDARD_COUNTER", "COUNTER_FINAL_OFFER", "ACCEPT_FINAL"):
                    last_bot_offer = turn.get("counter_price")
            if not last_user_offer and turn.get("from") == "user":
                last_user_offer = turn.get("text")
        decision_metadata = {
            "bot_offer": last_bot_offer or "N/A",
            "user_offer": last_user_offer or "N/A",
        }

    # Build a mock brain output shaped exactly like Strategy Engine output
    mock_brain = {
        "action":            action,
        "response_key":      response_key,
        "counter_price":     None,
        "policy_type":       "fast-track",
        "policy_version":    "1.0",
        "decision_metadata": decision_metadata,
    }

    state["brain_action"] = action
    state["response_key"] = response_key
    state["_brain_raw"]   = mock_brain

    logger.info("FAST TRACK: intent=%s → action=%s, key=%s", intent, action, response_key)
    return state

