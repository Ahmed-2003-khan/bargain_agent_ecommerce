import asyncio
from orchestrator.graph.state import AgentState
from orchestrator.graph.nodes import nlu_node, brain_node, mouth_node


async def test_flow():
    state: AgentState = {
        "session_id": "test-session-123",
        "mam": 500,
        "user_input": "I can pay 450",
        "history": [],
        "brain_action": None,
        "final_response": None
    }

    state = await nlu_node(state)
    print("NLU OK:", state)

    state = await brain_node(state)
    print("BRAIN OK:", state)

    state = await mouth_node(state)
    print("MOUTH OK:", state)


if __name__ == "__main__":
    asyncio.run(test_flow())
