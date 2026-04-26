# FinSolve RAG Assistant: Project Documentation

This documentation covers the development, architecture, and technical implementation of the FinSolve RAG (Retrieval-Augmented Generation) Chatbot, a secure, department-aware assistant designed to provide internal knowledge while enforcing strict Role-Based Access Control (RBAC).

## Project Description
The FinSolve AI Assistant is a specialized RAG application built to bridge the gap between static internal documentation and actionable employee insights. Unlike standard chatbots, this system is department-aware. It ensures that a user from Engineering cannot access sensitive Finance documents, even if they share the same LLM interface.

## 🛠️ Tech Stack & Architecture
**The Stack**
- Frontend: Streamlit (Python-based interactive UI).

- Backend: FastAPI (High-performance asynchronous API framework).

- LLM Model: Llama 3.2 (via Ollama for local execution) and Groq (for high-speed cloud inference).

- Embeddings: all-MiniLM-L6-v2 via HuggingFace (Local CPU execution).

- Vector Database: Qdrant (Local storage with metadata filtering).

**Layered Architecture**
- Data Ingestion Layer: Processes Markdown files, chunks text, and injects department-specific metadata.

- Vector Storage Layer: Stores high-dimensional embeddings in a Qdrant collection called finsolve_knowledge_base.

- Service Layer (llm_service.py): The "Brain" that handles retrieval, RBAC filtering, and prompt construction.

- API Layer (main.py): Acts as the secure gateway between the UI and the retrieval services.

- Presentation Layer (app.py): The Streamlit interface where users log in and chat.

## 🚀 Installations & Setup
```bash
# 1. Clone the repository
git clone https://github.com/your-repo/RAG-Assistant-Chatbot.git

# 2. Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# 3. Install dependencies
pip install fastapi uvicorn streamlit qdrant-client langchain-huggingface langchain-qdrant groq python-dotenv

# 4. Ingest data
python ingest_data.py
```

## 🤖 Chatbot Features
- **Department-Locked Retrieval:** Filters search results based on the logged-in user's allowed_depts.

- **Source Citation:** Every answer includes the exact filename (e.g., engineering_master_doc.md) used to generate the response.

- **Dual Model Support:** Toggle between local Ollama models and Groq API for different latency needs.

- **Hallucination Protection:** If no authorized documents are found, the system explicitly states it lacks authorization rather than guessing.

## 🧱 Struggles & Hurdles Encountered
1. **Metadata Key Mismatch:** During development, a critical hurdle was ensuring the department key in the ingestion script perfectly matched the search filter in the service layer, which initially resulted in Total chunks found: 0.

2. **Windows File Paths:** Standardizing the database path (db_path) was difficult due to how Qdrant interprets Windows drive letters (C:) as network schemes, requiring the use of explicit path= arguments.

3. **Port Refusal:** Frequent WinError 10061 errors occurred when the Streamlit frontend attempted to connect to the FastAPI backend before the latter had finished initializing the LLM weights.

## 📊 Model Analysis
| Model| Benefits| Drawbacks|
| ---------------| -------------| -----------------|
| Llama 3.2 (Local)| 100% Privacy; no data leaves the local machine.| Slow on CPU; requires significant RAM (8GB+).|
| Groq (API)| Sub-second inference speeds; highly scalable.| Requires an internet connection and API key.|
| all-MiniLM-L6-v2| Extremely fast and lightweight for local CPUs.| Limited semantic depth compared to larger models.|

## 📈 Scalability & Usage
- **Scalability:** The architecture is decoupled. The Qdrant database can be moved to a dedicated server (Qdrant Cloud), and the FastAPI backend can be containerized using Docker to handle thousands of concurrent requests.

- **Versatile Fields:**

    - **Legal:** Siloing case files by legal team/department.

    - **Healthcare:** Ensuring only authorized practitioners see specific patient-type guidelines.

    - **HR:** Managing employee handbooks where "Manager-only" sections remain hidden from general staff.