import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from typing import Dict, Any

from app.main import app
from app.db_connection import ProjectRecord

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
]

@pytest.fixture
def mock_projects():
    with patch("app.reconcile_logic._projects_cache", MOCK_PROJECTS):
        with patch("app.db_connection.check_databased_exists", return_value=True):
            yield MOCK_PROJECTS

# -----------------------------
#  manifest testing
# -----------------------------

def test_manifest_structure():
    resp = client.get("/")
    assert resp.status_code == 200

    data = resp.json()
    assert "name" in data
    assert "identifierSpace" in data
    assert "schemaSpace" in data
    assert "defaultTypes" in data

def test_manifest_headers():
    resp = client.get("/")
    assert resp.headers["content-type"] == "application/json; charset=uft-8"
    assert resp.headers.get("cache-control") == "no-store"

# -----------------------------
#  reconciliation testing
# -----------------------------

def test_reconcile_get_q_single():
    resp = client.get("/reconcile", params={"q": "Aberarder Wind Farm"})
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data
    assert len(data["q0"]["result"]) > 0

def test_reconcile_get_queries_batch():
    queries: Dict[str, Any] = {
        "q0": {"query": "Aberarder", "limit": 3},
        "q1": {"query": "Solar", "limit": 3}
    }

    resp = client.get("/reconcile", params={"queries": json.dumps(queries)})
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data
    assert "q1" in data

def test_reconcile_post_form_queries():
    queries: Dict[str, Any]= {"q0": {"query": "Aberarder Wind Farm", "limit":3}}

    resp = client.post("/reconcile", data={"queries": json.dumps(queries)})
    assert resp.status_code == 200
    assert "q0" in resp.json()

def test_reconcile_post_json_queries():
    payload: Dict[str, Dict[str, Any]]= {
        "queries": {
            "q0": {"query": "Aberarder", "limit": 3}
        }
    }

    resp = client.post("/reconcile", json=payload)
    assert resp.status_code == 200
    assert "q0" in resp.json()

def test_reconcile_missing_queries():
    with patch("app.db_connection.check_database_exists", return_value=True):
        resp = client.get("/reconcile")
        assert resp.status_code == 422

def test_reconcile_invalid_json():
    with patch("app.db_connection.check_database_exists", return_value=True):
        resp = client.get("/reconcile", params={"queries": "not json"})
        assert resp.status_code == 422

# -----------------------------
#  response format testing
# -----------------------------

def test_response_schema():
    resp = client.get("/reconcile", params={"q": "Wind"})
    assert resp.status_code == 200

    result = resp.json()["q0"]["result"]
    if len(result) > 0:
        candidate = result[0]
        assert "id" in candidate
        assert "name" in candidate
        assert "score" in candidate
        assert "match" in candidate
        assert "type" in candidate
        assert isinstance(candidate["type"], list)

# -----------------------------
#  blocking testing
# -----------------------------

def test_generate_blocks():
    from app.reconcile_logic import generate_blocks

    blocks = generate_blocks("west moray wind farm")

    assert "west" in blocks
    assert "moray" in blocks
    assert "mora" in blocks

def test_blocking_matches_developer():
    from app.reconcile_logic import get_blocked_candidates

    blocked = get_blocked_candidates("sse", MOCK_PROJECTS, min_candidates=1)
    names = [p.name for p in blocked]

    assert "Aberarder Wind Farm" in names

def test_blocking_matches_site():
    from app.reconcile_logic import get_blocked_candidates

    blocked = get_blocked_candidates("moray firth", MOCK_PROJECTS, min_candidates=1)
    names = [p.name for p in blocked]

    assert "West Moray Wind Farm" in names

# -----------------------------
#  property testing
# -----------------------------

def test_property_extraction():
    from app.reconcile_logic import extract_properties

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
    from app.reconcile_logic import extract_properties

    props = [{"pid": "MW Connected", "v": "50 MW"}]
    extracted = extract_properties(props)

    assert extracted["capacity_mw"] == 50.0

# -----------------------------
#  normalise testing
# -----------------------------

def test_normalise_name():
    from app.reconcile_norm_score import normalise_name

    assert normalise_name("Wind Farm") == "wind farm"
    assert normalise_name("  SOLAR PARK  ") == "solar park"
    assert normalise_name("O'Brien's Site") == "o brien s site"
    assert normalise_name("") == ""

def test_name_similarity():
    from app.reconcile_norm_score import name_similarity

    assert name_similarity("Wind Farm", "Wind Farm") >= 95
    assert name_similarity("Aberarder", "Aberarder Wind Farm") >= 70
    assert name_similarity("Wind", "Solar") < 50

def test_capacity_within_band():
    from app.reconcile_norm_score import capacity_within_band

    assert capacity_within_band(100, 105, band=0.10) is True
    assert capacity_within_band(100, 115, band=0.10) is False
    assert capacity_within_band(None, 100) is True

# -----------------------------
#  health testing
# -----------------------------

def test_health_with_db():
    with patch("app.db_connection.check_database_exists", return_value=True):
        with patch("app.db_connection.get_project_count", return_value=100):
            resp = client.get("/healthy")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

def test_health_without_db():
    with patch("app.db_connection.check_database_exists", return_value=True):
        with patch("app.db_connection.get_project_count", return_value=100):
            resp = client.get("/healthy")
            assert resp.status_code == 503
            assert resp.json()["status"] == "db error"