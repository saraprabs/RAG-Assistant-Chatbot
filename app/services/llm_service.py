import os
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from pathlib import Path
# point it to the root .env
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configuration
COLLECTION_NAME = "finsolve_knowledge_base"
# Llama 3.3 70B is currently the best balance of speed and logic on Groq
GROQ_MODEL = "llama-3.3-70b-versatile" 

class LLMService:
    def __init__(self):
        raw_key = os.environ.get("GROQ_API_KEY", "")
        clean_key = "".join(raw_key.split()).replace("'", "").replace('"', "")
         # Initialize Groq LLM
        self.llm = ChatOllama(
    model="llama3.2",
    temperature=0
)
        # Configuration"
        self.collection_name = COLLECTION_NAME

        # Local Embeddings - ensure this matches ingest_data.py
        #self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Connection to your local vector store
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            # Using preferential settings for local dev
            self.client = QdrantClient(path="./qdrant_db") 
            self.vectorstore = Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=self.embeddings
            )
            print("✅ LLM and Qdrant initialized successfully.")
        except Exception as e:
            print(f"❌ DATABASE ERROR: {e}")
            # If Qdrant fails, we still need a vectorstore attribute to avoid crashes
            self.vectorstore = None
        
       

    def _format_docs(self, docs: List) -> str:
        """Standardize context strings for the LLM."""
        if not docs:
            return "NO RELEVANT CONTEXT FOUND."
            
        formatted = []
        for doc in docs:
            source = doc.metadata.get("source_file", "Unknown Source")
            content = doc.page_content.replace("\n", " ")
            formatted.append(f"SOURCE: {source}\nCONTENT: {content}\n---")
        return "\n".join(formatted)

    def generate_rbac_response(self, query: str, allowed_depts: List[str], role_name: str) -> Dict[str, Any]:
        """Executes a RAG query with metadata filtering for RBAC."""
        
        # 1. Setup RBAC filter
        filter_dict = {
            "must": [
                {
                    "key": "metadata.department", 
                    "match": {"any": allowed_depts}
                }
            ]
        }

        # 2. Setup Retriever
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"filter": filter_dict, "k": 4}
        )

        # 3. Define System Prompt
        template = """
        You are the FinSolve Technical Architect, assisting the {role} department.
        
        STRICT OPERATING GUIDELINES:
        1. GROUNDING: Provide answers based ONLY on the provided CONTEXT. 
        2. CITATIONS: You must mention the specific 'SOURCE' file for every factual claim.
        3. DATA SILOS: If the context is empty or irrelevant, state: "I do not have authorization to access that specific data for the {role} department."
        4. TONE: Concise, technical, and objective. Use Markdown tables for data.

        CONTEXT:
        {context}

        USER QUESTION: {question}
        
        TECHNICAL RESPONSE:
        """
        prompt = ChatPromptTemplate.from_template(template)

        # 4. Build and Execute Chain
        rag_chain = (
            {
                "context": retriever | self._format_docs, 
                "question": RunnablePassthrough(), 
                "role": lambda _: role_name
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

        # 5. Extract results and source metadata
        # Using .invoke() instead of deprecated get_relevant_documents
        retrieved_docs = retriever.invoke(query)
        sources = list(set([doc.metadata.get("source_file") for doc in retrieved_docs]))
        
        answer = rag_chain.invoke(query)

        return {
            "answer": answer,
            "sources": sources
        }

# Singleton instance
llm_service = LLMService()