# UK Renewable Energy Reconciliation API

A lightweight reconciliation service implementing the **OpenRefine Reconciliation API (v0.2)** for matching NESO TEC client-side data against the **Renewable Energy Planning Database (REPD)**.

### ---------------
### Datasets & licences
### ---------------
- **REPD** — Renewable Energy Planning Database (UK). Used for project pipeline info. Licencing is © Crown copyright. Licensed under the Open Government Licence v3.0.
Use and re-use the Information that is available under this licence, freely and flexibly, with only a few conditions. (public) 
https://www.neso.energy/data-portal/transmission-entry-capacity-tec-register

- **NESO TEC Register** — Transmission Entry Capacity register (UK). Licence: National Energy SO Open Data Licence v1.0.
Notes: Data used only for academic prototype; attribution maintained; no redistribution of bulk raw where restricted.
https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract

### ---------------
## Quickstart
### ---------------

```bash
#install dependencies
pip install -e ".[dev]"

#run the service
uvicorn app.main:app --reload --port 8001

#verify it's running
curl http://localhost:8001/healthy
```

The service runs at `http://localhost:8001`.

---

### ---------------
## End points
### ---------------

### GET/POST `/` — Service Manifest

Returns service metadata. OpenRefine calls this to discover the service.

**Response:**
```json
{
  "name": "REPD x NESO TEC Reconciliation",
  "identifierSpace": "https://example.org/renewables/id",
  "schemaSpace": "https://example.org/renewables/schema",
  "defaultTypes": [
    {"id": "/renewable", "name": "Renewable Facility"}
  ]
}
```

---

### GET/POST `/reconcile` — Reconciliation

Match project names against the REPD database.

#### Query Parameters

| Parameter | Description |
|-----------|-------------|
| `q` | Single query string |
| `query` | Alternative to `q` |
| `queries` | JSON object of batch queries |

#### Single Query

```bash
curl "http://localhost:8001/reconcile?q=Moray%20Wind%20Farm"
```

#### Batch Queries

```bash
curl -X POST http://localhost:8001/reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "queries": {
      "q0": {"query": "Aberarder Wind Farm", "limit": 5},
      "q1": {"query": "Moray Offshore", "limit": 3}
    }
  }'
```

#### Form-Encoded (OpenRefine style)

```bash
curl -X POST http://localhost:8001/reconcile \
  -d 'queries={"q0":{"query":"Aberarder","limit":3}}'
```

#### Query Object Schema

```json
{
  "query": "Aberarder Wind Farm",
  "limit": 5,
  "type": "/renewable",
  "properties": [
    {"pid": "MW Connected", "v": "50"},
    {"pid": "Customer Name", "v": "SSE Renewables"},
    {"pid": "Plant Type", "v": "Wind Onshore"}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Text to match |
| `limit` | int | No | Max results (default: 3, max: 100) |
| `type` | string | No | Type filter |
| `properties` | array | No | Property constraints |

#### Supported Properties

| Property ID | Maps to | Example |
|-------------|---------|---------|
| `MW Connected` | Capacity | `"50"` |
| `MW Increase / Decrease` | Capacity | `"100"` |
| `Customer Name` | Developer | `"SSE Renewables"` |
| `Connection Site` | Site | `"Moray Firth"` |
| `Plant Type` | Technology | `"Wind Onshore"` |

#### Response

```json
{
  "q0": {
    "result": [
      {
        "id": "repd-1234",
        "name": "Aberarder Wind Farm",
        "score": 95.5,
        "match": true,
        "type": [
          {"id": "/technology/wind_onshore", "name": "Wind Onshore"}
        ],
        "description": "Wind Onshore | 50.0 MW | Operational | Developer: SSE Renewables"
      }
    ]
  }
}
```

| Field | Description |
|-------|-------------|
| `id` | REPD project ID (prefixed with `repd-`) |
| `name` | Project name |
| `score` | Confidence score (0–100) |
| `match` | `true` if score ≥ 90 |
| `type` | Technology type |
| `description` | Summary of project details |

---

### GET `/healthy` — Health Check

```bash
curl http://localhost:8001/healthy
```

**Response (200):**
```json
{
  "status": "ok",
  "database": "connected",
  "project_count": 4521
}
```

**Response (503):**
```json
{
  "status": "db_error",
  "database": "missing",
  "project_count": 0
}
```

---

### ---------------
## Connecting to OpenRefine
### ---------------

1. Start the reconciliation service:
   ```bash
   uvicorn app.main:app --port 8001
   ```

2. In OpenRefine, select a column containing project names

3. Click the column dropdown → **Reconcile** → **Start reconciling...**

4. Click **Add Standard Service**

5. Enter the service URL:
   ```
   http://localhost:8001/reconcile
   ```

6. Click **Add Service**

7. Select "Renewable Facility" as the type (or leave blank)

8. Optionally add property mappings:
   - Map your capacity column to `MW Connected`
   - Map your developer column to `Customer Name`

9. Click **Start Reconciling**

---

### ---------------
## Scoring Algorithm
### ---------------

Candidates are scored using weighted fuzzy matching:

| Component | Weight | Description |
|-----------|--------|-------------|
| Name | 50% | Fuzzy match against project name |
| Site | 20% | Fuzzy match against site name |
| Developer | 15% | Fuzzy match against developer |
| Technology | 5% | Fuzzy match against plant type |

**Capacity bonuses** (if provided):
- Within 5%: +10 points
- Within 15%: +5 points
- Within 25%: +2 points

Scores are capped at 100. A score ≥ 90 sets `match: true`.

---

### ---------------
## Limitations
### ---------------

- **Local database only** — Requires the REPD SQLite database at `data/raw/<database.db>`
- **No persistent entity IDs** — IDs are based on REPD project IDs and may change between database versions
- **English names only** — Optimised for UK project names; no internationalisation
- **No extend/suggest endpoints** — Only core reconciliation is implemented (W3C spec allows these as optional)
- **Single-threaded** — Not optimised for high concurrency
- **Fuzzy matching limits** — Very short queries (< 3 characters) may return poor results
- **No authentication** — Designed for local/thesis use only

---

### ---------------
## Examples
### ---------------

### Python

```python
import requests

response = requests.get(
    "http://localhost:8001/reconcile",
    params={"q": "Moray Wind Farm"}
)
results = response.json()["q0"]["result"]

for r in results:
    print(f"{r['name']} (score: {r['score']})")
```

### JavaScript

```javascript
const response = await fetch(
  "http://localhost:8001/reconcile?q=Moray%20Wind%20Farm"
);
const data = await response.json();
console.log(data.q0.result);
```

### Batch with Properties

```python
import requests
import json

queries = {
    "q0": {
        "query": "Aberarder",
        "limit": 5,
        "properties": [
            {"pid": "MW Connected", "v": "50"},
            {"pid": "Plant Type", "v": "Wind Onshore"}
        ]
    }
}

response = requests.post(
    "http://localhost:8001/reconcile",
    data={"queries": json.dumps(queries)}
)
print(response.json())
```

---

### ---------------
## Development
### ---------------

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Lint
ruff check .

# Run with auto-reload
uvicorn app.main:app --reload
```

---

### ---------------
## API Reference
### ---------------

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/` | Service manifest |
| GET/POST | `/reconcile` | Reconciliation queries |
| GET | `/healthy` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc documentation |
