from fastapi import FastAPI, Form
from .reconmodels import *
import json

app = FastAPI(title="UK Renewable Energy Reconciliation API", version="0.1.9")

@app.get("/")
def mainfest() -> dict:
    return{
        "name": "REPD x NESO TEC Reconciliation",
        "identifierSpace": "https://example.org/renewables/id",
        "schemaSpace": "https://example.org/renewables/schema",
        "defaultTypes": [{"id": "/renewable", "name": "Renewable Facility"}]
    }

#http://127.0.0.1:8001/reconcile?queries={%22q0%22:{%22query%22:%22Aberarder%20Wind%20Farm%22,%22limit%22:3}}

@app.api_route("/reconcile", methods=["GET", "POST"])
def reconcile(queries: str | None = None) -> ResponsePayload:
    queries_dict = json.loads(queries)

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
    
    response_payload = {
        query_id: ReconcileResult(result=searchOne(query)).model_dump()
        for query_id, query in validated_queries.items()
    }

    return response_payload


#@app.get("/")
#async def root():
#    return {"message": "Hello World"}

@app.get("/healthy")
def health():
    return {"status": "ok"}




#https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/
#https://docs.pydantic.dev/1.10/usage/models/