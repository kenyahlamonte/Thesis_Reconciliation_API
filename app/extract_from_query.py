from typing import Optional, Dict, List, Any

PROPERTY_ALIASES = {
    # capacity
    'MW Connected': 'capacity_mw',
    'MW Increase / Decrease': 'capacity_mw',
    'Cumulative Total Capacity (MW)': 'capacity_mw',

    # developer
    'Customer Name': 'customer_name',

    # site
    'Connection Site': 'connection_site',

    # technology
    'Plant Type': 'plant_type',

    # status
    'Project Status': 'project_status'
}

def extract_properties(props: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    if not props:
        return result

    for p in props:
        pid = p.get("pid")
        value = p.get("v")

        if pid is None or value is None:
            continue

        internal_name = PROPERTY_ALIASES.get(pid) or pid.lower().replace(' ', '_')

        if internal_name == 'capacity_mw':
            try:
                clean = str(value).replace(',', '').replace('MW', '')
                result[internal_name] = float(clean)
            except (TypeError, ValueError):
                pass

        else:
            result[internal_name] = value

    return result
