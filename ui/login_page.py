import streamlit as st
import time
import requests

BACKEND_URL = "http://127.0.0.1:8000"


def init_session_state():
    defaults = {
        "token": None,
        "user_email": None,
        "active_session_id": None,
        "messages": [],
        "view": "login",  # "login" or "signup"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login_page():
    st.title("Login")
    user_email = st.text_input("Email", key="login_email")
    user_password = st.text_input("Password", type="password", key="login_password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            response = requests.post(
                f"{BACKEND_URL}/login/",
                json={"email": user_email, "password": user_password},
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state.token = data["access_token"]
                st.session_state.user_email = user_email
                st.rerun()
            else:
                st.error("Invalid email ya password")

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
            response = requests.post(
                f"{BACKEND_URL}/sing-up/",
                json={"email": user_email, "password": user_password},
            )
            if response.status_code == 200:
                data = response.json()
                st.success(data["status"])
                time.sleep(2)
                st.session_state.view = "login"
                st.rerun()
            elif response.status_code == 400:
                st.error(response.json()["detail"])
            else:
                st.error("Invalid email ya password")

    with col2:
        if st.button("Back to Login"):
            st.session_state.view = "login"
            st.rerun()


def main():
    init_session_state()

    if st.session_state.token is None:
        if st.session_state.view == "signup":
            signup_page()
        else:
            login_page()
    else:
        st.title("Chat")
        st.write(f"Logged in as {st.session_state.user_email}")
        # your chat UI goes here


main()
