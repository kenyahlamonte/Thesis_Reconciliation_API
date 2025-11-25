from typing import List, Dict, Any, Optional
from reconcile_record import ProjectRecord

#look for matching properties based on pid
def extract_capacity_from_properties(props: List[Dict[str, Any]]) -> Optional[float]:
    return None

#run matching for one query in the map
def reconcile_single_query(query_obj: Dict[str, Any],
                           candidates: List[ProjectRecord],
                           top_n: int = 5) -> List[Dict[str, Any]]:
    return[]

#helper
def run_reconciliation(queries_obj: Dict[str, Any]) -> Dict[str, Any]:
    response: Dict[str, Any] = {}
    
    return response

