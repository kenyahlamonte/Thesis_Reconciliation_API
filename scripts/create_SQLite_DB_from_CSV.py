import sqlite3
from typing import TypedDict, Dict, Optional, Mapping, Callable
from datetime import datetime, timezone
from pathlib import Path
from argparse import ArgumentParser
import csv

# -----------------------------
#  grouping helpers
# -----------------------------

CSVRow = Mapping[str, str]

Context = Dict[str, int]

GroupHandler = Callable[
    [sqlite3.Connection, CSVRow, Context],
    Optional[Dict[str, int]]
]

class REPDGroup(TypedDict):
    fields: Dict[str, str]
    handler: GroupHandler

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
    capacity_mw    REAL,
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
    name_normalised TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS technology (
    technology_id INTEGER PRIMARY KEY,
    tech_name     TEXT
);

CREATE TABLE IF NOT EXISTS planning_consent (
    consent_id    INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_planning_project
    ON planning_consent(project_id);
"""

# -----------------------------
#  data processing helpers
# -----------------------------

def normalise_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value.lower() if value else None

def get_field(row: Mapping[str, str], logical_name: str) -> Optional[str]:
    header = REPD_FIELD_MAP.get(logical_name)
    if header is None:
        return None
    
    raw = row.get(header)
    if not isinstance(raw, str):
        return None
    
    value = raw.strip()
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
                            row: CSVRow, 
                            context: Context) -> Optional[Dict[str, int]]:
    legal_name = get_field(row, "Operator (or Applicant)")

    if not legal_name:
        return None
    
    name_norm = normalise_name(legal_name)

    cur = conn.execute(
        "SELECT company_id FROM company WHERE name_normalised = ?",
        (name_norm,)
    )
    row_id = cur.fetchone()
    if row_id is not None:
        return {"developer_id": row_id[0]}
    
    cur = conn.execute(
        """
        INSERT INTO company (legal_name, name_normalised)
        VALUES (?, ?)
        RETURNING company_id
        """,
        (legal_name.strip(), name_norm)
    )

    row_id = cur.fetchone()
    if row_id is not None:
        return {"developer_id": row_id[0]}
    
    return None

def get_or_create_site(conn: sqlite3.Connection, 
                       row: CSVRow, 
                       context: Context) -> Optional[Dict[str, int]]:
    site_name = get_field(row, "Address")
    if not site_name:
        return None
    
    name_norm = normalise_name(site_name)

    postcode = get_field(row, "Postcode")
    if postcode:
        cur = conn.execute(
            """
            SELECT site_id FROM site
            WHERE name_normalised = ? AND postcode = ?
            """,
            (name_norm, postcode,)
        )
    else:
        cur = conn.execute(
            """
            SELECT site_id FROM site
            WHERE name_normalised = ?
            """,
            (name_norm,)
        )
    
    row_id = cur.fetchone()
    if row_id is not None:
        return {"site_id": row_id[0]}
    
    cur = conn.execute(
        """
        INSERT INTO site (
            site_name, name_normalised, latitude, longitude,
            grid_ref, la_authority, postcode, country
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING site_id
        """,
        (
            site_name.strip(),
            name_norm,
            get_field(row, "Y-coordinate"),
            get_field(row, "X-coordinate"),
            get_field(row, "Ref ID"),
            get_field(row, "Local Authority"),
            postcode,
            get_field(row, "Country") or DEFAULT_COUNTRY,
        )
    )

    row_id = cur.fetchone()
    if row_id is not None:
        return {"site_id": row_id[0]}
    
    return None

def get_or_create_technology(conn: sqlite3.Connection, 
                             row: CSVRow, 
                             context: Context) -> Optional[Dict[str, int]]:
    tech_text = get_field(row, "Technology Type")
    if not tech_text:
        return None
    
    tech_text_clean = tech_text.strip()

    cur = conn.execute(
        """
        SELECT technology_id FROM technology
        WHERE tech_name = ?
        """,
        (tech_text_clean,)
    )

    row_id = cur.fetchone()
    if row_id is not None:
        return {"technology_id": row_id[0]}
    
    cur = conn.execute(
        """
        INSERT INTO technology (tech_name)
        VALUES (?)
        RETURNING technology_id
        """,
        (tech_text_clean,)
    )

    row_id = cur.fetchone()
    if row_id is not None:
        return {"technology_id": row_id[0]}
    
    return None

def create_project_row(conn: sqlite3.Connection, 
                        row: CSVRow, 
                        context: Context) -> Optional[Dict[str, int]]:
    project_name = get_field(row, "Site Name")
    if not project_name:
        return None
    
    project_name_norm = normalise_name(project_name)

    cur = conn.execute(
        """
        SELECT project_id FROM project
        WHERE name_normalised = ?
        """,
        (project_name_norm,)
    )

    row_id = cur.fetchone()
    if row_id is not None:
        return{"project_id": row_id[0]}
    
    cur = conn.execute(
        """
        INSERT INTO project (
            canonical_name,
            name_normalised,
            status,
            capacity_mw,
            technology_id,
            site_id,
            lead_company,
            country,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING project_id
        """,
        (project_name,
         project_name_norm,
         get_field(row, "Development Status"),
         parse_float(get_field(row, "Installed Capacity (MWelec)")),
         context.get("technology_id"),
         context.get("site_id"),
         context.get("developer_id"),
         DEFAULT_COUNTRY,
         current_timestamp(),
         current_timestamp(),
        ),
    )

    row_id = cur.fetchone()
    if row_id is not None:
        return{"project_id": row_id[0]}

    return None

def create_planning_row(conn: sqlite3.Connection, 
                        row: CSVRow, 
                        context: Context) -> None:
    project_id = context.get("project_id")
    if project_id is None:
        return None
    
    stage_fields = [
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
    ]

    for stage in stage_fields:
        decision_date = get_field(row, stage)
        if decision_date:
            conn.execute(
                """
                INSERT INTO planning_consent (project_id, stage, decision_date)
                VALUES (?, ?, ?)
                """,
                (project_id, stage, decision_date)
            )

    return None

# -----------------------------
#  handle grouping
# -----------------------------

REPD_GROUPS: Dict[str, REPDGroup] = {

    "site": {
        "fields": {
            "Address": "Address",
            "Y-coordinate": "Y-coordinate",
            "X-coordinate": "X-coordinate",
            "Ref ID": "Ref ID",
            "Local Authority": "Local Authority",
            "Postcode": "Postcode",
            "Country": "Country",
        },
        "handler": get_or_create_site,
    },

    "developer": {
        "fields": {
            "Operator (or Applicant)": "Operator (or Applicant)",
        },
        "handler": get_or_create_developer,
    },

    "technology": {
        "fields": {
            "Technology Type": "Technology Type",
        },
        "handler": get_or_create_technology,
    },

    "project": {
        "fields": {
            "Site Name": "Site Name",
            "Development Status": "Development Status",
            "Installed Capacity (MWelec)": "Installed Capacity (MWelec)",
        },
        "handler": create_project_row,
    },

    "planning": {
        "fields": {
            "Planning Application Reference": "Planning Application Reference",
            "Planning Authority": "Planning Authority",
            "Planning Application Submitted": "Planning Application Submitted",
            "Planning Application Withdrawn": "Planning Application Withdrawn",
            "Planning Permission Refused": "Planning Permission Refused",
            "Appeal Lodged": "Appeal Lodged",
            "Appeal Withdrawn": "Appeal Withdrawn",
            "Appeal Refused": "Appeal Refused",
            "Appeal Granted": "Appeal Granted",
            "Planning Permission Granted": "Planning Permission Granted",
            "Planning Permission Expired": "Planning Permission Expired",
            "Under Construction": "Under Construction",
            "Operational": "Operational",
        },
        "handler": create_planning_row,
    }
}

REPD_FIELD_MAP = {
    alias: header
    for group in REPD_GROUPS.values()
    for alias, header in group["fields"].items()
}

REPD_PIPELINE = [
    "site",
    "developer",
    "technology",
    "project",
    "planning"
]

DEFAULT_COUNTRY = "GB"

# -----------------------------
#  create db
# -----------------------------

def load_repd(csv_path: Path, db_path: Path, recreate: bool = False) -> None:
    if recreate and db_path.exists():
        db_path.unlink()

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_SQL)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows_processed = 0
        with conn:
            for row in reader:
                context: Context = {}
                for group_name in REPD_PIPELINE:
                    group = REPD_GROUPS[group_name]
                    result = group["handler"](conn, row, context)
                    if result:
                        context.update(result)
                rows_processed += 1
        
        print(f"Number of rows processed: {rows_processed}")

# -----------------------------
#  entry point
# -----------------------------

def main() -> None:
    parser = ArgumentParser(
        description="Load REPD CSV data into SQLite database"
    )

    parser.add_argument(
        "csv_file",
        type=Path,
        help="Path to the REPD CSV file"
    )

    parser.add_argument(
        "db_file",
        type=Path,
        nargs="?",
        default=None,
        help="Path to the SQLite database (defaults to .db extension)"
    )

    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate the database if it exists"
    )

    args = parser.parse_args()

    if not args.csv_file.exists():
        print(f"Error, CSV file not found: {args.csv_file}")
        raise SystemExit(1)
    
    db_file = args.db_file or args.csv_file.with_suffix(".db")

    print(f"Loading {args.csv_file} into {db_file}...")
    load_repd(args.csv_file, db_file, recreate=args.recreate)
    print("Done!")

if __name__ == "__main__":
    main()