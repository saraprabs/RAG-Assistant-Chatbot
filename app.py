import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

# --- Configuration ---
API_URL = "http://localhost:8000"

st.set_page_config(page_title="FinSolve AI Assistant", page_icon="🏦", layout="wide")

# --- Session State Initialization ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "password" not in st.session_state:
    st.session_state.password = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar: Authentication ---
with st.sidebar:
    st.title("🔐 FinSolve Access")
    
    if not st.session_state.authenticated:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            try:
                # Call the /login endpoint to verify credentials and get the role
                response = requests.get(
                    f"{API_URL}/login", 
                    auth=HTTPBasicAuth(username, password)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.password = password
                    st.session_state.role = data["role"]
                    st.success(f"Logged in as {username} ({data['role']})")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")
    else:
        st.write(f"**User:** {st.session_state.username}")
        st.write(f"**Department:** {st.session_state.role.capitalize()}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.messages = []
            st.rerun()

# --- Main Chat Interface ---
st.title("🏦 FinSolve AI Engineering Assistant")

if not st.session_state.authenticated:
    st.info("Please log in from the sidebar to access department-specific data.")
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                st.caption(f"Sources: {', '.join(message['sources'])}")

    # Chat Input
    if prompt := st.chat_input("Ask a question about your department..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response from FastAPI
        with st.chat_message("assistant"):
            with st.spinner("Consulting knowledge base..."):
                try:
                    # Pass the message to the protected /chat endpoint
                    res = requests.post(
                        f"{API_URL}/chat",
                        params={"message": prompt},
                        auth=HTTPBasicAuth(st.session_state.username, st.session_state.password)
                    )
                    
                    if res.status_code == 200:
                        data = res.json()
                        answer = data["answer"]
                        sources = data["sources"]
                        
                        st.markdown(answer)
                        if sources:
                            st.caption(f"Sources used: {', '.join(sources)}")
                        
                        # Save to history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": answer, 
                            "sources": sources
                        })
                    else:
                        st.error(f"Error: {res.status_code}")
                except Exception as e:
                    st.error(f"Request failed: {e}")