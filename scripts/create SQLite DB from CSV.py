import sqlite3
from typing import Dict, Optional
from datetime import datetime, timezone
from pathlib import Path
import csv

# -----------------------------
#  column-map
# -----------------------------

REPD_GROUPS = {

    "site": {
        "fields": [
            "Address",
            "Y-coordinate",
            "X-coordinate",
            "Ref ID",
            "Local Authority",
            "Postcode",
            "Country",
        ],
        "handler": get_or_create_site
    },

    "developer": {
        "fields": [
            "Operator (or Applicant)",
        ],
        "handler": get_or_create_developer
    },

    "technology": {
        "fields": [
            "Technology Type",
        ],
        "handler": get_or_create_technology
    },

    "project": {
        "fields": [
            "Site Name",
            "Development Status",
            "Installed Capacity (MWelec)",
        ],
        "handler": create_project_row
    },

    "planning": {
        "fields": [
            "Planning Application Reference",
            "Planning Authority",
            "Planning Application Submitted",
            "Planning Application Withdrawn",
            "Planning Permission Refused",
            "Appeal Lodged",
            "Appeal Withdrawn",
            "Appeal Refused",
            "Appeal Granted",
            "Planning Permission Granted",
            "Planning Permission Expired",
            "Under Construction",
            "Operational",
        ],
        "handler": create_planning_row
    }
}

REPD_PIPELINE = [
    "site",
    "developer",
    "technology",
    "project",
    "planning"
]

# -----------------------------
#  schema
# -----------------------------

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

# -----------------------------
#  helpers
# -----------------------------

def normalise_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value.lower() if value else None

def get_field(row: Dict[str, str], logical_name: str) -> Optional[str]:
    header = REPD_COLUMN_MAP.get(logical_name)
    if not header:
        return None
    value = row.get(header, "")
    value = value.strip()
    return value or None

def parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value.replace(",", ""))
    except Exception:
        return None
    
def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# -----------------------------
#  get-or-create
# -----------------------------

def get_or_create_developer(conn: sqlite3.Connection,
                            legal_name: Optional[str]) -> Optional[int]:
    if not legal_name:
        return None
    name_norm = normalise_name(legal_name)

    cur = conn.execute(
        "SELECT company_id FROM company WHERE name_normalised = ?",
        (name_norm,)
    )
    row = cur.fetchone()
    if row:
        return row [0]
    
    cur = conn.execute(
        """
        INSERT INTO company (legal_name, name_normalised, company_type)
        VALUES (?, ?, ?)
        """,
        (legal_name.strip(), name_norm)
    )
    return cur.lastrowid

def get_or_create_site(conn: sqlite3.Connection, row, site_context) -> Optional[Dict[str, int]]:
    if not site_name:
        return None
    
    name_norm = normalise_name(site_name)

    if postcode:
        cur = conn.execute(
            """
            SELECT site_id FROM site
            WHERE name_normalised = ? AND postcode = ?
            """,
            (name_norm, postcode)
        )
    else:
        cur = conn.execute(
            """
            SELECT site_id FROM site
            WHERE name_normalised = ?
            """,
            (name_norm,)
        )
    
    row = cur.fetchone()

    if row:
        return row[0]
    
    cur = conn.execute(
        """
        INSERT INTO site (
            site_name, name_normalised, latitude, longitude,
            grid_ref, la_authority, postcode, country_code
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            site_name.strip(),
            name_norm,
            latitude,
            longitude,
            grid_ref,
            la_authority,
            postcode,
            country_code or DEFAULT_COUNTRY
        )
    )

    return ("site_id": cur.lastrowid}

def get_or_create_technology(conn: sqlite3.Connection,
                             tech_text: Optional[str]) -> Optional[int]:
    if not tech_text:
        return None
    
    tech_text_clean = tech_text.strip()

    cur = conn.execute(
        """
        SELECT technology_id FROM technology
        WHERE tech_name = ?
        """,
        (tech_text_clean)
    )

    row = cur.fetchone()
    if row:
        return row[0]
    
    cur = conn.execute(
        """
        INSERT INTO technology (tech_name)
        VALUES (?, ?)
        """,
        (tech_text_clean)
    )

    return cur.lastrowid

# -----------------------------
#  row load logic
# -----------------------------

def insert_to_db(conn: sqlite3.Connection,
                 row: Dict[str, str]) -> None:
    
    site_context = {}
    developer_context = {}
    technology_context = {}
    project_context = {}

    DEFAULT_COUNTRY = "GB"

# -----------------------------
#  entry point
# -----------------------------
def load_repd(csv_path: Path, db_path: Path, recreate: bool = False) -> None:
    if recreate and db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.executescript(SCHEMA_SQL)

    with csv_path.open("r", eoncoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows_processed = 0
        with conn:
            for row in reader:
                #process
                rows_processed += 1

