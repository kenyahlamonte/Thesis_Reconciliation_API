from typing import List, Dict, Optional
from pydantic import BaseModel

class ReconcileQuery(BaseModel):
    query: str
    limit: Optional[int] = 3

class Candidate(BaseModel):
    id: str
    name: str
    location: Optional[str] = None
    type: Optional[str] = None
    score: float
    match: bool

class ReconcileResult(BaseModel):
    result: List[Candidate]

ResponsePayload = Dict[str, ReconcileResult]