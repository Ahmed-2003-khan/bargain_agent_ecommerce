import asyncio

from orchestrator.graph.workflow import build_workflow
from orchestrator.graph.state import AgentState


async def run_graph():
    graph = build_workflow()

    state: AgentState = {
        "session_id": "session-graph-test",
        "mam": 150,
        "user_input": "I can pay 140",
        "history": [],
        "brain_action": None,
        "final_response": None
    }

    result = await graph.ainvoke(state)

    print("\nGRAPH RESULT:")
    print(result)


if __name__ == "__main__":
    asyncio.run(run_graph())
