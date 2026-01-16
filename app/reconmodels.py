from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class ReconcileQueryProperty(BaseModel):
    pid: str
    v: Any

class ReconcileQuery(BaseModel):
    query: str
    limit: Optional[int] = Field(default=3, ge=1, le=100)
    type: Optional[str] = None
    type_strict: Optional[str] = None
    properties: Optional[List[ReconcileQueryProperty]] = None

class CandidateType(BaseModel):
    id: str
    name: str

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