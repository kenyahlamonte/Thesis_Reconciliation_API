from typing import Optional
import re

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

#attempt to ensure highest match possibilties
def normalise_name(s: str) -> str:
    if not s:
        return ""

    s = re.sub(r"[\W_]+", " ", s)

    s = re.sub(r"\s+", " ", s)

    return s.lower().strip()

#determine how similar the names are
def name_similarity(query: str, candidate: str) -> float:
    qn = normalise_name(query)
    cn = normalise_name(candidate)

    if not qn or not cn:
        return 0.0

    if fuzz is not None:
        return float(fuzz.token_set_ratio(qn, cn))

    if qn == cn:
        return 100.0
    if qn in cn or cn in qn:
        return 80.0

    return 0.0

#filter based on +-10% of capacity
def capacity_within_band(query_capacity: Optional[float],
                         project_capacity: Optional[float],
                         band: float = 0.10) -> bool:
    if query_capacity is None or project_capacity is None:
        return True

    return abs(project_capacity - query_capacity) <= band * query_capacity
