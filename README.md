# UK Renewable Energy Reconciliation API

A lightweight reconciliation service implementing the **OpenRefine Reconciliation API (v0.2)** for matching NESO TEC client-side data against the **Renewable Energy Planning Database (REPD)**.

The `/reconcile` endpoint accepts GET and POST inputs and returns results in an OpenRefine-compatible structure.


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

### bash
```bash
python -m venv .venv
```
### windows
```
. .venv/Scripts/activate
```

### macOS/linux
```
source .venv/bin/activate
```

### dependencies 
```
pip install -r requirements.txt
```

### server
```
uvicorn app.main:app --reload --port 8001
```

The API will be available at: http://localhost:8001

### ---------------
## Powershell vs. Linux
### ---------------

Powershell users use run.ps1, Linux users run make

### ---------------
## API Reference
### ---------------

### GET - Single Query
```
curl "http://localhost:8001/reconcile?q=Aberarder%20Wind%20Farm"
```
### GET - Batch Query
```
curl "http://localhost:8001/reconcile?queries={"q0": {"query": "Aberarder Wind Farm", "limit": 3},"q1": {"query": "Another Site", "limit": 3}}"
```
### POST - Form Request
```
curl -X POST http://localhost:8001/reconcile \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'queries={"q0": {"query": "Aberarder Wind Farm", "limit": 3}}'
```
### POST - JSON Request
```
curl -X POST http://localhost:8001/reconcile \
  -H "Content-Type: application/json" \
  -d '{
        "queries": {
          "q0": { "query": "Aberarder Wind Farm", "limit": 3 }
        }
      }'
```
### healthy
```
curl http://localhost:8001/healthy
```