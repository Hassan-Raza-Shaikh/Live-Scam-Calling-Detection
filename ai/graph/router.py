from ai.graph.state import GraphState

def route_next_supervisor(state: GraphState) -> str:
    """Routes execution based on fast path alert or supervisor state."""
    if state.get("fast_path_alert"):
        return "decision_supervisor"
    return state.get("next_node", "workers_execution")
