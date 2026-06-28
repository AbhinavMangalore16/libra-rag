from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.agents.workflow import agent_app
from langfuse.langchain import CallbackHandler
import os

router = APIRouter(prefix="/agent", tags=["agent"])

class AgentRequest(BaseModel):
    query: str
    session_id: str = "default_session"
    agent_metadata: str = ""

class AgentResponse(BaseModel):
    query: str
    rewritten_query: str
    route: str
    answer: str
    session_id: str
    metrics: dict = {}

@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(request: AgentRequest):
    """
    Submits a query to the Agentic LangGraph workflow, using the session_id for Agentic Memory,
    and automatically logs the entire trace to Langfuse.
    """
    try:
        initial_state = {"user_query": request.query, "agent_metadata": request.agent_metadata}
        
        # Initialize Langfuse Callback
        langfuse_handler = CallbackHandler()
        
        # Configure the checkpointer thread and attach the Langfuse tracer
        config = {
            "configurable": {"thread_id": request.session_id},
            "callbacks": [langfuse_handler]
        }
        
        # Invoke the compiled LangGraph workflow with memory and tracing asynchronously
        final_state = await agent_app.ainvoke(initial_state, config=config)
        
        return AgentResponse(
            query=request.query,
            rewritten_query=final_state.get("rewritten_query", request.query),
            route=final_state.get("route", "unknown"),
            answer=final_state.get("answer", "No answer generated."),
            session_id=request.session_id,
            metrics=final_state.get("eval_metrics", {})
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse
import json

@router.post("/chat/stream")
async def chat_with_agent_stream(request: AgentRequest):
    """
    Submits a query to the Agentic LangGraph workflow and streams node executions and state.
    """
    initial_state = {"user_query": request.query, "agent_metadata": request.agent_metadata}
    langfuse_handler = CallbackHandler()
    config = {
        "configurable": {"thread_id": request.session_id},
        "callbacks": [langfuse_handler]
    }
    
    async def event_generator():
        try:
            async for event in agent_app.astream(initial_state, config=config):
                # event is a dict mapping node_name -> state_updates
                for node_name, state_updates in event.items():
                    # We need to serialize LangChain message objects safely
                    def custom_serializer(obj):
                        if hasattr(obj, "dict"):
                            return obj.dict()
                        if hasattr(obj, "to_json"):
                            return obj.to_json()
                        return str(obj)

                    data = {
                        "node": node_name,
                        "state": state_updates
                    }
                    yield f"data: {json.dumps(data, default=custom_serializer)}\n\n"
            
            # Send a final 'done' event to close cleanly
            yield "data: {\"done\": true}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
