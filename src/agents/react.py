
import os
import tomllib
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage # The foundational class for all message types in LangGraph
from langchain_core.messages import ToolMessage # Passes data back to LLM after it calls a tool such as the content and the tool_call_id
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import SystemMessage # Message for providing instructions to the LLM
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.tools.gmail_tools import read_mail, send_mail  
from src.tools.search_tool import web_search, fetch_page
from src.tools.function_call import tool_executor

from src.guardrails.llm_grardrail import query_handle, safety_router

with open("prompts/system_prompt.md", "r") as file:
    SYSTEM_PROMPT = file.read()

load_dotenv()

tools = [web_search, fetch_page, read_mail, send_mail]

with open("config.toml", "rb") as file:
    config = tomllib.load(file)  

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

llm = ChatOpenAI(
    base_url="https://freellmapi-seyc.onrender.com/v1",
    model="auto",
    api_key=os.environ.get("FREE_LLM_API")
).bind_tools(tools)


def model_call(state: AgentState) -> AgentState:
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"])
    return {"messages": [response]}


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
app = graph.compile(checkpointer=checkpointer)
thread = {"configurable": {"thread_id": "user-123"}}

current_chat_state = {"messages": []}
while True:
    user_input = input("Enter: ")
    print("\nuser: " + user_input)

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    current_chat_state["messages"].append(("user", user_input))
    current_chat_state = app.invoke(current_chat_state, thread)

    state = app.get_state(thread)
    if state.next:
        interrupt_data = state.tasks[0].interrupts[0].value
        print("--- APPROVAL NEEDED ---")
        print(interrupt_data["preview"])
        answer = input("Proceed? [y/n]: ").strip().lower()
        resume_payload = {"approved": answer == "y"}
        current_chat_state = app.invoke(Command(resume=resume_payload), thread)

    print("AI: " + current_chat_state["messages"][-1].content)


