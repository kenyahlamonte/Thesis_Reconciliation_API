from typing import Optional
import re

#attempt to ensure highest match possibilties
def normalise_name(s: str) -> str:
    return s

#determine how similar the names are
def name_similarity(query: str, candidate: str) -> float:
    return 0.0

#filter based on +-10% of capacity
def capacity_within_band(query_capacity: Optional[float],
                         project_capacity: Optional[float],
                         band: float = 0.10) -> bool:
    return True