import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from typing import Dict, Any

from app.main import app
from app.db_connection import ProjectRecord
from app.reconcile_logic import (
    generate_blocks,
    score_candidate,
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
    with patch("app.reconcile_logic._projects_cache", MOCK_PROJECTS):
        with patch("app.main.check_databased_exists", return_value=True):
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

#need to test post

# -----------------------------
#  scoring testing
# -----------------------------

def test_score_candidate_weights():
    """Test that scoring weights are applied correctly"""
    query_str = "Aberarder Wind Farm"
    query_normalised = normalise_name(query_str)
    query_props: Dict[str, Any] = {}
    
    project = MOCK_PROJECTS[0]  # Aberarder Wind Farm
    
    score = score_candidate(query_str, query_normalised, query_props, project)
    
    # Perfect name match should give high score
    assert score >= 50.0
    assert score <= 100.0
    
    # Test with mismatched name but matching site
    query_str2 = "Random Name"
    score2 = score_candidate(query_str2, normalise_name(query_str2), query_props, project)
    
    # Should be much lower without name match
    assert score2 < score

def test_score_candidate_capacity_bonus():
    """Test capacity matching bonus scoring"""
    project = MOCK_PROJECTS[0]  # 50.0 MW
    query_str = "Aberarder"
    query_normalised = normalise_name(query_str)
    
    # Test with exact capacity match (within 5% band) - should get +10 bonus
    query_props_exact = {"capacity_mw": 50.0}
    score_exact = score_candidate(query_str, query_normalised, query_props_exact, project)
    
    # Test without capacity
    query_props_none: Dict[str, Any] = {}
    score_none = score_candidate(query_str, query_normalised, query_props_none, project)
    
    # Exact match should have bonus
    assert score_exact > score_none
    
    # Test with 15% band match (should get +5 bonus)
    query_props_close = {"capacity_mw": 55.0}
    score_close = score_candidate(query_str, query_normalised, query_props_close, project)
    
    # Test with 25% band match (should get +2 bonus)
    query_props_far = {"capacity_mw": 60.0}
    score_far = score_candidate(query_str, query_normalised, query_props_far, project)
    
    # Verify bonus hierarchy
    assert score_exact > score_close > score_far > score_none or score_exact > score_close >= score_far

#need to test dev matching and tech matching

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

# -----------------------------
#  normalise testing
# -----------------------------

def test_normalise_name():
    """Test name normalisation"""

    assert normalise_name("Wind Farm") == "wind farm"
    assert normalise_name("  SOLAR PARK  ") == "solar park"
    assert normalise_name("O'Brien's Site") == "o brien s site"
    assert normalise_name("") == ""

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
