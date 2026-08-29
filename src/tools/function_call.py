import json
from langgraph.types import interrupt
from langchain_core.messages import ToolMessage
from src.tools.tool_registry import TOOL_REGISTRY

def format_preview(tool_name, args_dict):
    """Human-readable summary of what's about to happen."""

    if tool_name == "send_mail":
        return (f"Send email to {args_dict.get('to')}\n"
                f"Subject: {args_dict.get('subject')}\n"
                f"Body: {args_dict.get('body')}")
    # fallback for any other irreversible tool you add later
    return f"Call {tool_name} with args: {args_dict}"


def tool_executor(state):
    last_message = state["messages"][-1]
    outputs = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args_dict = tool_call["args"]
        entry = TOOL_REGISTRY.get(tool_name)

        if entry is None:
            result = f"Error: unknown tool '{tool_name}'"

        elif entry["reversibility"] == "irreversible":
            decision = interrupt({
                "type": "approval_request",
                "tool_name": tool_name,
                "args": args_dict,
                "preview": format_preview(tool_name, args_dict),
            })

            if decision.get("approved"):
                final_args = decision.get("edited_args", args_dict)
                result = entry["func"].invoke(final_args)
            else:
                result = f"User rejected the action: {tool_name}({args_dict})"

        else:
            result = entry["func"].invoke(args_dict)

        outputs.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )

    return {"messages": outputs}

