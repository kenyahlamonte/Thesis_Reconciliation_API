import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from typing import Dict, Any

from app.main import app
from app.db_connection import ProjectRecord
from app.reconcile_logic import (
    generate_blocks,
    get_blocked_candidates,
    score_candidate,
    get_projects,
    clear_projects_cache,
)
from app.reconcile_norm_score import normalise_name, name_similarity, capacity_within_band
from app.extract_from_query import extract_properties

client = TestClient(app)

# -----------------------------
#  db-less testing
# -----------------------------

MOCK_PROJECTS = [
    ProjectRecord(
        id="repd-1",
        name="Aberarder Wind Farm",
        name_normalised="aberarder wind farm",
        capacity_mw=50.0,
        status="Operational",
        technology="Wind Onshore",
        country="GB",
        site_name="Aberarder Site",
        site_name_normalised="aberarder site",
        developer="SSE Renewables",
        developer_normalised="sse renewables",
    ),
    ProjectRecord(
        id="repd-2",
        name="West Moray Wind Farm",
        name_normalised="west moray wind farm",
        capacity_mw=900.0,
        status="Under Construction",
        technology="Wind Offshore",
        country="GB",
        site_name="Moray Firth",
        site_name_normalised="moray firth",
        developer="EDF Energy",
        developer_normalised="edf energy",
    ),
    ProjectRecord(
        id="repd-3",
        name="East Coast Solar Park",
        name_normalised="east coast solar park",
        capacity_mw=20.0,
        status="Operational",
        technology="Solar Photovoltaics",
        country="GB",
        site_name="East Coast Substation",
        site_name_normalised="east coast substation",
        developer="Octopus Energy",
        developer_normalised="octopus energy",
    ),
    ProjectRecord(
        id="repd-4",
        name="Moray East Offshore Wind",
        name_normalised="moray east offshore wind",
        capacity_mw=950.0,
        status="Operational",
        technology="Wind Offshore",
        country="GB",
        site_name="Moray Firth East",
        site_name_normalised="moray firth east",
        developer="EDF Energy",
        developer_normalised="edf energy",
    ),
]

@pytest.fixture
def mock_projects():
    """Fixture to mock project database"""
    with patch("app.reconcile_logic.get_projects", return_value=MOCK_PROJECTS):
        with patch("app.main.check_database_exists", return_value=True):
            yield MOCK_PROJECTS

# -----------------------------
#  manifest testing
# -----------------------------

def test_manifest_structure():
    """Test that manifest returns correct structure"""
    resp = client.get("/")
    assert resp.status_code == 200

    data = resp.json()
    assert "name" in data
    assert "identifierSpace" in data
    assert "schemaSpace" in data
    assert "defaultTypes" in data

def test_manifest_headers():
    """Test manifest response headers"""
    resp = client.get("/")
    assert resp.headers["content-type"] == "application/json; charset=utf-8"
    assert resp.headers.get("cache-control") == "no-store"

