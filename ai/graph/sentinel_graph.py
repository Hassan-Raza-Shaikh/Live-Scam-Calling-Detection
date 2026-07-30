from langgraph.graph import StateGraph, END
from ai.graph.state import GraphState
from ai.graph.nodes import (
    workflow_supervisor_node,
    memory_supervisor_node,
    workers_execution_node,
    consensus_supervisor_node,
    decision_supervisor_node
)

def build_sentinel_graph():
    """Builds and compiles the Sentinel AI LangGraph Supervisor-Worker state machine."""
    workflow = StateGraph(GraphState)
    
    # Add Nodes
    workflow.add_node("workflow_supervisor", workflow_supervisor_node)
    workflow.add_node("memory_supervisor", memory_supervisor_node)
    workflow.add_node("workers_execution", workers_execution_node)
    workflow.add_node("consensus_supervisor", consensus_supervisor_node)
    workflow.add_node("decision_supervisor", decision_supervisor_node)
    
    # Define Edges
    workflow.set_entry_point("workflow_supervisor")
    workflow.add_edge("workflow_supervisor", "memory_supervisor")
    workflow.add_edge("memory_supervisor", "workers_execution")
    workflow.add_edge("workers_execution", "consensus_supervisor")
    workflow.add_edge("consensus_supervisor", "decision_supervisor")
    workflow.add_edge("decision_supervisor", END)
    
    return workflow.compile()

# Global compiled sentinel graph instance
sentinel_app = build_sentinel_graph()
