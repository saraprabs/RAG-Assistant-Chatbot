from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .services.llm_service import llm_service

app = FastAPI()
security = HTTPBasic()
import os
from dotenv import load_dotenv
from pathlib import Path

# Force load .env from the project root (up one level from the 'app' folder)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Verify the key is actually there before starting the API
# if not os.getenv("GROQ_API_KEY"):
#     print("❌ FATAL ERROR: GROQ_API_KEY is missing from environment!")
# else:
#     print(f"✅ GROQ_API_KEY detected: {os.getenv('GROQ_API_KEY')[:6]}...")
# 1. Define the Role-to-Metadata Mapping
# This is the "Source of Truth" for your RBAC
ROLE_DATA_MAPPING: Dict[str, List[str]] = {
    "engineering": ["engineering", "general"],
    "marketing": ["marketing", "general"],
    "finance": ["finance", "general"],
    "hr": ["hr", "general","HR"],
    "c_level": ["engineering", "marketing", "finance", "hr", "general"],
    "employee": ["general"]
}

# Dummy user database
users_db: Dict[str, Dict[str, str]] = {
    "Tony": {"password": "password123", "role": "engineering"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "engineering"},
    "Sid": {"password": "sidpass123", "role": "marketing"},
    "Natasha": {"password": "hrpass123", "role": "hr"}
}


# Authentication dependency
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}


# Login endpoint
@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}


# Protected test endpoint
@app.get("/test")
def test(user=Depends(authenticate)):
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}


# Protected chat endpoint
@app.post("/chat")
async def query_chatbot(message: str, user=Depends(authenticate)):
    """
    Handles user queries by enforcing department-level data silos.
    """
    user_role = user["role"]
    
    # Identify which departments this user is allowed to "see"
    allowed_depts = ROLE_DATA_MAPPING.get(user_role.lower(), ["general"])
    
    try:
        # Pass the query and the role-based filter to the RAG service
        result = llm_service.generate_rbac_response(
            query=message,
            allowed_depts=allowed_depts,
            role_name=user_role
        )
        
        return {
            "username": user["username"],
            "role": user_role,
            "authorized_access": allowed_depts,
            "answer": result["answer"],
            "sources": result["sources"]
        }
        
    except Exception as e:
        # Log error for Peter's debugging
        print(f"Error in chat execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))