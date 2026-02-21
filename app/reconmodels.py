"""
Pydantic models for W3C Reconciliation Service API.

Reference: https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/
"""

from typing import Annotated, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, RootModel

# =============================================================================
#  request
# =============================================================================

class ReconcileQueryProperty(BaseModel):
    """A property constraint for filtering reconciliation candidates."""
    model_config = ConfigDict(extra="forbid")

    pid: Annotated[str, Field(description="Property identifier (e.g., 'MW Connected')")]
    v: Annotated[Any, Field(description="Property value to match")]

class ReconcileQuery(BaseModel):
    """A single reconciliation query following the W3C spec."""

    model_config = ConfigDict(extra="ignore")  # Allow unknown fields for forward compatibility

    query: Annotated[str, Field(min_length=1, description="The text to reconcile")]
    limit: Annotated[int, Field(default=3, ge=1, le=100, description="Maximum candidates to return")]
    type: Annotated[str | None, Field(default=None, description="Type filter (e.g., '/renewable')")]
    type_strict: Annotated[str | None, Field(default=None, description="Strictness: 'any', 'all', 'should'")]
    properties: Annotated[
        list[ReconcileQueryProperty] | None,
        Field(default=None, description="Property constraints for filtering")
    ]

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()

class ReconcileQueriesRequest(RootModel[dict[str, ReconcileQuery]]):
    """
    Batch reconciliation request: a mapping of query IDs to queries.

    Example:
        {
            "q0": {"query": "Aberarder Wind Farm", "limit": 3},
            "q1": {"query": "Moray Offshore", "limit": 5}
        }
    """

    def __getitem__(self, key: str) -> ReconcileQuery:
        return self.root[key]

    def items(self) -> list[tuple[str, ReconcileQuery]]:
        return list(self.root.items())

    def keys(self) -> list[str]:
        return list(self.root.keys())

# =============================================================================
#  response
# =============================================================================

class CandidateType(BaseModel):
    """Type information for a reconciliation candidate."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(description="Type identifier", examples=["/renewable", "/technology/wind"])]
    name: Annotated[str, Field(description="Human-readable type name", examples=["Renewable Facility", "Wind"])]

class Candidate(BaseModel):
    """A single reconciliation candidate result."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(description="Unique identifier for the matched entity", examples=["repd-1234"])]
    name: Annotated[str, Field(description="Display name of the matched entity")]
    score: Annotated[float, Field(ge=0, le=100, description="Confidence score (0-100)")]
    match: Annotated[bool, Field(description="True if this is a confident match (score >= 90)")]
    type: Annotated[
        list[CandidateType],
        Field(default_factory=list, description="Types associated with this candidate")
    ]
    description: Annotated[
        str | None,
        Field(default=None, description="Additional details about the candidate")
    ]

class ReconcileResult(BaseModel):
    """Result for a single reconciliation query."""

    model_config = ConfigDict(extra="forbid")

    result: Annotated[list[Candidate], Field(description="Ranked list of matching candidates")]

class ReconcileResponse(RootModel[dict[str, ReconcileResult]]):
    """
    Batch reconciliation response: a mapping of query IDs to results.

    Example:
        {
            "q0": {"result": [{"id": "repd-1", "name": "...", "score": 95.0, "match": true, "type": [...]}]},
            "q1": {"result": [...]}
        }
    """
    pass

# =============================================================================
#  manifest
# =============================================================================

class ServiceType(BaseModel):
    """A type supported by the reconciliation service."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(description="Type identifier")]
    name: Annotated[str, Field(description="Human-readable name")]


class ServiceManifest(BaseModel):
    """
    Service manifest describing the reconciliation endpoint.

    Returned by GET/POST to the service root.
    """

    model_config = ConfigDict(extra="allow")  # Allow extension fields

    name: Annotated[str, Field(description="Human-readable service name")]
    identifierSpace: Annotated[str, Field(description="URI for the identifier namespace")]
    schemaSpace: Annotated[str, Field(description="URI for the schema namespace")]
    defaultTypes: Annotated[
        list[ServiceType],
        Field(default_factory=list, description="Default types for queries without type constraints")
    ]

# =============================================================================
#  health
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(extra="forbid")

    status: Annotated[str, Field(description="Service status", examples=["ok", "db_error"])]
    database: Annotated[str, Field(description="Database connection status")]
    project_count: Annotated[int, Field(ge=0, description="Number of projects in database")]
