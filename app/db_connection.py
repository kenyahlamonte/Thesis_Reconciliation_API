import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from contextlib import contextmanager

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "raw" / "repd-q2-jul-2025.db"

@dataclass
class ProjectRecord:
    id : str
    name : str
    name_normalised : str
    capacity_mw : Optional[float] = None
    status : Optional[str] = None
    technology: Optional[str] = None
    country: Optional[str] = None
    site_name: Optional[str] = None
    site_name_normalised: Optional[str] = None
    developer: Optional[str] = None
    developer_normalised: Optional[str] = None

@contextmanager
def get_db_connection(db_path: Path = DEFAULT_DB_PATH):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def fetch_all_projects(db_path: Path = DEFAULT_DB_PATH) -> List[ProjectRecord]:
    with get_db_connection(db_path) as conn:
        tech_map = {
            r['technology_id']: r['tech_name']
            for r in conn.execute("SELECT technology_id, tech_name FROM technology")
        }
        site_map = {
            r['site_id']: (r['site_name'], r['name_normalised'] or "")
            for r in conn.execute("SELECT site_id, site_name, name_normalised FROM site")
        }
        company_map = {
            r['site_id']: (r['site_name'], r['name_normalised'] or "")
            for r in conn.execute("SELECT site_id, site_name, name_normalised FROM site")
        }

        projects = conn.execute("""
            SELECT
                project_id, canonical_name, name_normalised,
                capacity_mw, status, country,
                technology_id, site_id, lead_company
            FROM project
        """)

        result: list[ProjectRecord] = []
        for r in projects:
            site_data = site_map.get(r['site_id'], (None, ""))
            company_data = company_map.get(r['lead_company'], (None, ""))

            result.append(ProjectRecord(
                id=f"repd-{r['project_id']}",
                name=r['canonical_name'],
                name_normalised=r['name_normalised'],
                capacity_mw=r['capacity_mw'],
                status=r['status'],
                technology=tech_map.get(r['technology_id']),
                country=r['country'],
                site_name=site_data[0],
                site_name_normalised=site_data[1],
                developer=company_data[0],
                developer_normalised=company_data[1]
            ))
        
        return result
    
def get_project_count(db_path: Path = DEFAULT_DB_PATH) -> int:
    with get_db_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM project")
        return cursor.fetchone()[0]
    
def check_database_exists(db_path: Path = DEFAULT_DB_PATH) -> bool:
    return db_path.exists()