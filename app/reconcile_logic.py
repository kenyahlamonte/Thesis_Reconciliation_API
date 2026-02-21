from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from .db_connection import (
    ProjectRecord,
    fetch_all_projects,
    check_database_exists,
    DEFAULT_DB_PATH,
)

from .reconcile_norm_score import(
    capacity_within_band,
    name_similarity,
    normalise_name,
)

from .extract_from_query import extract_properties
from .logging_config import get_logger

logger = get_logger(__name__)

# -----------------------------
#  cache
# -----------------------------

_cache: Dict[str, list[ProjectRecord]] = {}

def get_projects(db_path: Path = DEFAULT_DB_PATH) -> List[ProjectRecord]:
    cache_key = str(db_path)

    if cache_key in _cache:
        logger.debug(f"Cache HIT: {len(_cache[cache_key])} projects from cache")
        return _cache[cache_key]

    if not check_database_exists(db_path):
        logger.error(f"Database not found at {db_path}")
        raise FileNotFoundError(
            f"Database not found at {db_path}"
            "Run create_SQLite_DB_from_CSV.py first :)"
        )

    logger.info(f"Loading projects from database: {db_path}")
    _cache[cache_key] = fetch_all_projects(db_path)
    logger.info(f"Loaded {len(_cache[cache_key])} projects into cache")

    return _cache[cache_key]

def clear_projects_cache() -> None:
    count = sum(len(projects) for projects in _cache.values())
    _cache.clear()

    countCleared = sum(len(projects) for projects in _cache.values())
    if countCleared == 0:
        logger.info(f"Cache cleared ({count} projects removed)")
    else:
        logger.info(f"Cache not cleared ({countCleared} remaining of {count} projects)")

# -----------------------------
#  blocking
# -----------------------------

def generate_blocks(name_normalised: str) -> Set[str]:
    blocks: Set[str] = set()

    if not name_normalised:
        return blocks

    words = name_normalised.split()
    blocks.update(words)

    for word in words:
        if len(word) >= 4:
            blocks.add(word[:4])

    if len(name_normalised) >= 4:
        blocks.add(name_normalised[:4])

    return blocks

def generate_project_blocks(proj: ProjectRecord) -> Set[str]:
    blocks: Set[str] = set()

    blocks.update(generate_blocks(proj.name_normalised))

    if proj.site_name_normalised:
        blocks.update(generate_blocks(proj.site_name_normalised))

    if proj.developer_normalised:
        blocks.update(generate_blocks(proj.developer_normalised))

    return blocks

def get_blocked_candidates(
        query_normalised: str,
        projects: List[ProjectRecord],
        min_candidates: int = 10
) -> List[ProjectRecord]:
    query_blocks = generate_blocks(query_normalised)

    if not query_blocks:
        logger.debug("No query blocks generated, returning all projects")
        return projects

    blocked = [
        p for p in projects
        if query_blocks & generate_project_blocks(p)
    ]

    if len(blocked) < min_candidates:
        logger.debug(f"Blocking found {len(blocked)} candidates (< {min_candidates}), using prefix fallback")
        prefix = query_normalised[:3] if len(query_normalised) >= 3 else query_normalised
        blocked = [
            p for p in projects
            if prefix in p.name_normalised
            or prefix in (p.site_name_normalised or "")
            or prefix in (p.developer_normalised or "")
        ]
    else:
        reduction_pct = (1 - len(blocked) / len(projects)) * 100
        logger.debug(f"Blocking: {len(projects)} → {len(blocked)} candidates ({reduction_pct:.1f}% reduction)")


    return blocked if len(blocked) >= min_candidates else projects

# -----------------------------
#  scoring
# -----------------------------

def score_candidate(
    query_str: str,
    query_normalise: str,
    query_props: Dict[str, Any],
    project: ProjectRecord
) -> float:

    score_name = name_similarity(query_str, project.name)

    score_site = 0.0
    if project.site_name:
        score_site = name_similarity(query_str, project.site_name)

    score_dev = 0.0
    if project.developer:
        dev_query = query_props.get('customer_name') or query_str
        score_dev = name_similarity(dev_query, project.developer)

    score_tech = 0.0
    query_tech = query_props.get('plant_type')
    if query_tech and project.technology:
        score_tech = name_similarity(query_tech, project.technology)

    score = (
        score_name * 0.50 +
        score_site * 0.20 +
        score_dev * 0.15 +
        score_tech * 0.05
    )

    query_capacity = query_props.get('capacity_mw')
    if query_capacity is not None and project.capacity_mw is not None:
        if capacity_within_band(query_capacity, project.capacity_mw, band=0.05):
            score += 10
        elif capacity_within_band(query_capacity, project.capacity_mw, band=0.15):
            score += 5
        elif capacity_within_band(query_capacity, project.capacity_mw, band=0.25):
            score += 2

    return min(score, 100.0)

# -----------------------------
#  reconciliation
# -----------------------------

#run matching for one query in the map
def reconcile_single_query(
        query_obj: Dict[str, Any],
        candidates: Optional[List[ProjectRecord]] = None,
        top_n: int = 5
) -> List[Dict[str, Any]]:

    query_str = query_obj.get("query") or ""
    if not query_str:
        logger.warning("Empty query string provided")
        return []

    limit = query_obj.get("limit") or top_n
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        logger.warning(f"Invalid limit value: {limit}, using default {top_n}")
        limit = top_n

    if candidates is None:
        candidates = get_projects()

    logger.debug(f"Reconciling query: '{query_str}' (limit={limit})")

    query_normalised = normalise_name(query_str)
    query_props = extract_properties(query_obj.get("properties"))

    blocked = get_blocked_candidates(query_normalised, candidates)

    scored: List[Dict[str, Any]] = []

    for proj in blocked:
        score = score_candidate(query_str, query_normalised, query_props, proj)

        if score <= 0:
            continue

        result_type: list[Dict[str, str]] = []

        if proj.technology:
            result_type.append({
                "id": f"/technology/{proj.technology.lower().replace(' ', '_')}",
                "name": proj.technology
            })
        else:
            result_type.append({"id": "/renewable", "name": "Renewable Facility"})

        scored.append({
            "id": proj.id,
            "name": proj.name,
            "score": round(score, 2),
            "match": score >= 90.0,
            "type": result_type,
            "description": _build_description(proj),
        })

    scored.sort(key=lambda r: r["score"], reverse=True)
    results = scored[:limit]

    #log top result
    if results:
        top = results[0]
        logger.info(f"Query '{query_str}' → Top match: '{top['name']}' (score: {top['score']}, match: {top['match']})")
    else:
        logger.warning(f"Query '{query_str}' → No matches found")

    logger.debug(f"Returning {len(results)} results (from {len(scored)} scored candidates)")

    return results

def _build_description(proj: ProjectRecord) -> str:
    parts: list[str] = []
    if proj.technology:
        parts.append(proj.technology)
    if proj.capacity_mw:
        parts.append(f"{proj.capacity_mw} MW")
    if proj.status:
        parts.append(proj.status)
    if proj.developer:
        parts.append(f"Developer: {proj.developer}")
    if proj.site_name:
        parts.append(f"Site: {proj.site_name}")
    return " | ".join(parts)


def run_reconciliation(
    queries_obj: Dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH
) -> Dict[str, Any]:

    logger.info(f"Running reconciliation for {len(queries_obj)} queries")
    candidates = get_projects(db_path)

    results = {
        qid: {"result": reconcile_single_query(q, candidates)}
        for qid, q in queries_obj.items()
    }

    logger.debug("Reconciliation batch complete")
    return results
