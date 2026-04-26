import os
from dotenv import load_dotenv
from langchain_community.document_loaders import UnstructuredMarkdownLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# UPDATED: Using the dedicated langchain_huggingface package if available, 
# otherwise community is fine, but ensures local execution.
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http import models
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
        dept_tag = dept.lower().strip()
        loader = DirectoryLoader(
            dept_path, 
            glob="**/*.md", 
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'}
        )
        
        try:
            docs = loader.load()
            
            # Apply Metadata Tagging
            # for doc in docs:
            #     doc.metadata["department"] = dept.lower().strip()
            #     #key="department"
            #     # Extract filename safely
            #     source_path = doc.metadata.get("source", "unknown")
            #     doc.metadata["source_file"] = os.path.basename(source_path)
                
            # Chunking Logic
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            for doc in docs:
                # Extract filename for source tracking
                source_path = doc.metadata.get("source", "unknown")
                filename = os.path.basename(source_path)
                
                # Split the document into chunks
                chunks = text_splitter.split_documents([doc])
                # 4. MANUALLY ASSIGN METADATA TO EVERY CHUNK
                # This is the step that was likely missing or failing
                for chunk in chunks:
                    chunk.metadata["department"] = dept_tag
                    chunk.metadata["source_file"] = filename
            
                all_documents.extend(chunks)
                        
            print(f"✅ Processed {len(docs)} files into {len(chunks)} chunks for: {dept_tag}")

        except Exception as e:
            print(f"⚠️ Skipping {dept} due to error: {e}")

    # 5. Upload to Vector Store
    if all_documents:
        print(f"🚀 Uploading {len(all_documents)} total chunks to Qdrant...")
        
        # Initialize the raw client
        client = QdrantClient(path=DB_PATH)
        
        # 1. Clear the collection to ensure a fresh schema
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
        )

        # 2. Extract vectors and upload manually
        # We do this to ensure the payload is EXACTLY what we want
        for i, doc in enumerate(all_documents):
            vector = embeddings.embed_query(doc.page_content)
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=i,
                        vector=vector,
                        payload={
                            "page_content": doc.page_content,
                            "metadata": doc.metadata, # LangChain style nesting
                            "department": doc.metadata.get("department"), # Direct access for filtering
                            "source_file": doc.metadata.get("source_file")
                        }
                    )
                ]
            )
        print("✨ Ingestion Complete via Direct Client.")
    else:
        print("❌ No documents found to ingest.")

if __name__ == "__main__":
    ingest_data_with_rbac()