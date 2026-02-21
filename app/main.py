"""
UK Renewable Energy Reconciliation Service.

A W3C-compliant reconciliation service for matching project names against the REPD database, using the OpenRefine API.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import Any, cast
from contextlib import asynccontextmanager
import json as _json

from .reconcile_logic import run_reconciliation
from .db_connection import check_database_exists, get_project_count
from .reconmodels import (
    ReconcileQueriesRequest,
    ReconcileResponse,
    ServiceManifest,
    ServiceType,
    HealthResponse,
)
from .logging_config import setup_logging, get_logger

setup_logging(level="INFO")
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - startup and shutdown."""
    logger.info("Reconciliation Service starting up")
    logger.info(f"Service version: 0.2.15")
    
    if check_database_exists():
        count = get_project_count()
        logger.info(f"Database connected: {count} projects loaded")
    else:
        logger.warning("Database not found - Service will return 503 errors")
    
    yield

    logger.info("Reconciliation Service shutting down")

app = FastAPI(
    title="UK Renewable Energy Reconciliation Service",
    description="W3C-compliant reconciliation service for matching renewable energy projects against REPD",
    version="0.2.14",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan, 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3333",
        "http://localhost:3333"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.api_route("/", methods=["GET", "POST"], response_model=ServiceManifest)
def manifest() -> JSONResponse:
    """Service manifest endpoint."""
    logger.debug("Manifest request received")

    payload = ServiceManifest(
        name="REPD x NESO TEC Reconciliation",
        identifierSpace="https://example.org/renewables/id",
        schemaSpace="https://example.org/renewables/schema",
        defaultTypes=[ServiceType(id="/renewable", name="Renewable Facility")]
    )

    return JSONResponse(
        content=payload.model_dump(),
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"}
    )

@app.api_route("/reconcile", methods=["GET", "POST"], response_model=ReconcileResponse)
async def reconcile(
    request: Request,
    q: str | None = None,
    query: str | None = None,
) -> JSONResponse: 
    
    if not check_database_exists():
        logger.error("Database not found - returning 503")
        raise HTTPException(status_code=503, detail="Database not initialised")
    
    #expected OpenRefine standard POST
    payload: str | dict[str, Any] | None = None

    #if not POST then maybe a GET
    if payload is None:
        payload = request.query_params.get("queries")

    #if not a batch then turn into a batch
    single = q or query

    if payload is None and single:
        logger.debug(f"Single query request: '{single}'")
        payload = {"q0": {"query": single, "limit": 3}}

    #check if raw JSON form
    if payload is None and request.method == "POST":
        content_type = request.headers.get("content-type", "")

        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            try:
                form_data = await request.form()
                if "queries" in form_data:
                    payload = str(form_data["queries"])
                    logger.debug("Parsed form-encoded queries")
            except Exception as e:
                logger.warning(f"Form parsing failed: {e}")
                pass  #form parsing failed, try other methods
        
        if payload is None:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    body = cast(dict[str, Any], body)
                    if "queries" in body:
                        payload = body["queries"]
                    elif "query" in body:
                        payload = {"q0": {"query": body["query"], "limit": body.get("limit", 3)}}
                    logger.debug("Parsed JSON queries")
            except Exception as e:
                logger.warning(f"JSON parsing failed: {e}")
                pass  #JSON parsing failed

    #handle missing data
    if payload is None:
        logger.warning("Request missing queries parameter")
        raise HTTPException(
            status_code=422,
            detail="Provide ?queries=..., ?q=..., form queries=..., or JSON {\"queries\":{...}}"
        )

    if isinstance(payload, str):
        try:
            queries_dict = _json.loads(payload)
        except _json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in queries: {e}")
            raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")
    else:
        queries_dict = payload
    
    if not isinstance(queries_dict, dict):
        logger.error(f"Queries must be JSON object, got {type(queries_dict)}")
        raise HTTPException(status_code=422, detail="queries must be JSON object")
    
    #validate with Pydantic
    try:
        validated = ReconcileQueriesRequest.model_validate(queries_dict)
        queries_dict = {qid: query_obj.model_dump() for qid, query_obj in validated.items()}
        logger.info(f"Processing {len(queries_dict)} reconciliation queries")
    except ValidationError as e:
        logger.error(f"Validation error: {e.errors()}")
        raise HTTPException(status_code=422, detail=e.errors())
    
    try:
        response_payload = run_reconciliation(queries_dict)

        total_results = sum(len(result.get("result", [])) for result in response_payload.values())
        logger.info(f"Reconciliation complete: {total_results} total candidates returned")

    except FileNotFoundError as e:
        logger.error(f"Database file not found: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    
    except Exception as e:
        logger.error(f"Reconciliation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reconciliation error: {e}")

    #validate response
    try:
        response = ReconcileResponse.model_validate(response_payload)
    except ValidationError as e:
        logger.error(f"Response validation error: {e.errors()}")
        raise HTTPException(status_code=500, detail=f"Response validation error: {e.errors()}")

    return JSONResponse(
        content=response.model_dump(),
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )

@app.get("/healthy", response_model=HealthResponse)
def health() -> JSONResponse:
    """Health check endpoint."""
    db_exists = check_database_exists()

    if db_exists:
        count = get_project_count()
        logger.debug(f"Health check: OK ({count} projects)")
    else:
        logger.warning("Health check: Database missing")
    
    payload = HealthResponse(
        status="ok" if db_exists else "db_error",
        database="connected" if db_exists else "missing",
        project_count=get_project_count() if db_exists else 0
    )
    
    return JSONResponse(
        content=payload.model_dump(),
        status_code=200 if db_exists else 503,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )

logger.debug("Main module loaded")

#https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/
#https://docs.pydantic.dev/1.10/usage/models/
#https://fastapi.tiangolo.com/tutorial/cors/#use-corsmiddleware
#https://fastapi.tiangolo.com/advanced/response-directly/