def test_manifest_post():
    """Test that manifest works with POST as well"""
    resp = client.post("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data

# -----------------------------
#  scoring testing
# -----------------------------

def test_score_candidate_weights():
    """Test that scoring weights are applied correctly"""
    query_str = "Aberarder Wind Farm"
    query_normalised = normalise_name(query_str)
    query_props: Dict[str, Any] = {}
    
    project = MOCK_PROJECTS[0]
    
    score = score_candidate(query_str, query_normalised, query_props, project)
    
    #perfect name match should give high score
    assert score >= 50.0
    assert score <= 100.0
    
    #test with mismatched name but matching site
    query_str2 = "Random Name"
    score2 = score_candidate(query_str2, normalise_name(query_str2), query_props, project)
    
    #should be much lower without name match
    assert score2 < score

def test_score_candidate_capacity_bonus():
    """Test capacity matching bonus scoring"""
    project = MOCK_PROJECTS[0] 
    query_str = "Aberarder"
    query_normalised = normalise_name(query_str)
    
    #test with exact capacity match (within 5% band) - should get +10 bonus
    query_props_exact = {"capacity_mw": 50.0}
    score_exact = score_candidate(query_str, query_normalised, query_props_exact, project)
    
    #test without capacity
    query_props_none: Dict[str, Any] = {}
    score_none = score_candidate(query_str, query_normalised, query_props_none, project)
    
    #exact match should have bonus
    assert score_exact > score_none
    
    #test with 15% band match (should get +5 bonus)
    query_props_close = {"capacity_mw": 55.0}
    score_close = score_candidate(query_str, query_normalised, query_props_close, project)
    
    #test with 25% band match (should get +2 bonus)
    query_props_far = {"capacity_mw": 60.0}
    score_far = score_candidate(query_str, query_normalised, query_props_far, project)
    
    #verify bonus hierarchy
    assert score_exact > score_close > score_far > score_none or score_exact > score_close >= score_far

def test_score_candidate_developer_matching():
    """Test that developer/customer name matching works"""
    project = MOCK_PROJECTS[0]
    query_str = "Some Project"
    query_normalised = normalise_name(query_str)
    
    #with developer match
    query_props_dev: Dict[str, Any] = {"customer_name": "SSE Renewables"}
    score_with_dev = score_candidate(query_str, query_normalised, query_props_dev, project)
    
    #without developer
    query_props_no_dev: Dict[str, Any] = {}
    score_no_dev = score_candidate(query_str, query_normalised, query_props_no_dev, project)
    
    #should have higher score with developer match
    assert score_with_dev >= score_no_dev

def test_score_candidate_technology_matching():
    """Test that technology/plant type matching works"""
    project = MOCK_PROJECTS[0]
    query_str = "Aberarder"
    query_normalised = normalise_name(query_str)
    
    #with matching technology
    query_props_tech: Dict[str, Any] = {"plant_type": "Wind Onshore"}
    score_with_tech = score_candidate(query_str, query_normalised, query_props_tech, project)
    
    #without technology
    query_props_no_tech: Dict[str, Any] = {}
    score_no_tech = score_candidate(query_str, query_normalised, query_props_no_tech, project)
    
    #should have higher score with technology match
    assert score_with_tech >= score_no_tech

# -----------------------------
#  reconciliation testing
# -----------------------------

def test_reconcile_get_q_single():
    """Test single query via GET with q parameter"""
    resp = client.get("/reconcile", params={"q": "Aberarder Wind Farm"})
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data
    assert "result" in data["q0"]
    assert len(data["q0"]["result"]) > 0
    
    #check first result
    first_result = data["q0"]["result"][0]
    assert "id" in first_result
    assert "name" in first_result
    assert "Aberarder" in first_result["name"]

def test_reconcile_get_queries_batch():
    """Test batch queries via GET"""
    queries: Dict[str, Any] = {
        "q0": {"query": "Aberarder", "limit": 3},
        "q1": {"query": "Solar", "limit": 3}
    }

    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data
    assert "q1" in data
    assert len(data["q0"]["result"]) > 0
    assert len(data["q1"]["result"]) > 0

def test_reconcile_post_form_queries():
    """Test POST with form-encoded queries"""
    with patch("app.main.check_database_exists", return_value=True):
        with patch("app.reconcile_logic.get_projects", return_value=MOCK_PROJECTS):
            queries: Dict[str, Dict[str, Any]] = {"q0": {"query": "Aberarder Wind Farm", "limit": 3}}
            resp = client.post("/reconcile", data={"queries": json.dumps(queries)})
            assert resp.status_code == 200
            assert "q0" in resp.json()

def test_reconcile_post_json_queries():
    """Test POST with JSON body containing queries"""
    payload: Dict[str, Dict[str, Any]]= {
        "queries": {
            "q0": {"query": "Aberarder", "limit": 3}
        }
    }

    resp = client.post("/reconcile", json=payload)
    assert resp.status_code == 200
    assert "q0" in resp.json()

def test_reconcile_missing_queries():
    """Test that missing queries parameter returns 422"""
    with patch("app.main.check_database_exists", return_value=True):
        resp = client.get("/reconcile")
        assert resp.status_code == 422

def test_reconcile_invalid_json():
    """Test that invalid JSON returns 422"""
    with patch("app.main.check_database_exists", return_value=True):
        resp = client.get("/reconcile", params={"queries": "not json"})
        assert resp.status_code == 422

def test_reconcile_returns_best_match():
    """Test that reconciliation returns best match first"""
    resp = client.get("/reconcile", params={"q": "Aberarder Wind Farm"})
    assert resp.status_code == 200
    
    result = resp.json()["q0"]["result"]
    assert len(result) > 0
    
    #first result should be Aberarder Wind Farm
    first = result[0]
    assert "Aberarder" in first["name"]
    assert first["score"] > 50.0
    
    #results should be sorted by score descending
    for i in range(len(result) - 1):
        assert result[i]["score"] >= result[i + 1]["score"]

def test_rconcile_empty_query():
    """Test handling of empty query string"""
    queries: Dict[str, Dict[str, Any]] = {"q0": {"query": "", "limit": 3}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})

    #should return validation error
    assert resp.status_code == 422

