from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, RemoveMessage
from src.services.llm.client import get_llm
from src.services.opensearch.retriever import hybrid_search
from src.services.agents.state import AgentState

def rewrite_query(state: AgentState) -> AgentState:
    """
    Optimizes the user's query for better retrieval, taking chat history into account.
    """
    llm = get_llm()
    query = state["user_query"]
    
    # Simple history string for rewriting context
    history_str = "\n".join([f"{m.type}: {m.content}" for m in state.get("messages", [])[-4:]])
    
    prompt = (
        f"Chat History:\n{history_str}\n\n"
        f"Rewrite the following user query to resolve any pronouns (like 'it' or 'they') based on the Chat History, "
        f"so it can be used independently for a vector search engine. If the query is already self-contained or is just a "
        f"conversational/personal question, return it exactly as is without adding extra topic details. "
        f"Query: '{query}'. Return ONLY the rewritten query."
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"rewritten_query": response.content.strip()}

def route_query(state: AgentState) -> AgentState:
    """
    Routes the query to either 'rag', 'web_search', or 'simple'.
    """
    llm = get_llm()
    query = state.get("rewritten_query", state["user_query"])
    
    prompt = f"Classify this query: '{query}'. If it requires factual information, paper summaries, technical details, or external knowledge from internal documents, respond with 'rag'. If it requires real-time web search or current events, respond with 'web_search'. If it is a simple greeting or casual chat, respond with 'simple'. Return ONLY 'rag', 'web_search', or 'simple'."
    
    response = llm.invoke([HumanMessage(content=prompt)])
    route = response.content.strip().lower()
    
    if "rag" in route: 
        route = "rag"
    elif "web" in route or "search" in route:
        route = "web_search"
    else: 
        route = "simple"
    
    return {"route": route}

async def apply_guardrails(state: AgentState) -> dict:
    """
    Applies NeMo Guardrails on the user input to enforce safety and policy.
    """
    from src.services.guardrails.rails import get_rails
    rails = get_rails()
    
    query = state["user_query"]
    # Run the Colang dialog rails asynchronously
    res = await rails.generate_async(messages=[{"role": "user", "content": query}])
    content = res.get("content")
    
    canned_responses = [
        "I am mangrove-v1",
        "I cannot engage with offensive",
        "For your privacy and security"
    ]
    
    # If a rule was triggered, we short circuit the graph by returning the answer and a blocked route
    is_blocked = any(canned_phrase in content for canned_phrase in canned_responses)
    
    if is_blocked:
        from langchain_core.messages import HumanMessage, AIMessage
        return {
            "route": "blocked", 
            "answer": content,
            "messages": [HumanMessage(content=query), AIMessage(content=content)]
        }
        
    return {"route": "pass"}

def web_search_context(state: AgentState) -> AgentState:
    """
    Uses Tavily Search MCP tool to fetch context from the web.
    """
    from langchain_community.tools.tavily_search import TavilySearchResults
    tool = TavilySearchResults(max_results=3)
    query = state.get("rewritten_query", state["user_query"])
    
    try:
        results = tool.invoke({"query": query})
        context_str = "\n\n".join([f"Source: [{res['url']}]({res['url']})\n{res['content']}" for res in results])
    except Exception as e:
        print(f"Web search failed: {e}")
        context_str = "No web search context available."
        
    return {"context_str": context_str}

def fetch_context(state: AgentState) -> AgentState:
    """
    Executes hybrid search using the rewritten query.
    """
    query = state.get("rewritten_query", state["user_query"])
    
    try:
        results = hybrid_search(query, k=5, chunk_type="parent")
    except Exception as e:
        print(f"Search failed: {e}")
        results = []
    
    context_str = "\n\n".join([
        f"Source: [{doc.get('source_file', 'unknown')}](/api/proxy-document?file={doc.get('source_file', 'unknown')}#page={doc.get('page_number', 0)}) (Page {doc.get('page_number', 0)})\n{doc.get('text', '')}" 
        for doc in results
    ])
    
    return {"documents": results, "context_str": context_str}

def generate_rag_answer(state: AgentState) -> AgentState:
    """
    Generates an answer based on RAG context and Conversation Memory.
    """
    llm = get_llm()
    summary = state.get("summary", "")
    agent_metadata = state.get("agent_metadata", "")
    
    sys_content = (
        "You are an expert AI research assistant. You are having an ongoing conversation with the user. "
        "Use the provided 'Context' documents to answer technical or factual questions. "
        "Use the 'Conversation Summary' and chat history to answer personal or conversational questions (like the user's name). "
        "If a factual question cannot be answered using the provided Context, clearly state that you don't know based on the documents. "
        "Always cite your sources when using the Context."
    )
    if agent_metadata:
        sys_content = f"Here is your specific agent persona and instruction context. You MUST follow these instructions closely:\n{agent_metadata}\n\n" + sys_content
        
    if summary:
        sys_content += f"\n\nPrevious Conversation Summary:\n{summary}"
        
    messages = [SystemMessage(content=sys_content)]
    # Add recent messages for immediate context
    messages.extend(state.get("messages", []))
    
    # Add the current RAG context and question
    human_msg = HumanMessage(content=f"Context:\n{state.get('context_str', '')}\n\nQuestion:\n{state.get('user_query')}")
    messages.append(human_msg)
    
    response = llm.invoke(messages)
    
    # We append the user's raw query and the AI's response to the memory
    return {
        "answer": response.content,
        "messages": [HumanMessage(content=state["user_query"]), AIMessage(content=response.content)]
    }

