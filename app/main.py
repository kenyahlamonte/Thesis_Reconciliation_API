from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Annotated
from .reconmodels import *
import json as _json

app = FastAPI(title="UK Renewable Energy Reconciliation API", version="0.1.11")

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
def mainfest() -> dict:
    payload = {
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
    
) -> dict: 
    
    #expected OpenRefine standard POST
    payload = queries

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
                    payload = body["queries"]

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

    #normalisation
    queries_dict = _json.loads(payload) if isinstance(payload, str) else payload
    
    #validation
    validated_queries = {
        query_id: ReconcileQuery(**query_data)
        for query_id, query_data in queries_dict.items()
    }

    def searchOne(q: ReconcileQuery):
        #matching logic later
        #return one fake match
        return [
            Candidate(
                id="repd001",
                name=q.query,
                location="Scotland",
                type="Wind Onshore",
                score=100,
                match=True
            )
        ]
    
    #build output
    response_payload = {
        query_id: ReconcileResult(result=searchOne(query)).model_dump()
        for query_id, query in validated_queries.items()
    }

    return JSONResponse(
        content=response_payload,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )

@app.get("/healthy")
def health():
    payload = {"status": "ok"}
    return JSONResponse(
        content=payload,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )




#https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/
#https://docs.pydantic.dev/1.10/usage/models/
#https://fastapi.tiangolo.com/tutorial/cors/#use-corsmiddleware
#https://fastapi.tiangolo.com/advanced/response-directly/