def test_reconcile_unicode_names():
    """Test that Unicode characters in queries are handled correctly"""
    queries: Dict[str, Dict[str, Any]] = {"q0": {"query": "Ábérárdér Wíñd Färm", "limit": 3}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200
    
    data = resp.json()
    assert "q0" in data

    #should still find results even with accented characters
    assert "result" in data["q0"]

def test_reconcile_get_query_parameter():
    """Test single query via GET with query parameter"""
    resp = client.get("/reconcile", params={"query": "Moray"})
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data
    assert len(data["q0"]["result"]) > 0

def test_reconcile_post_json_single_query():
    """Test POST with JSON body containing single query"""
    payload: Dict[str, Any] = {"query": "Moray", "limit": 5}

    resp = client.post("/reconcile", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "q0" in data

def test_reconcile_whitespace_query():
    """Test that queries with excessive whitespace are handled"""
    queries: Dict[str, Dict[str, Any]] = {"q0": {"query": "  Aberarder   Wind   Farm  ", "limit": 3}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200
    
    result = resp.json()["q0"]["result"]
    assert len(result) > 0

def test_reconcile_database_missing():
    """Test that missing database returns 503"""
    with patch("app.main.check_database_exists", return_value=False):
        resp = client.get("/reconcile", params={"q": "test"})
        assert resp.status_code == 503
        assert "Database not initialised" in resp.json()["detail"]

def test_reconcile_with_properties():
    """Test reconciliation with property constraints"""
    queries: Dict[str, Any, Dict[str, Any]] = {
        "q0": {
            "query": "Aberarder",
            "limit": 3,
            "properties": [
                {"pid": "MW Connected", "v": "50"}
            ]
        }
    }
    
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200
    
    result = resp.json()["q0"]["result"]
    assert len(result) > 0

def test_reconcile_limit_enforcement():
    """Test that limit parameter is respected"""
    queries: Dict[str, Dict[str, Any]] = {"q0": {"query": "Wind", "limit": 2}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200
    
    result = resp.json()["q0"]["result"]
    assert len(result) <= 2

def test_reconcile_very_large_limit(mock_projects):
    queries = {"q0": {"query": "Wind", "limit": 1000}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    
    #check status code
    assert resp.status_code == 422
    
    #access 'detail' key on error responses
    error_response = resp.json()
    assert "detail" in error_response
    
    detail_str = str(error_response["detail"])
    assert "limit" in detail_str.lower() or "less than or equal" in detail_str.lower()

#def test_extract_properties_missing_values():

# -----------------------------
#  response format testing
# -----------------------------

def test_response_schema():
    """Test that response follows W3C reconciliation schema"""
    resp = client.get("/reconcile", params={"q": "Wind"})
    assert resp.status_code == 200

    result = resp.json()["q0"]["result"]
    if len(result) > 0:
        candidate = result[0]
        
        #required fields
        assert "id" in candidate
        assert "name" in candidate
        assert "score" in candidate
        assert "match" in candidate
        assert "type" in candidate
        
        #type must be list
        assert isinstance(candidate["type"], list)
        
        #score must be 0-100
        assert 0 <= candidate["score"] <= 100
        
        #match must be boolean
        assert isinstance(candidate["match"], bool)
        
        #if type is present, check structure
        if len(candidate["type"]) > 0:
            type_obj = candidate["type"][0]
            assert "id" in type_obj
            assert "name" in type_obj

def test_response_headers(mock_projects):
    """Test response headers are correct"""
    resp = client.get("/reconcile", params={"q": "Wind"})
    assert resp.headers["content-type"] == "application/json; charset=utf-8"
    assert resp.headers.get("cache-control") == "no-store"


def test_response_match_flag(mock_projects):
    """Test that match flag is set correctly for high scores"""
    resp = client.get("/reconcile", params={"q": "Aberarder Wind Farm"})
    result = resp.json()["q0"]["result"]
    
    if len(result) > 0:
        first = result[0]
        #high score should set match=True
        if first["score"] >= 90.0:
            assert first["match"] is True
        else:
            assert first["match"] is False


def test_response_description_format(mock_projects):
    """Test that description field is properly formatted"""
    resp = client.get("/reconcile", params={"q": "Aberarder"})
    result = resp.json()["q0"]["result"]
    
    if len(result) > 0:
        candidate = result[0]
        if candidate.get("description"):
            #description should contain useful info
            desc = candidate["description"]
            assert isinstance(desc, str)
            assert len(desc) > 0

# -----------------------------
#  blocking testing
# -----------------------------

def test_generate_blocks():
    f"""Test block generation for indexing"""
    blocks = generate_blocks("west moray wind farm")

    assert "west" in blocks
    assert "moray" in blocks
    assert "wind" in blocks
    assert "farm" in blocks
    
    #should also have 4-char prefixes
    assert "mora" in blocks

def test_blocking_matches_developer():
    """Test that blocking can match on developer name"""
    from app.reconcile_logic import get_blocked_candidates

    blocked = get_blocked_candidates("sse", MOCK_PROJECTS, min_candidates=1)
    names = [p.name for p in blocked]

    assert "Aberarder Wind Farm" in names

def test_blocking_matches_site():
    """Test that blocking can match on site name"""
    from app.reconcile_logic import get_blocked_candidates

    blocked = get_blocked_candidates("moray firth", MOCK_PROJECTS, min_candidates=1)
    names = [p.name for p in blocked]

    assert "West Moray Wind Farm" in names

def test_generate_blocks_short_words():
    """Test that short words (< 4 chars) don't generate prefixes"""
    blocks = generate_blocks("a bb ccc dddd")
    
    assert "a" in blocks
    assert "bb" in blocks
    assert "ccc" in blocks
    assert "dddd" in blocks

def test_generate_blocks_empty():
    """Test block generation with empty string"""
    blocks = generate_blocks("")
    assert len(blocks) == 0

def test_blocking_fallback_to_prefix():
    """Test that blocking falls back to prefix matching if needed"""
    #query that won't match blocks but will match prefix
    blocked = get_blocked_candidates("xyz", MOCK_PROJECTS, min_candidates=10)
    
    #should fall back to returning all projects if no matches
    assert len(blocked) > 0

def test_blocking_returns_all_if_no_matches():
    """Test that all projects returned if blocking finds too few"""
    blocked = get_blocked_candidates("zzzzz", MOCK_PROJECTS, min_candidates=10)
    
    #should return all projects as fallback
    assert len(blocked) >= 3

# -----------------------------
#  property testing
# -----------------------------

def test_property_extraction():
    """Test property extraction from query"""

    props = [
        {"pid": "MW Connected", "v": "50.5"},
        {"pid": "Customer Name", "v": "SSE"},
        {"pid": "Plant Type", "v": "Wind Onshore"}
    ]

    extracted = extract_properties(props)

    assert extracted["capacity_mw"] == 50.5
    assert extracted["customer_name"] == "SSE"
    assert extracted["plant_type"] == "Wind Onshore"

def test_property_capacity_with_units():

    props = [{"pid": "MW Connected", "v": "50 MW"}]
    extracted = extract_properties(props)

    assert extracted["capacity_mw"] == 50.0

def test_property_capacity_with_commas():
    """Test capacity extraction with comma thousands separator"""
    props = [{"pid": "MW Connected", "v": "1,234.5"}]
    extracted = extract_properties(props)

    assert extracted["capacity_mw"] == 1234.5

def test_extract_properties_missing_values():
    """Test property extraction with missing values"""
    props = [
        {"pid": "MW Connected"},  #missing 'v'
        {"v": "50"},  #missing 'pid'
        {"pid": "Customer Name", "v": None},  #null value
    ]

    extracted = extract_properties(props)
    
    #should skip entries with missing values
    assert "capacity_mw" not in extracted
    assert "customer_name" not in extracted

def test_extract_properties_empty():
    """Test property extraction with empty list"""
    extracted = extract_properties([])
    assert extracted == {}

def test_extract_properties_none():
    """Test property extraction with None"""
    extracted = extract_properties(None)
    assert extracted == {}

def test_extract_properties_invalid_capacity():
    """Test property extraction with invalid capacity value"""
    props = [{"pid": "MW Connected", "v": "not a number"}]
    extracted = extract_properties(props)
    
    #should skip invalid capacity
    assert "capacity_mw" not in extracted

def test_extract_properties_aliases():
    """Test that property aliases work correctly"""
    props = [
        {"pid": "MW Increase / Decrease", "v": "100"},
        {"pid": "Connection Site", "v": "Site A"},
        {"pid": "Project Status", "v": "Operational"}
    ]
    
    extracted = extract_properties(props)
    
    assert extracted["capacity_mw"] == 100.0
    assert extracted["connection_site"] == "Site A"
    assert extracted["project_status"] == "Operational"

# -----------------------------
#  normalise testing
# -----------------------------

def test_normalise_name():
    """Test name normalisation"""

    assert normalise_name("Wind Farm") == "wind farm"
    assert normalise_name("  SOLAR PARK  ") == "solar park"
    assert normalise_name("O'Brien's Site") == "o brien s site"
    assert normalise_name("") == ""

def test_normalise_name_multiple_spaces():
    """Test that multiple spaces are collapsed"""
    assert normalise_name("Wind    Farm") == "wind farm"
    assert normalise_name("A  B   C    D") == "a b c d"


def test_normalise_name_special_characters():
    """Test that special characters are removed"""
    assert normalise_name("Wind@Farm!") == "wind farm"
    assert normalise_name("Solar#Park$") == "solar park"
    assert normalise_name("Site & Co.") == "site co"

def test_name_similarity():
    """Test name similarity scoring"""
    #exact match
    assert name_similarity("Wind Farm", "Wind Farm") >= 95
    
    #partial match
    assert name_similarity("Aberarder", "Aberarder Wind Farm") >= 70
    
    #different
    assert name_similarity("Wind", "Solar") < 50
    
    #case insensitive
    assert name_similarity("WIND FARM", "wind farm") >= 95

def test_name_similarity_empty():
    """Test name similarity with empty strings"""
    assert name_similarity("", "Wind Farm") == 0.0
    assert name_similarity("Wind Farm", "") == 0.0
    assert name_similarity("", "") == 0.0


def test_name_similarity_substring():
    """Test name similarity with substring matching"""
    score = name_similarity("Moray", "West Moray Wind Farm")
    assert score > 50.0

def test_capacity_within_band():
    """Test capacity band matching"""
    #within 10% band
    assert capacity_within_band(100, 105, band=0.10) is True
    assert capacity_within_band(100, 110, band=0.10) is True
    
    #outside 10% band
    assert capacity_within_band(100, 115, band=0.10) is False
    assert capacity_within_band(100, 85, band=0.10) is False
    
    #none values should return True (no constraint)
    assert capacity_within_band(None, 100) is True
    assert capacity_within_band(100, None) is True
    assert capacity_within_band(None, None) is True

def test_capacity_within_band_different_bands():
    """Test capacity matching with different band sizes"""
    #5% band
    assert capacity_within_band(100, 105, band=0.05) is True
    assert capacity_within_band(100, 106, band=0.05) is False
    
    #25% band
    assert capacity_within_band(100, 120, band=0.25) is True
    assert capacity_within_band(100, 130, band=0.25) is False

# -----------------------------
#  health testing
# -----------------------------

def test_health_with_db():
    """Test health endpoint when database is available"""
    with patch("app.main.check_database_exists", return_value=True):
        with patch("app.main.get_project_count", return_value=100):
            resp = client.get("/healthy")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

def test_health_without_db():
    """Test health endpoint when database is missing"""
    with patch("app.main.check_database_exists", return_value=False):
        resp = client.get("/healthy")
        assert resp.status_code == 503
        assert resp.json()["status"] == "db_error"

def test_health_headers():
    """Test health endpoint response headers"""
    with patch("app.main.check_database_exists", return_value=True):
        with patch("app.main.get_project_count", return_value=100):
            resp = client.get("/healthy")
            assert resp.headers.get("cache-control") == "no-store"

# -----------------------------
#  cache testing
# -----------------------------

def test_admin_reload_clears_cache():
    """Test that cache can be cleared"""
    from app.reconcile_logic import _cache, clear_projects_cache
    
    #add something to cache
    _cache["test_key"] = [MOCK_PROJECTS[0]]
    assert len(_cache) > 0
    
    #clear cache
    clear_projects_cache()
    
    #should be empty
    assert len(_cache) == 0

def test_cache_persistence():
    """Test that cache persists across multiple calls"""
    with patch("app.reconcile_logic.fetch_all_projects", return_value=MOCK_PROJECTS) as mock_fetch:
        with patch("app.reconcile_logic.check_database_exists", return_value=True):
            #clear cache first
            clear_projects_cache()
            
            #first call should fetch from DB
            from app.reconcile_logic import get_projects
            projects1 = get_projects()
            assert mock_fetch.call_count == 1
            
            #second call should use cache
            projects2 = get_projects()
            assert mock_fetch.call_count == 1  # Still 1, not 2
            
            #should return same data
            assert len(projects1) == len(projects2)

# -----------------------------
#  edge case testing
# -----------------------------

def test_reconcile_special_characters_in_query(mock_projects):
    """Test queries with special characters"""
    queries = {"q0": {"query": "Wind & Solar (UK) Ltd.", "limit": 3}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200


def test_reconcile_very_long_query(mock_projects):
    """Test with very long query string"""
    long_query = "A" * 1000
    queries = {"q0": {"query": long_query, "limit": 3}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200


def test_reconcile_numeric_query(mock_projects):
    """Test with numeric query"""
    queries = {"q0": {"query": "12345", "limit": 3}}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200


def test_reconcile_multiple_batch_queries(mock_projects):
    """Test with large batch of queries"""
    queries = {f"q{i}": {"query": "Wind", "limit": 2} for i in range(10)}
    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200
    
    data = resp.json()
    assert len(data) == 10


def test_project_without_optional_fields(mock_projects):
    """Test scoring with projects that have None for optional fields"""
    minimal_project = ProjectRecord(
        id="repd-999",
        name="Minimal Project",
        name_normalised="minimal project",
        capacity_mw=None,
        status=None,
        technology=None,
        country=None,
        site_name=None,
        site_name_normalised=None,
        developer=None,
        developer_normalised=None,
    )
    
    query_str = "Minimal"
    query_normalised = normalise_name(query_str)
    query_props: Dict[str, Any] = {}
    
    #should not crash
    score = score_candidate(query_str, query_normalised, query_props, minimal_project)
    assert score >= 0.0


def test_reconcile_single_query_result_type(mock_projects):
    """Test that result types are correctly populated"""
    resp = client.get("/reconcile", params={"q": "Aberarder"})
    result = resp.json()["q0"]["result"]
    
    if len(result) > 0:
        candidate = result[0]
        assert len(candidate["type"]) > 0
        
        type_obj = candidate["type"][0]
        assert type_obj["id"].startswith("/")
        assert len(type_obj["name"]) > 0
