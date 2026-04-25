import os
from dotenv import load_dotenv
from langchain_community.document_loaders import UnstructuredMarkdownLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# UPDATED: Using the dedicated langchain_huggingface package if available, 
# otherwise community is fine, but ensures local execution.
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
import shutil

# Load environment variables
load_dotenv()

# Configuration
BASE_DATA_DIR = "resources/data"
COLLECTION_NAME = "finsolve_knowledge_base"
DB_PATH = "./qdrant_db"

def ingest_data_with_rbac():
    # 1. Initialize local embeddings
    # This runs on your CPU. No API key needed for this step!
    print("⏳ Loading embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # 2. Cleanup old data
    # This prevents "vector dimension mismatch" if you previously used OpenAI
    if os.path.exists(DB_PATH):
        print(f"🧹 Clearing old database at {DB_PATH}...")
        shutil.rmtree(DB_PATH)
    
    all_documents = []
    
    # 3. Check if data directory exists
    if not os.path.exists(BASE_DATA_DIR):
        print(f"❌ Error: Data directory {BASE_DATA_DIR} not found!")
        return

    # 4. Iterate through department folders
    departments = [d for d in os.listdir(BASE_DATA_DIR) if os.path.isdir(os.path.join(BASE_DATA_DIR, d))]
    print(f"🔍 Found departments: {departments}")

    for dept in departments:
        dept_path = os.path.join(BASE_DATA_DIR, dept)
        
        loader = DirectoryLoader(
            dept_path, 
            glob="**/*.md", 
            loader_cls=UnstructuredMarkdownLoader
        )
        
        try:
            docs = loader.load()
            
            # Apply Metadata Tagging
            for doc in docs:
                doc.metadata["department"] = dept.lower()
                # Extract filename safely
                source_path = doc.metadata.get("source", "unknown")
                doc.metadata["source_file"] = os.path.basename(source_path)
                
            # Chunking Logic
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunked_docs = text_splitter.split_documents(docs)
            
            all_documents.extend(chunked_docs)
            print(f"✅ Processed {len(chunked_docs)} chunks for {dept}")
        except Exception as e:
            print(f"⚠️ Skipping {dept} due to error: {e}")

    # 5. Upload to Vector Store
    if all_documents:
        print(f"🚀 Uploading {len(all_documents)} total chunks to Qdrant...")
        Qdrant.from_documents(
            all_documents,
            embeddings,
            path=DB_PATH,
            collection_name=COLLECTION_NAME,
        )
        print("✨ Ingestion Complete. You can now start the FastAPI server.")
    else:
        print("❌ No documents found to ingest.")

if __name__ == "__main__":
    ingest_data_with_rbac()