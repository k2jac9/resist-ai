"""ResistAI FastAPI server for AMR drug discovery pipeline.

Exposes NVIDIA NIM biology models and the full pipeline orchestrator
as a production-ready REST API with auth, CORS, timing, and health checks.

Run with: uvicorn src.api.server:app --port 8000
"""
from __future__ import annotations

import hmac
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class PipelineRequest(BaseModel):
    pathogen: str = Field(..., description="Pathogen identifier, e.g. acinetobacter_baumannii")
    max_drugs: int = Field(100, ge=1, le=500, description="Max compounds to screen per target")
    generate_novel: bool = Field(True, description="Run MolMIM novel molecule generation")


class BindingRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=10, description="Amino acid sequence")
    ligand_smiles: str = Field(..., min_length=1, description="Ligand SMILES string")


class StructureRequest(BaseModel):
    sequence: str = Field(..., min_length=10, description="Amino acid sequence")


class GenerateRequest(BaseModel):
    seed_smiles: str = Field(..., min_length=1, description="Seed molecule SMILES")
    num_molecules: int = Field(5, ge=1, le=50, description="Number of molecules to generate")
    optimize: str = Field("QED", description="Property to optimize (QED, logP, etc.)")


class DNAGenerateRequest(BaseModel):
    sequence: str = Field(..., min_length=5, description="Input DNA sequence (A/T/G/C)")
    num_tokens: int = Field(256, ge=1, le=2048, description="Nucleotide tokens to generate")


class DockRequest(BaseModel):
    protein_pdb: str = Field(..., min_length=10, description="Protein PDB structure string")
    ligand_smiles: str = Field(..., min_length=1, description="Ligand SMILES string")
    num_poses: int = Field(5, ge=1, le=20, description="Number of docking poses")


class BinderRequest(BaseModel):
    target_sequence: str = Field(..., min_length=10, description="Target protein sequence")
    contigs: Optional[str] = Field(None, description="RFdiffusion contig specification")


