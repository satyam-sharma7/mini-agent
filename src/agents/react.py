import os
import tomllib
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from typing import Annotated, Sequence, TypedDict, List, Dict, AsyncGenerator, Any
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import InMemorySaver

from src.tools.gmail_tools import read_mail, send_mail
from src.tools.search_tool import web_search, fetch_page
from src.tools.function_call import tool_executor
from src.guardrails.llm_grardrail import query_handle, safety_router

load_dotenv()

with open("prompts/system_prompt.md", "r") as file:
    SYSTEM_PROMPT = file.read()

with open("config.toml", "rb") as file:
    config = tomllib.load(file)  

tools = [web_search, fetch_page, read_mail, send_mail]

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

llm = ChatOpenAI(
    base_url="https://freellmapi-seyc.onrender.com/v1",
    model="auto",
    api_key=os.environ.get("FREE_LLM_API")
).bind_tools(tools)


async def model_call(state: AgentState) -> AgentState:
    response = await llm.ainvoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"])
    return {"messages": [response]}


# Build Graph
graph = StateGraph(AgentState)
graph.add_node("guardrail_scanner", query_handle)
graph.add_node("our_agent", model_call)
graph.add_node("tools", tool_executor)

graph.add_edge(START, "guardrail_scanner")

graph.add_conditional_edges(
    "guardrail_scanner",
    safety_router,
    {
        "safe": "our_agent",
        "unsafe": END
    }
)

graph.add_conditional_edges(
    "our_agent",
    lambda state: "tools" if state["messages"][-1].tool_calls else END,
)
graph.add_edge("tools", "our_agent")

checkpointer = InMemorySaver()
agent_app = graph.compile(checkpointer=checkpointer)


def _format_history(short_term_memory: List[Dict[str, str]]) -> List[BaseMessage]:
    """Converts Redis short-term dictionary history into standard LangChain message objects."""
    formatted_messages = []
    for msg in short_term_memory:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            formatted_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            formatted_messages.append(AIMessage(content=content))
    return formatted_messages


async def call_agent(
    message: str, 
    short_term_memory: List[Dict[str, str]] = None,
    session_id: str = "default_session"
) -> AsyncGenerator[str, None]:
    if short_term_memory is None:
        short_term_memory = []

    history_messages = _format_history(short_term_memory)
    history_messages.append(HumanMessage(content=message))
    
    input_state = {"messages": history_messages}
    config = {"configurable": {"thread_id": session_id}}

    async for event in agent_app.astream_events(input_state, config=config, version="v2"):
        kind = event["event"]
        
        # 1. Safely extract node name from event root OR metadata
        node_name = event.get("langgraph_node") or event.get("metadata", {}).get("langgraph_node", "")

        # 2. STRICT CHECK: Must be an LLM stream event AND strictly from "our_agent"
        if kind == "on_chat_model_stream" and node_name == "our_agent":
            chunk = event["data"]["chunk"]

            # 3. Ignore tool call argument chunks
            if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                continue

            token = getattr(chunk, "content", "")
            if token and isinstance(token, str):
                yield token
