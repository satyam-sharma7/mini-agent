from src.tools import gmail_tools
from src.tools import search_tool

TOOL_REGISTRY = {
    "read_mail": {
        "func": gmail_tools.read_mail,
        "reversibility": "read",
    },
    "send_mail": {
        "func": gmail_tools.send_mail,
        "reversibility": "irreversible",
    },
    "web_search": {
        "func": search_tool.web_search,
        "reversibility": "read",
    },
    "fetch_page": {
        "func": search_tool.fetch_page,
        "reversibility": "read",
    },

    # "create_event": {"func": calendar_tools.create_event, "reversibility": "reversible"},
}
