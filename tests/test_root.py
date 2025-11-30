import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

#tests 23/11/25
#test GET with a single query
def test_reconcile_get_q_single():
    resp = client.get("/reconcile", params={"q": "Aberarder Wind Farm"})
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data
    
    result = data["q0"]["result"]
    assert isinstance(result, list)
    assert result[0]["name"] == "Aberarder Wind Farm"
    assert result[0]["id"] == "repd001"

#test GET with batch queries
def test_reconcile_get_queries_batch():
    queries = {
        "q0": {"query": "Aberarder Wind Farm", "limit": 3},
        "q1": {"query": "Another Site", "limit": 3}
    }

    resp = client.get(
        "/reconcile",
        params={"queries": json.dumps(queries)}
    )
    assert resp.status_code == 200

    data = resp.json()
    assert set(data.keys()) == {"q0", "q1"}

    for key, q in queries.items():
        result = data[key]["result"]
        assert result[0]["name"] == q["query"]
        assert result[0]["id"] == "repd001"

#test POST form (OpenRefine)
def test_reconcile_post_form_queries():
    queries = {
        "q0": {"query": "Aberarder Wind Farm", "limit":3}
    }

    resp = client.post(
        "/reconcile",
        data={"queries": json.dumps(queries)},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data

    result = data["q0"]["result"]
    assert result[0]["name"] == "Aberarder Wind Farm"

#test POST with JSON body
def test_reconcile_post_json_queries():
    payload = {
        "queries": {
            "q0": {"query": "Aberarder Wind Farm", "limit": 3}
        }
    }

    resp = client.post("/reconcile", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "q0" in data

    result = data["q0"]["result"]
    assert result[0]["name"] == "Aberarder Wind Farm"

#test 422 error
def test_reconcile_missing_queries():
    resp = client.get("/reconcile")
    assert resp.status_code == 422

    data = resp.json()
    assert "detail" in data
    assert "Provide ?queries" in data["detail"]

#tests 29/11/
#test headers and encoding
def test_reconcile_headers_and_encoding():
    resp = client.get("/reconcile", params={"q": "Aberarder Wind Farm"})
    assert resp.status_code == 200

    assert resp.headers["content-type"] == "application/json; charset=utf-8"

    assert resp.headers.get("cache-control") == "no-store"

    assert resp.encoding.lower() == "utf-8"

#test shape of response
def test_reconcile_response_schema_single():
    resp = client.get("/reconcile", params={"q": "Aberarder Wind Farm"})
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, dict)
    assert "q0" in data
    assert "result" in data["q0"]

    results = data["q0"]["result"]
    assert isinstance(results, list)
    assert len(results) >= 1

    candidate = results[0]
    expected_keys = {"id", "name", "location", "type", "score", "match"}
    assert expected_keys.issubset(candidate.keys())

    assert isinstance(candidate["id"], str)
    assert isinstance(candidate["name"], str)
    assert isinstance(candidate["score"], float)
    assert isinstance(candidate["match"], bool)

#test non-reconcile headers
def test_manifest_headers_and_encoding():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json; charset=utf-8"
    assert resp.headers.get("cache-control") == "no-store"
    assert resp.encoding.lower() == "utf-8"

def test_health_headers_and_encoding():
    resp = client.get("/healthy")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json; charset=utf-8"
    assert resp.headers.get("cache-control") == "no-store"
    assert resp.encoding.lower() == "utf-8"

