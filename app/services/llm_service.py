import os
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
#from langchain_community.vectorstores import Qdrant
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv
from pathlib import Path
# point it to the root .env
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
db_path = os.path.join(project_root, "qdrant_db")
# Configuration
COLLECTION_NAME = "finsolve_knowledge_base"
# Llama 3.3 70B is currently the best balance of speed and logic on Groq
GROQ_MODEL = "llama-3.3-70b-versatile" 

class LLMService:
    def __init__(self):
        #raw_key = os.environ.get("GROQ_API_KEY", "")
        #clean_key = "".join(raw_key.split()).replace("'", "").replace('"', "")
        # 1. Initialize LLM and Embeddings
        self.llm = ChatOllama(model="llama3.2", temperature=0)
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.collection_name = COLLECTION_NAME
        
        
        # Local Embeddings - ensure this matches ingest_data.py
        #self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        # Verify the collection exists
        try:
            count = self.client.get_collection(self.collection_name).points_count
            print(f"✅ Success: Connected to {db_path} with {count} chunks.")
        except Exception as e:
            print(f"❌ DB ERROR: Collection not found! Run ingest_data.py first. Error: {e}")
        # Configuration"
        self.collection_name = COLLECTION_NAME
        
        
        
        # Connection to your local vector store
        try:
            #self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            # Using preferential settings for local dev
            self.client = QdrantClient(path=db_path) 
           
            # Check if data actually exists
            collection_info = self.client.get_collection(self.collection_name)
            count = collection_info.points_count
            self.vectorstore = QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
                embedding=self.embeddings
            )
            print(f"✅ Success: Connected to {db_path} with {count} chunks.")

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

    def generate_rbac_response(self, query, allowed_depts, role_name):
        clean_depts = [d.lower().strip() for d in allowed_depts]
    # Create the metadata filter for RBAC
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="department",
                    match=models.MatchAny(any=clean_depts)
            )
        ]
    )

        # Convert vectorstore to retriever with the filter
        retriever = self.vectorstore.as_retriever(
        search_kwargs={"filter": search_filter, "k": 5}
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
        # --- DEBUG BLOCK START ---
        print(f"\n🔍 DEBUGGING RETRIEVAL FOR: {query}")
        print(f"🔑 Filter depts: {allowed_depts}")
        print(f"📦 Total chunks found: {len(retrieved_docs)}")

        for i, doc in enumerate(retrieved_docs):
            print(f"  [{i}] Source: {doc.metadata.get('source_file')}")
            print(f"  [{i}] Dept Tag: {doc.metadata.get('department')}")
            # print(f"  [{i}] Preview: {doc.page_content[:50]}...") # Optional: see content
        print("--- DEBUG BLOCK END ---\n")
        sources = list(set([doc.metadata.get("source_file") for doc in retrieved_docs]))
        
        answer = rag_chain.invoke(query)

        return {
            "answer": answer,
            "sources": sources
        }

# Singleton instance
llm_service = LLMService()