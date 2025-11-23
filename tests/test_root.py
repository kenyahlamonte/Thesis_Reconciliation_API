import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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