import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from contextlib import contextmanager
from .logging_config import get_logger

logger = get_logger(__name__)

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
    logger.debug(f"Opening database connection: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
        logger.debug("Database connection closed")

def fetch_all_projects(db_path: Path = DEFAULT_DB_PATH) -> List[ProjectRecord]:
    logger.info(f"Fetching all projects from database: {db_path}")
    try:
        with get_db_connection(db_path) as conn:
            tech_map = {
                r['technology_id']: r['tech_name']
                for r in conn.execute("SELECT technology_id, tech_name FROM technology")
            }
            logger.debug(f"Loaded {len(tech_map)} technology types")

            site_map = {
                r['site_id']: (r['site_name'], r['name_normalised'] or "")
                for r in conn.execute("SELECT site_id, site_name, name_normalised FROM site")
            }
            logger.debug(f"Loaded {len(site_map)} sites")

            company_map = {
                r['site_id']: (r['site_name'], r['name_normalised'] or "")
                for r in conn.execute("SELECT site_id, site_name, name_normalised FROM site")
            }
            logger.debug(f"Loaded {len(company_map)} companies")

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
            
            logger.info(f"Successfully fetched {len(result)} projects from database")
            return result
    
    except sqlite3.Error as e:
        logger.error(f"Database error while fetching projects: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching projects: {e}", exc_info=True)
        raise
    
def get_project_count(db_path: Path = DEFAULT_DB_PATH) -> int:
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM project")
            return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logger.error(f"Database error while counting projects: {e}")
        return 0
    
def check_database_exists(db_path: Path = DEFAULT_DB_PATH) -> bool:
    exists = db_path.exists()
    if exists:
        logger.debug(f"Database exists: {db_path}")
    else:
        logger.warning(f"Database NOT found: {db_path}")
    return exists