def generate_simple_answer(state: AgentState) -> AgentState:
    """
    Generates a conversational answer using Memory.
    """
    llm = get_llm()
    summary = state.get("summary", "")
    agent_metadata = state.get("agent_metadata", "")
    
    sys_content = "You are a helpful conversational AI assistant."
    
    if agent_metadata:
        sys_content = f"Here is your specific agent persona and instruction context. You MUST follow these instructions closely:\n{agent_metadata}\n\n" + sys_content
        
    if summary:
        sys_content += f"\n\nPrevious Conversation Summary:\n{summary}"
        
    messages = [SystemMessage(content=sys_content)]
    messages.extend(state.get("messages", []))
    messages.append(HumanMessage(content=state["user_query"]))
    
    response = llm.invoke(messages)
    
    return {
        "answer": response.content,
        "messages": [HumanMessage(content=state["user_query"]), AIMessage(content=response.content)]
    }

def summarize_memory(state: AgentState) -> AgentState:
    """
    Summary Buffer Memory logic: Compresses old messages if history gets too long.
    """
    messages = state.get("messages", [])
    summary = state.get("summary", "")
    
    # If we have more than 6 messages, compress the oldest ones
    if len(messages) > 6:
        llm = get_llm()
        
        # We will summarize all but the last 2 messages (which are the most recent interaction)
        messages_to_summarize = messages[:-2]
        
        summary_prompt = "Summarize the following conversation history. "
        if summary:
            summary_prompt += f"Include this previous summary in your new summary:\n{summary}\n\n"
            
        summary_prompt += "Conversation:\n" + "\n".join([f"{m.type}: {m.content}" for m in messages_to_summarize])
        
        response = llm.invoke([HumanMessage(content=summary_prompt)])
        new_summary = response.content
        
        # We use RemoveMessage to delete them from LangGraph's state
        delete_messages = [RemoveMessage(id=m.id) for m in messages_to_summarize]
        
        return {"summary": new_summary, "messages": delete_messages}
        
    return {}

async def evaluate_ragas(state: AgentState) -> AgentState:
    """
    Evaluates the final RAG answer using Ragas metrics and logs the query to Postgres.
    """
    query = state.get("rewritten_query", state["user_query"])
    answer = state.get("answer", "")
    route = state.get("route", "unknown")
    context_str = state.get("context_str", "")
    
    eval_metrics = {}
    
    # Only run Ragas if we actually did RAG and have an answer/context
    if route not in ["simple", "blocked"] and answer and context_str:
        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
            from src.services.llm.client import get_llm
            from langchain_community.embeddings import HuggingFaceEmbeddings
            import os
            from src.core.config import get_settings
            
            os.environ["OPENAI_API_KEY"] = get_settings().LLM_API_KEY
            llm = get_llm()
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
            data = {
                "user_input": [query],
                "response": [answer],
                "retrieved_contexts": [[context_str]],
                "reference": [""]
            }
            dataset = Dataset.from_dict(data)
            
            import asyncio
            
            def _run_ragas_in_thread():
                # Ragas spawns internal threads which will use the global event loop policy.
                # Uvicorn sets this to uvloop, which nest_asyncio can't patch.
                # Temporarily revert the global policy so child threads get standard loops.
                old_policy = asyncio.get_event_loop_policy()
                asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    import nest_asyncio
                    nest_asyncio.apply(loop)
                    
                    return evaluate(
                        dataset=dataset,
                        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                        llm=llm,
                        embeddings=embeddings,
                    )
                finally:
                    loop.close()
                    asyncio.set_event_loop_policy(old_policy)
            
            result = await asyncio.to_thread(_run_ragas_in_thread)
            eval_metrics = result.to_pandas().to_dict(orient="records")[0]
        except Exception as e:
            import logging
            logging.error(f"Ragas evaluation failed: {e}")
            eval_metrics = {"error": str(e)}

    # Log to Neon Postgres if available
    from src.core.config import get_settings
    settings = get_settings()
    if settings.POSTGRES_DATABASE_URL:
        from src.db.session import AsyncSessionLocal
        from src.db.models import QueryLog
        async with AsyncSessionLocal() as session:
            q_log = QueryLog(
                session_id=state.get("session_id", "default"),
                query=query,
                answer=answer,
                route=route,
                eval_metrics=eval_metrics
            )
            session.add(q_log)
            await session.commit()
            
    return {"eval_metrics": eval_metrics}
