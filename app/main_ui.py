import streamlit as st
import requests

# Page Config
st.set_page_config(page_title="FinSolve RAG Assistant", layout="wide")

st.title("🤖 FinSolve Technical Assistant")
st.markdown("---")

# 1. Sidebar for Authentication (Simulation)
with st.sidebar:
    st.header("🔐 User Access")
    username = st.selectbox("Select User Role", ["engineer_user", "hr_user", "finance_user", "admin_user"])
    st.info(f"Current Role: **{username.split('_')[0].upper()}**")

# 2. Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message:
            st.caption(f"Sources: {', '.join(message['sources'])}")

# 3. Input Handling
if prompt := st.chat_input("Ask a technical question..."):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call FastAPI Backend
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            try:
                payload = {"query": prompt, "username": username}
                response = requests.post("http://127.0.0.1:8000/chat", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])
                    
                    st.markdown(answer)
                    if sources:
                        st.caption(f"Sources: {', '.join(sources)}")
                    
                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer, 
                        "sources": sources
                    })
                else:
                    st.error(f"Backend Error: {response.text}")
            except Exception as e:
                st.error(f"Connection failed: Ensure FastAPI is running on port 8000. ({e})")