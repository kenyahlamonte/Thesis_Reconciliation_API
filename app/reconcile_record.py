from dataclasses import dataclass
from typing import Optional

#current dataclass structure, likely more fields required
@dataclass
class ProjectRecord:
    id: str
    name: str
    capacity_mw: Optional[float] = None
