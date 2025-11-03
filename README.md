# Thesis_Reconciliation_API
The final project for my UoL degree is a reconiliation API, built to return searches on the database using OpenRefine 

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
uvicorn app.main:app --reload
```

### ---------------
## Powershell vs. Linux
### ---------------

Powershell users use run.ps1, Linux users run make