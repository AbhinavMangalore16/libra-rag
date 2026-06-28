import asyncio
from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_tavily import TavilySearch
from langchain.tools import tool
from langchain_core.messages import AIMessage

from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

# --- Rich Imports ---
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

load_dotenv()

# Initialize Rich Console
console = Console()

@tool
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

async def build_graph():

    client = MultiServerMCPClient(
        {
            "weather": {
                "url": "http://localhost:8000/mcp",
                "transport": "streamable_http"
            }
        }
    )

    mcp_tools = await client.get_tools()
    tavily = TavilySearch(max_results=5)

    tools = [
        *mcp_tools,
        tavily,
        add,
        multiply
    ]

    llm = ChatOllama(
        model="qwen2.5:7b",
        temperature=0.7
    )

    llm = llm.bind_tools(tools)

    tool_node = ToolNode(tools)

    def agent_node(state: AgentState):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    def approval_node(state: AgentState):
        last_message = state["messages"][-1]

        if not isinstance(last_message, AIMessage):
            return {}

        tool_calls = last_message.tool_calls

        approval = interrupt(
            {
                "question": "Approve tool execution?",
                "tool_calls": tool_calls
            }
        )

        if approval is False:
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Tool execution rejected by user."
                    }
                ]
            }

        return {}

    def route_after_agent(state: AgentState):
        last_message = state["messages"][-1]

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "approval"

        return END
    
    builder = StateGraph(AgentState)

    builder.add_node("agent", agent_node)
    builder.add_node("approval", approval_node)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "approval": "approval",
            END: END
        }
    )
    builder.add_edge("approval", "tools")
    builder.add_edge("tools", "agent")

    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    return graph


async def main():
    
    # Use a spinner while initializing the graph and loading MCP tools
    with console.status("[bold green]Initializing Agent, MCP Tools, and Memory...[/bold green]", spinner="dots"):
        graph = await build_graph()

    config = {
        "configurable": {
            "thread_id": "abhinav"
        }
    }

    # Welcome Panel
    welcome_text = Text("Agent is ready! Memory, HITL, and MCP are active.\nType 'exit' to quit.", justify="center")
    console.print(Panel(welcome_text, title="[bold cyan]🚀 System Online[/bold cyan]", border_style="cyan"))

    while True:

        # Rich Prompt for User Input
        query = Prompt.ask("\n[bold green]👤 You[/bold green]")

        if query.lower() in ["exit", "quit"]:
            console.print("[bold red]Shutting down agent... Goodbye![/bold red]")
            break

        # Spinner while LLM processes
        with console.status("[bold blue]🤖 Agent is thinking...[/bold blue]", spinner="aesthetic"):
            result = await graph.ainvoke(
                {
                    "messages": [("user", query)]
                },
                config=config
            )

        # Handle HITL Interruption
        if "__interrupt__" in result:
            interrupt_data = result["__interrupt__"][0].value

            # Create a nice table to display requested tool calls
            table = Table(show_header=True, header_style="bold magenta", expand=True)
            table.add_column("🛠️ Tool Name", style="cyan", width=20)
            table.add_column("Arguments", style="yellow")

            for tool_call in interrupt_data["tool_calls"]:
                table.add_row(
                    tool_call.get("name", "Unknown"), 
                    str(tool_call.get("args", {}))
                )

            # Wrap the table in a Warning Panel
            console.print(Panel(
                table, 
                title="[bold red]⚠️ Action Required: Tool Execution Request[/bold red]", 
                border_style="red"
            ))

            # Rich Boolean Confirm Prompt
            approval = Confirm.ask("[bold red]Approve execution of these tools?[/bold red]")

            with console.status("[bold magenta]Executing tool and resuming...[/bold magenta]", spinner="bouncingBar"):
                if approval:
                    result = await graph.ainvoke(Command(resume=True), config=config)
                else:
                    result = await graph.ainvoke(Command(resume=False), config=config)

        # Assistant Output Panel
        last_message = result["messages"][-1]
        
        # We only want to render standard content in the markdown panel (ignore empty messages that just return tool calls)
        if last_message.content:
            console.print(Panel(
                Markdown(last_message.content), 
                title="[bold blue]🤖 Assistant[/bold blue]", 
                border_style="blue",
                padding=(1, 2)
            ))


if __name__ == "__main__":
    asyncio.run(main())