class APIResponse(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle: log NIM availability on boot."""
    nim = _get_nim()
    if nim.available:
        logger.info("NIM client available with API key")
    else:
        logger.warning("NIM client unavailable -- endpoints will use fallback/mock data")
    yield


app = FastAPI(
    title="ResistAI API",
    description="AMR drug discovery pipeline powered by NVIDIA NIM biology models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS: never combine a wildcard origin with credentials. Origins are read
# from RESISTAI_CORS_ORIGINS (comma-separated); default is no cross-origin
# access. Set to "*" explicitly only for local/dev use (credentials disabled).
_cors_origins_env = os.environ.get("RESISTAI_CORS_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
_allow_credentials = bool(_cors_origins) and "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_REQUIRED_KEY = os.environ.get("RESISTAI_API_KEY", "")
# Fail closed unless the operator explicitly opts out of auth for local dev.
_ALLOW_NO_AUTH = os.environ.get("RESISTAI_ALLOW_NO_AUTH", "").lower() in ("1", "true", "yes")

if not _REQUIRED_KEY and not _ALLOW_NO_AUTH:
    logger.warning(
        "RESISTAI_API_KEY is not set -- all endpoints will reject requests with 503. "
        "Set RESISTAI_API_KEY to enable the API, or RESISTAI_ALLOW_NO_AUTH=true for local dev."
    )


async def verify_api_key(api_key: Optional[str] = Security(_api_key_header)) -> Optional[str]:
    """Validate the X-API-Key header.

    Fails closed: if no key is configured the API is disabled (503) unless
    RESISTAI_ALLOW_NO_AUTH is explicitly enabled. Comparison is timing-safe.
    """
    if not _REQUIRED_KEY:
        if _ALLOW_NO_AUTH:
            return api_key
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured. Set RESISTAI_API_KEY.",
        )
    if not api_key or not hmac.compare_digest(api_key, _REQUIRED_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


# ---------------------------------------------------------------------------
# Timing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    elapsed = (time.time() - t0) * 1000
    response.headers["X-Response-Time-Ms"] = f"{elapsed:.1f}"
    return response


# ---------------------------------------------------------------------------
# Lazy-loaded clients (avoid import errors at module level)
# ---------------------------------------------------------------------------

_nim_client = None
_orchestrator = None


def _get_nim():
    global _nim_client
    if _nim_client is None:
        from src.models.nim_client import NIMClient
        _nim_client = NIMClient()
    return _nim_client


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from src.pipeline.orchestrator import PipelineOrchestrator
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


def _result_to_dict(result: Any) -> dict:
    """Convert a dataclass result to a plain dict."""
    if hasattr(result, "to_dict"):
        return result.to_dict()
    return asdict(result)


def _timed(func, *args, **kwargs) -> tuple[Any, float]:
    """Call func and return (result, elapsed_ms)."""
    t0 = time.time()
    result = func(*args, **kwargs)
    return result, (time.time() - t0) * 1000


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/pipeline/run", response_model=APIResponse)
def run_pipeline(req: PipelineRequest, _key: str = Security(verify_api_key)):
    """Run the full AMR drug discovery pipeline for a pathogen."""
    try:
        orch = _get_orchestrator()
        result, elapsed = _timed(
            orch.run_full_pipeline,
            pathogen_name=req.pathogen,
            max_drugs=req.max_drugs,
            generate_novel=req.generate_novel,
        )
        return APIResponse(success=True, data=result.to_dict(), elapsed_ms=round(elapsed, 1))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/predict/binding", response_model=APIResponse)
def predict_binding(req: BindingRequest, _key: str = Security(verify_api_key)):
    """Predict protein-ligand binding affinity using Boltz-2."""
    nim = _get_nim()
    if not nim.available:
        raise HTTPException(status_code=503, detail="NIM client unavailable (no API key)")
    try:
        result, elapsed = _timed(nim.predict_binding, req.protein_sequence, req.ligand_smiles)
        return APIResponse(success=result.success, data=_result_to_dict(result), elapsed_ms=round(elapsed, 1))
    except Exception as exc:
        logger.exception("Binding prediction failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/predict/structure", response_model=APIResponse)
def predict_structure(req: StructureRequest, _key: str = Security(verify_api_key)):
    """Predict protein 3D structure using ESMFold."""
    nim = _get_nim()
    if not nim.available:
        raise HTTPException(status_code=503, detail="NIM client unavailable (no API key)")
    try:
        result, elapsed = _timed(nim.fold_protein, req.sequence)
        return APIResponse(success=result.success, data=_result_to_dict(result), elapsed_ms=round(elapsed, 1))
    except Exception as exc:
        logger.exception("Structure prediction failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/generate/molecules", response_model=APIResponse)
def generate_molecules(req: GenerateRequest, _key: str = Security(verify_api_key)):
    """Generate novel optimized molecules using MolMIM."""
    nim = _get_nim()
    if not nim.available:
        raise HTTPException(status_code=503, detail="NIM client unavailable (no API key)")
    try:
        result, elapsed = _timed(
            nim.generate_molecules,
            seed_smiles=req.seed_smiles,
            num_molecules=req.num_molecules,
            property_name=req.optimize,
        )
        return APIResponse(success=result.success, data=_result_to_dict(result), elapsed_ms=round(elapsed, 1))
    except Exception as exc:
        logger.exception("Molecule generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/generate/dna", response_model=APIResponse)
def generate_dna(req: DNAGenerateRequest, _key: str = Security(verify_api_key)):
    """Generate DNA sequences using Evo2-40b."""
    nim = _get_nim()
    if not nim.available:
        raise HTTPException(status_code=503, detail="NIM client unavailable (no API key)")
    try:
        result, elapsed = _timed(nim.generate_dna, req.sequence, req.num_tokens)
        return APIResponse(success=result.success, data=_result_to_dict(result), elapsed_ms=round(elapsed, 1))
    except Exception as exc:
        logger.exception("DNA generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/dock", response_model=APIResponse)
def dock_molecule(req: DockRequest, _key: str = Security(verify_api_key)):
    """Predict 3D binding pose using DiffDock."""
    nim = _get_nim()
    if not nim.available:
        raise HTTPException(status_code=503, detail="NIM client unavailable (no API key)")
    try:
        result, elapsed = _timed(
            nim.dock_molecule,
            protein_pdb=req.protein_pdb,
            ligand_smiles=req.ligand_smiles,
            num_poses=req.num_poses,
        )
        return APIResponse(success=result.success, data=_result_to_dict(result), elapsed_ms=round(elapsed, 1))
    except Exception as exc:
        logger.exception("Docking failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/design/binder", response_model=APIResponse)
def design_binder(req: BinderRequest, _key: str = Security(verify_api_key)):
    """Design a protein binder using RFdiffusion + ProteinMPNN.

    First folds the target sequence with ESMFold, then designs a binder
    backbone with RFdiffusion, and finally designs sequences with ProteinMPNN.
    """
    nim = _get_nim()
    if not nim.available:
        raise HTTPException(status_code=503, detail="NIM client unavailable (no API key)")
    try:
        t0 = time.time()

        # Step 1: Fold target
        fold = nim.fold_protein(req.target_sequence)
        if not fold.success:
            raise HTTPException(status_code=422, detail="ESMFold failed to fold target sequence")

        # Step 2: Design binder backbone
        n_res = min(len(req.target_sequence), 60)
        contigs = req.contigs or f"10-30/A1-{n_res}/10-30"
        backbone = nim.design_binder(fold.pdb_string, contigs=contigs)
        if not backbone.success:
            raise HTTPException(status_code=422, detail="RFdiffusion binder design failed")

        # Step 3: Design sequences for backbone
        sequences = nim.design_sequence(backbone.pdb_string)

        elapsed = (time.time() - t0) * 1000
        data = {
            "backbone_residues": backbone.num_residues,
            "backbone_elapsed_ms": backbone.elapsed_ms,
            "sequences": _result_to_dict(sequences) if sequences.success else None,
            "contigs_used": contigs,
        }
        return APIResponse(success=sequences.success, data=data, elapsed_ms=round(elapsed, 1))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Binder design failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/v1/health", response_model=APIResponse)
def health_check():
    """Check availability of all NIM endpoints."""
    nim = _get_nim()
    if not nim.available:
        return APIResponse(
            success=False,
            data={"nim_available": False, "endpoints": {}},
            error="NIM client unavailable (no API key)",
        )
    try:
        result, elapsed = _timed(nim.health_check)
        all_ok = all(result.values())
        return APIResponse(
            success=all_ok,
            data={"nim_available": True, "endpoints": result},
            elapsed_ms=round(elapsed, 1),
        )
    except Exception as exc:
        logger.exception("Health check failed")
        return APIResponse(success=False, error="Health check failed")


@app.get("/v1/models", response_model=APIResponse)
def list_models():
    """List available NIM models and their status."""
    from src.models.nim_client import ENDPOINTS

    nim = _get_nim()
    models = []
    for name, url in ENDPOINTS.items():
        models.append({
            "name": name,
            "url": url,
            "available": nim.available,
        })
    return APIResponse(
        success=True,
        data={
            "nim_configured": nim.available,
            "model_count": len(models),
            "models": models,
        },
    )


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "data": None, "elapsed_ms": 0.0},
    )
