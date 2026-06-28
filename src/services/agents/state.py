from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    Represents the state of our agentic workflow at any given node.
    """
    # Core Memory: LangGraph handles appending new messages to this list
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Summary Buffer Memory: Stores the compressed semantic context of old messages
    summary: str
    
    # Processing State
    user_query: str
    agent_metadata: str
    rewritten_query: str
    route: str
    
    # RAG Retrieval
    documents: List[Dict[str, Any]]
    context_str: str
    
    # LLM Generation
    answer: str
    
    # Evaluation
    eval_metrics: dict
