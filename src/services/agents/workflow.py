from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.services.agents.state import AgentState
from src.services.agents.nodes import (
    apply_guardrails,
    rewrite_query,
    route_query,
    fetch_context,
    web_search_context,
    generate_rag_answer,
    generate_simple_answer,
    summarize_memory,
    evaluate_ragas
)

def build_agent_graph():
    """
    Builds and compiles the production-grade LangGraph workflow with Summary Buffer Memory.
    """
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("guardrails", apply_guardrails)
    workflow.add_node("rewrite", rewrite_query)
    workflow.add_node("route", route_query)
    workflow.add_node("fetch_context", fetch_context)
    workflow.add_node("web_search_context", web_search_context)
    workflow.add_node("rag_answer", generate_rag_answer)
    workflow.add_node("simple_answer", generate_simple_answer)
    workflow.add_node("summarize_memory", summarize_memory)
    workflow.add_node("evaluate_ragas", evaluate_ragas)
    
    # Add Edges
    workflow.add_edge(START, "guardrails")
    
    # Guardrails Conditional Routing
    workflow.add_conditional_edges(
        "guardrails",
        lambda state: state.get("route", "pass"),
        {
            "blocked": "summarize_memory",
            "pass": "rewrite"
        }
    )
    
    workflow.add_edge("rewrite", "route")
    
    # Conditional Routing
    workflow.add_conditional_edges(
        "route",
        lambda state: state["route"],
        {
            "rag": "fetch_context",
            "web_search": "web_search_context",
            "simple": "simple_answer"
        }
    )
    
    workflow.add_edge("fetch_context", "rag_answer")
    workflow.add_edge("web_search_context", "rag_answer")
    
    # After answering, always run the memory compression check
    workflow.add_edge("rag_answer", "summarize_memory")
    workflow.add_edge("simple_answer", "summarize_memory")
    
    workflow.add_edge("summarize_memory", "evaluate_ragas")
    workflow.add_edge("evaluate_ragas", END)
    
    # Add SQLite-backed MemorySaver (for session persistence)
    memory_saver = MemorySaver()
    
    return workflow.compile(checkpointer=memory_saver)

# Compiled graph for easy import
agent_app = build_agent_graph()
