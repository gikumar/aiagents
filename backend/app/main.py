# backend/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from contextlib import asynccontextmanager
from .agentfactory import AgentFactory


# Add the current directory to the Python path
sys.path.append(os.path.dirname(__file__))

# Initialize the agent factory
agent_factory = AgentFactory()

# --- FastAPI Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cleanup on startup and handle shutdown"""
    print("Starting up... Initializing agent factory")
    yield  # App runs here
    print("Shutting down...")  # Add any cleanup here if needed

app = FastAPI(lifespan=lifespan)

# --- CORS Configuration ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class Message(BaseModel):
    role: str  # "user" or "agent"
    content: str
    isError: Optional[bool] = False

class AskRequest(BaseModel):
    agentMode: str
    prompt: str
    file_content: Optional[str] = None
    chat_history: Optional[List[Message]] = None

class AskResponse(BaseModel):
    response: str
    thread_id: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    graph_data: Optional[Dict[str, Any]] = None
    status: str

# --- API Endpoints ---
@app.post("/ask", response_model=AskResponse)
async def ask_agent(request: AskRequest):
    """Enhanced endpoint with graph support and better error handling"""
    try:
        # Input validation
        if not request.prompt and not request.file_content:
            raise HTTPException(
                status_code=400,
                detail="Either prompt or file content must be provided"
            )

        # Convert chat history to the format expected by AgentFactory
        formatted_history = None
        if request.chat_history:
            formatted_history = [
                {
                    "role": msg.role,
                    "content": msg.content
                } 
                for msg in request.chat_history
            ]

        # Process request using AgentFactory
        # The agent factory's process_request2 method handles the SQL generation
        # and tool chaining based on its updated instructions.
        response = agent_factory.process_request2(
            prompt=request.prompt,
            agent_mode=request.agentMode,
            file_content=request.file_content,
            chat_history=formatted_history
        )
        
        return {
            "response": response.response,
            "thread_id": response.thread_id,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "graph_data": response.graph_data,
            "status": "success"
        }

    except HTTPException as http_err:
        # Re-raise HTTP exceptions (like 404, 401)
        raise http_err
        
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error in /ask: {str(e)}", flush=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/")
async def health_check():
    """Enhanced health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Agent Backend",
        "version": "1.1",
        "features": ["text", "graph_generation", "nl_to_sql"] # Added nl_to_sql feature
    }