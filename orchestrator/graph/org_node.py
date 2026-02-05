import httpx
from orchestrator.graph.state import AgentState

# --- CONFIG ---
NLU_URL = "http://nlu-service:8000/parse"
BRAIN_URL = "http://strategy-engine:8000/decide"
MOUTH_URL = "http://llm-phraser:8000/respond"

TIMEOUT = 5.0


# -------------------------
# NLU NODE
# -------------------------
async def nlu_node(state: AgentState) -> AgentState:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            NLU_URL,
            json={
                "text": state["user_input"]
            }
        )
        response.raise_for_status()
        nlu_data = response.json()

    state["history"].append({
        "role": "user",
        "content": state["user_input"]
    })

    state["user_offer"] = nlu_data.get("price")
    state["intent"] = nlu_data.get("intent")

    return state


# -------------------------
# BRAIN NODE
# -------------------------
async def brain_node(state: AgentState) -> AgentState:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            BRAIN_URL,
            json={
                "session_id": state["session_id"],
                "user_offer": state.get("user_offer"),
                "mam": state["mam"],
                "history": state["history"]
            }
        )
        response.raise_for_status()
        brain_data = response.json()

    state["brain_action"] = brain_data.get("action")
    state["counter_price"] = brain_data.get("counter_price")

    return state


# -------------------------
# MOUTH NODE
# -------------------------
async def mouth_node(state: AgentState) -> AgentState:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            MOUTH_URL,
            json={
                "action": state["brain_action"],
                "counter_price": state.get("counter_price"),
                "history": state["history"]
            }
        )
        response.raise_for_status()
        mouth_data = response.json()

    final_text = mouth_data.get("text")

    state["history"].append({
        "role": "assistant",
        "content": final_text
    })

    state["final_response"] = final_text

    return state
