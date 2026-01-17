from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Annotated, Any, Dict, cast
import json as _json

from .reconcile_logic import run_reconciliation
from .db_connection import check_database_exists, get_project_count

app = FastAPI(title="UK Renewable Energy Reconciliation Service", version="0.2.5")

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

@app.get("/")
def mainfest() -> JSONResponse:
    payload : Dict[str, Any] = {
        "name": "REPD x NESO TEC Reconciliation",
        "identifierSpace": "https://example.org/renewables/id",
        "schemaSpace": "https://example.org/renewables/schema",
        "defaultTypes": [{"id": "/renewable", "name": "Renewable Facility"}]
    }

    return JSONResponse(
        content=payload,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"}
    )

#http://127.0.0.1:8001/reconcile?queries={%22q0%22:{%22query%22:%22Aberarder%20Wind%20Farm%22,%22limit%22:3}}

@app.api_route("/reconcile", methods=["GET", "POST"])
async def reconcile(
    request: Request,

    #parameters
    queries: Annotated[Optional[str], Form()] = None,
    q: Optional[str] = None,
    query: Optional[str] = None,
    
) -> JSONResponse: 
    
    if not check_database_exists():
        raise HTTPException(status_code=503, detail="Database not initialised)")
    #expected OpenRefine standard POST
    payload: str | dict[str, Any] | None = None

    #if not POST then maybe a GET
    if payload is None:
        payload = request.query_params.get("queries")

    #if not a batch then turn into a batch
    single = q or query

    if payload is None and single:
        payload = {"q0": {"query": single, "limit": 3}}

    #check if raw JSON form
    if payload is None and request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                if "queries" in body:
                    payload = cast(dict[str, Any], body["queries"])

                #wrap into batch
                elif "query" in body:
                    payload = {"q0": {"query": body["query"], "limit": 3}}
        except Exception:
            pass

    #handle missing data
    if payload is None:
        raise HTTPException(
            status_code=422,
            detail="Provide ?queries=..., ?q=..., form queries=..., or JSON {\"queries\":{...}}"
        )

    if isinstance(payload, str):
        try:
            queries_dict = _json.loads(payload)
        except _json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalide JSON: {e}")
    else:
        queries_dict = payload
    
    if not isinstance(queries_dict, dict):
        raise HTTPException(status_code=400, detail="queries must be JSON object")
    
    try:
        response_payload = run_reconciliation(cast(dict[str, Any], queries_dict))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation error: {e}")

    return JSONResponse(
        content=response_payload,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )

@app.get("/healthy")
def health():
    db_exists = check_database_exists()
    payload : Dict[str, Any] = {
            "status": "ok" if db_exists else "db error",
            "database": "connected" if db_exists else "missing",
            "project_count": get_project_count() if db_exists else 0}
    
    return JSONResponse(
        content=payload,
        status_code = 200 if db_exists else 503,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )




#https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/
#https://docs.pydantic.dev/1.10/usage/models/
#https://fastapi.tiangolo.com/tutorial/cors/#use-corsmiddleware
#https://fastapi.tiangolo.com/advanced/response-directly/

