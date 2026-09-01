import streamlit as st
from typing import Optional
import time
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"

def init_session_state():
    defaults = {
        "token": None,
        "user_email": None,
        "active_session_id": None,
        "messages": [],
        "sessions": [],
        "view": "login"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def api_request(
    method: str, 
    endpoint: str, 
    data: Optional[dict] = None, 
    headers: Optional[dict] = None,
    stream: bool = False  # Added stream flag
):
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, stream=stream)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, stream=stream)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()

        # Handle streaming responses
        # In api_request():
        if stream:
            def generate():
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        try:
                            # Strip quotes or decode JSON string
                            cleaned_chunk = json.loads(chunk)
                            yield cleaned_chunk
                        except json.JSONDecodeError:
                            # Fallback if chunk is plain text
                            yield chunk
            return generate()

        # Standard non-streaming JSON response
        return response.json()

    except requests.exceptions.HTTPError as e:
        try:
            error_body = e.response.json()
            detail = error_body.get("detail", "Something went wrong.")
        except (ValueError, AttributeError):
            detail = str(e)
        st.error(detail)
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None

    
def login_page():
    st.title("Login")
    user_email = st.text_input("Email", key="login_email")
    user_password = st.text_input("Password", type="password", key="login_password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            response = api_request("POST", "/login", {"email": user_email, "password": user_password})
            if response and "access_token" in response:
                st.session_state.token = response["access_token"]
                st.session_state.messages = []
                st.session_state.active_session_id = None
                st.session_state.user_email = user_email
                st.rerun()
            # else:
            #     st.error("Invalid email ya password")

    with col2:
        if st.button("Go to Sign Up"):
            st.session_state.view = "signup"
            st.rerun()


def signup_page():
    st.title("Sign Up")
    user_email = st.text_input("Email", key="signup_email")
    user_password = st.text_input("Password", type="password", key="signup_password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Sign Up"):
            response = api_request("POST", "/sing-up", {"email": user_email, "password": user_password})
            if response and "access_token" in response:
                st.session_state.token = response["access_token"]
                st.session_state.messages = []
                st.session_state.active_session_id = None
                st.session_state.user_email = user_email
                st.rerun()
            # else:
            #     st.error("Invalid email ya password")

    with col2:
        if st.button("Back to Login"):
            st.session_state.view = "login"
            st.rerun()


def load_sessions():
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    
    # New Chat button
    if st.button("➕ New Chat", key="new_chat"):
        response = api_request("POST", "/sessions", headers=headers)
        if response and "session_id" in response:
            st.session_state.active_session_id = response["session_id"]
            st.session_state.messages = []
            st.rerun()
    
    st.divider()
    
    # Load sessions
    sessions = api_request("GET", "/sessions", headers=headers)
    
    if sessions:
        st.session_state.sessions = sessions
        for session in sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    session["title"],
                    key=f"session_{session['id']}",
                    use_container_width=True
                ):
                    st.session_state.active_session_id = session["id"]
                    # Load messages for this session
                    messages = api_request(
                        "GET",
                        f"/sessions/{session['id']}/messages",
                        headers=headers
                    )
                    if messages:
                        st.session_state.messages = messages
                    else:
                        st.session_state.messages = []
                    st.rerun()
            
            with col2:
                if st.button(
                    "🗑️",
                    key=f"delete_{session['id']}",
                    help="Delete this chat"
                ):
                    api_request(
                        "DELETE",
                        f"/sessions/{session['id']}",
                        headers=headers
                    )
                    if st.session_state.active_session_id == session["id"]:
                        st.session_state.active_session_id = None
                        st.session_state.messages = []
                    st.rerun()

def chat_interface():
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    st.html(
        """
        <style>
            /* Base reset */
            .stChatMessage {
                background-color: transparent !important;
            }
            
            /* USER CHAT (RIGHT ALIGNED, BUBBLE) */
            .stChatMessage:has(.chat-user) {
                flex-direction: row-reverse !important;
            }
            .stChatMessage:has(.chat-user) > div {
                flex-direction: row-reverse !important;
            }
            .stChatMessage:has(.chat-user) .stMarkdown {
                background-color: #ffffff !important;
                color: #000000 !important;
                padding: 0.75rem 1.25rem !important;
                border-radius: 18px 18px 0px 18px !important;
                margin-right: 10px !important;
                margin-left: auto !important;
                width: fit-content !important;
                max-width: 70% !important;
            }

            /* ASSISTANT CHAT (LEFT ALIGNED, FITS TEXT LENGTH) */
            .stChatMessage:has(.chat-assistant) {
                flex-direction: row !important;
            }
            .stChatMessage:has(.chat-assistant) .stMarkdown {
                background-color: #2b2c36 !important;
                color: #ffffff !important;
                padding: 0.75rem 1.25rem !important;
                border-radius: 18px 18px 18px 0px !important;
                margin-left: 10px !important;
                margin-right: auto !important;
                width: fit-content !important; /* Shrinks the dark background box to fit text */
                max-width: 80% !important;     /* Keeps text from stretching across whole screen on long lines */
            }
        </style>
        """
    )

    # 1. Render existing chat history
    for message in st.session_state.messages:
        role = message.get("role", message.get("author"))
        content = message.get("content", message.get("message"))

        if role not in ("user", "assistant"):
            role = "assistant" if role == "ai" else "user"

        with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
            st.html(f"<span class='chat-{role}'></span>")
            st.write(content)

    # 2. Handle user input
    user_input = st.chat_input("Message...")
    if user_input:
        if st.session_state.active_session_id is None:
            response = api_request("POST", "/sessions", headers=headers)
            if response and "session_id" in response:
                st.session_state.active_session_id = response["session_id"]
            else:
                return

        # Display user message immediately in UI and store it
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑"):
            st.html("<span class='chat-user'></span>")
            st.write(user_input)

        # Stream assistant response directly in UI
        with st.chat_message("assistant", avatar="🤖"):
            st.html("<span class='chat-assistant'></span>")
            
            stream_generator = api_request(
                "POST",
                f"/sessions/{st.session_state.active_session_id}/messages",
                data={"session_id": str(st.session_state.active_session_id), "message": user_input},
                headers=headers,
                stream=True
            )

            if stream_generator:
                full_response = st.write_stream(stream_generator)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

        st.rerun()

def main():
    init_session_state()
    
    # Set page config
    st.set_page_config(
        page_title="Claude Clone",
        page_icon="💬",
        layout="wide"
    )
    st.markdown("""
    <style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
        text-align: left;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.token is None:
        if st.session_state.view == "signup":
            signup_page()
        else:
            login_page()
    else:
        with st.sidebar:
            st.header(f"👤 {st.session_state.user_email}")
            
            if st.button("🔐 Logout", key="logout"):
                st.session_state.token = None
                st.session_state.user_email = None
                st.session_state.active_session_id = None
                st.session_state.messages = []
                st.rerun()
            
            st.divider()
            st.header("💬 Your Chats")
            load_sessions()
        
        # # Main chat area
        chat_interface()


main()
