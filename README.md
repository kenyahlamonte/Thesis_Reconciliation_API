# Thesis_Reconciliation_API
The final project for my UoL degree is a reconiliation API, built to return searches on the database using OpenRefine 

## Quickstart

# bash
python -m venv .venv
# windows
. .venv/Scripts/activate
# macOS/linux
source .venv/bin/activate

# dependencies 
pip install -r requirements.txt

# server
uvicorn app.main:app --reload