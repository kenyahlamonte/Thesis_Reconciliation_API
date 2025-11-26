from typing import List, Dict, Any, Optional
from reconcile_record import ProjectRecord
from reconcile_norm_score import capacity_within_band, name_similarity
from projects_small_case import PROJECTS

#look for matching properties based on pid
def extract_capacity_from_properties(props: List[Dict[str, Any]]) -> Optional[float]:
    for p in props or []:
        pid = p.get("pid")

        if pid in {"capacity_mw", "capacity", "Capacity (MW)"}:
            try:
                return float(p.get("v"))
            except (TypeError, ValueError):
                continue
    
    return None

#run matching for one query in the map
def reconcile_single_query(query_obj: Dict[str, Any],
                           candidates: List[ProjectRecord],
                           top_n: int = 5) -> List[Dict[str, Any]]:
    query_str = query_obj.get("query") or ""
    if not query_str:
        return []
    
    limit = query_obj.get("limit") or top_n
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = top_n

    props = query_obj.get("properties") or []
    query_capacity = extract_capacity_from_properties(props)

    scored: List[Dict[str, Any]] = []

    for proj in candidates:
        if not capacity_within_band(query_capacity, proj.capacity_mw, band=0.10):
            continue

        score = name_similarity(query_str, proj.name)
        if score <= 0:
            continue
        
        #crude selection for now
        is_match = score >= 90.0

        #openrefine dict
        scored.append(
            {
                "id": proj.id,
                "name": proj.name,
                "score": int(score),
                "match": is_match,
                "type": [
                    {"id": "project", "name": "Project"}
                ]
            }
        )

    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:limit]

#helper
def run_reconciliation(queries_obj: Dict[str, Any]) -> Dict[str, Any]:
    response: Dict[str, Any] = {}

    for qid, q in queries_obj.items():
        results = reconcile_single_query(q, PROJECTS)
        response[qid] = {"result": results}
    
    return response

