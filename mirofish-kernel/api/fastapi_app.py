"""
MiroFish Kernel — Minimal FastAPI API

Thin REST adapter over the PipelineOrchestrator.
Keeps all logic in the kernel — API is just HTTP ↔ function mapping.

Usage:
    uvicorn api.fastapi_app:app --reload --port 5001
"""

import os
from typing import Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
except ImportError:
    raise ImportError("FastAPI required: pip install mirofish-kernel[fastapi]")

from core import PipelineOrchestrator
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.graph.zep_adapter import ZepGraphAdapter
from adapters.simulation.mock_engine import MockSimulationEngine
from adapters.memory.local_memory import LocalMemoryStore


# ─── Globals ───────────────────────────────────────────────────
pipeline: Optional[PipelineOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize pipeline on startup."""
    global pipeline
    
    llm_key = os.environ.get("LLM_API_KEY")
    zep_key = os.environ.get("ZEP_API_KEY")
    
    if not llm_key:
        raise RuntimeError("LLM_API_KEY environment variable required")
    if not zep_key:
        raise RuntimeError("ZEP_API_KEY environment variable required")
    
    llm = OpenAIAdapter(
        api_key=llm_key,
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini"),
    )
    graph_store = ZepGraphAdapter(api_key=zep_key)
    sim_engine = MockSimulationEngine()
    memory = LocalMemoryStore()
    
    pipeline = PipelineOrchestrator(
        llm=llm,
        graph_store=graph_store,
        simulation_engine=sim_engine,
        memory_store=memory,
    )
    
    yield
    
    pipeline = None


app = FastAPI(
    title="MiroFish Kernel API",
    description="Swarm Intelligence Engine — Prediction API",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ─────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "MiroFish Kernel API"}


@app.post("/api/predict")
async def predict(
    requirement: str = Form(...),
    text: Optional[str] = Form(None),
    project_name: str = Form("MiroFish Analysis"),
):
    """
    Run the full prediction pipeline.
    
    Send seed text + requirement, get back a prediction report.
    """
    if not pipeline:
        raise HTTPException(500, "Pipeline not initialized")
    if not text:
        raise HTTPException(400, "Either text or file upload required")
    
    try:
        result = pipeline.run(
            requirement=requirement,
            text=text,
            project_name=project_name,
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/chat/{project_id}")
async def chat(project_id: str, message: str = Form(...)):
    """Chat with the report agent about a completed analysis."""
    if not pipeline:
        raise HTTPException(500, "Pipeline not initialized")
    
    try:
        response = pipeline.chat_with_report(project_id, message)
        return {"response": response}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/project/{project_id}")
async def get_project(project_id: str):
    """Get project status and info."""
    if not pipeline:
        raise HTTPException(500, "Pipeline not initialized")
    
    project = pipeline.get_project(project_id)
    if not project:
        raise HTTPException(404, f"Project {project_id} not found")
    
    return project.to_dict()
