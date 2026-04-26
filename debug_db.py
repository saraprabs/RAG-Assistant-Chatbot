import os
from qdrant_client import QdrantClient

# Configuration - update DB_PATH if your folder is named differently
DB_PATH = "./qdrant_db"
COLLECTION_NAME = "finsolve_knowledge_base"

def inspect_tags():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database directory not found at {DB_PATH}")
        return

    # 1. Initialize Client
    client = QdrantClient(path=DB_PATH)
    
    print(f"🔍 Accessing collection: {COLLECTION_NAME}...")
    
    try:
        # 2. Scroll through all points to extract metadata
        # Note: 'with_payload=True' is required to see the tags
        points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000, # Adjust if you have more than 1000 chunks
            with_payload=True,
            with_vectors=False
        )
        
        # 3. Extract unique tags
        found_tags = set()
        for p in points:
            dept = p.payload.get("department")
            if dept:
                found_tags.add(dept)
        
        # 4. Display Results
        if not found_tags:
            print("⚠️ No tags found. Either the collection is empty or 'department' key is missing.")
        else:
            print("\n✅ Unique Department Tags found in DB:")
            for tag in sorted(list(found_tags)):
                # Printing with quotes to spot accidental spaces like " finance"
                print(f"  - '{tag}'")
                
    except Exception as e:
        print(f"❌ Error accessing Qdrant: {e}")

if __name__ == "__main__":
    inspect_tags()