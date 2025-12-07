import sqlite3
from typing import Dict

REPD_COLUMN_MAP: Dict[str, str] = {
    "project_name": "Site Name",
    "status": "Development Status",
    "technology": "Technology Type",
    "capacity_mw": "Installed Capacity (MWelec)",

    "site_name": "Address",
    "latitude": "Y-coordinate",
    "longitude": "X-coordinate",
    "la_authority": "Local Authority",
    "postcode": "Postcode",
    "country": "Country",

    "developer": "Operator (or Applicant)",

    "planning_reference": "Planning Application Reference",
    "planning_authority": "Planning Authority",
    "planning_application_submitted": "Planning Application Submitted",
    "planning_application_withdrawn": "Planning Application Withdrawn",
    "planning_application_refused": "Planning Permission Refused",
    "planning_appeal_lodged": "Appeal Lodged",
    "planning_appeal_withdrawn": "Appeal Withdrawn",
    "planning_appeal_refused": "Appeal Refused",
    "planning_appeal_granted": "Appeal Granted",
    "planning_application_granted": "Planning Permission Granted",
    "planning_permission_expired": "Planning Permission Expired",
    "site_under_construction": "Under Construction",
    "site_operational": "Operational",

    "repd_id": "Ref ID",
    "old_id": "Old Ref ID",
    "new_id": "Are they re-applying (New REPD Ref)",
}

DEFAULT_COUNTRY = "GB"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS project (
    project_id     INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    name_normalised TEXT NOT NULL,
    status         TEXT,
    technology_id  INTEGER,
    site_id        INTEGER,
    lead_company   INTEGER,
    country        TEXT,
    created_at     TEXT,
    updated_at     TEXT,
    FOREIGN KEY (technology_id) REFERENCES technology(technology_id),
    FOREIGN KEY (site_id)       REFERENCES site(site_id),
    FOREIGN KEY (lead_company)  REFERENCES company(company_id)
);

CREATE TABLE IF NOT EXISTS site (
    site_id         INTEGER PRIMARY KEY,
    site_name       TEXT NOT NULL,
    name_normalised TEXT NOT NULL,
    latitude        REAL,
    longitude       REAL,
    grid_ref        TEXT,
    la_authority    TEXT,
    postcode        TEXT,
    country         TEXT
);

CREATE TABLE IF NOT EXISTS company (
    company_id      INTEGER PRIMARY KEY,
    legal_name      TEXT NOT NULL,
    name_normalised TEXT NOT NULL,
);

CREATE TABLE IF NOT EXISTS technology (
    technology_id INTEGER PRIMARY KEY,
    tech_name     TEXT
);

CREATE TABLE IF NOT EXISTS capacity_block (
    capacity_id  INTEGER PRIMARY KEY,
    project_id   INTEGER,
    capacity_mw  REAL NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE IF NOT EXISTS planning_consent (
    consent_id    INTEGER PRIMARY KEY,
    project_id    INTEGER,
    stage         TEXT,
    decision_date TEXT,
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE IF NOT EXISTS reconcile_query (
    rq_id      INTEGER PRIMARY KEY,
    raw_query  TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS reconcile_candidate (
    rc_id           INTEGER PRIMARY KEY,
    rq_id           INTEGER,
    project_id      INTEGER,
    score           REAL,
    is_exact        INTEGER,
    feature_vectore TEXT,
    rationale       TEXT,
    FOREIGN KEY (rq_id)      REFERENCES reconcile_query(rq_id),
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE IF NOT EXISTS reconcile_match (
    rm_id         INTEGER PRIMARY KEY,
    rq_id         INTEGER,
    project_id    INTEGER,
    decided_match INTEGER,
    decided_by    TEXT,
    decided_at    TEXT,
    FOREIGN KEY (rq_id)      REFERENCES reconcile_query(rq_id),
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE INDEX IF NOT EXISTS idx_project_name_norm
    ON project(name_normalised);

CREATE INDEX IF NOT EXISTS idx_site_name_norm
    ON site(name_normalised);

CREATE INDEX IF NOT EXISTS idx_company_name_norm
    ON company(name_normalised);

CREATE INDEX IF NOT EXISTS idx_external_id_system_value
    ON external_id(system, value);

CREATE INDEX IF NOT EXISTS idx_capacity_project
    ON capacity_block(project_id);

CREATE INDEX IF NOT EXISTS idx_grid_project
    ON grid_connection(project_id);

CREATE INDEX IF NOT EXISTS idx_planning_project
    ON planning_consent(project_id);
"""