from langgraph.graph import StateGraph
from orchestrator.graph.state import AgentState
from orchestrator.graph.nodes import nlu_node, brain_node, mouth_node


def build_workflow():

    graph = StateGraph(AgentState)

    graph.add_node("nlu", nlu_node)
    graph.add_node("brain", brain_node)
    graph.add_node("mouth", mouth_node)

    graph.set_entry_point("nlu")
    graph.add_edge("nlu", "brain")
    graph.add_edge("brain", "mouth")

    return graph.compile()
