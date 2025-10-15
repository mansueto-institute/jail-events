"""
Cook County Jail Locations Database
Contains known jail facilities with their official addresses and coordinates.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import polars as pl

@dataclass
class JailLocation:
    """Represents a jail facility with its location data."""
    name: str
    official_name: str
    address: str
    city: str
    state: str
    zip_code: str
    latitude: float
    longitude: float
    facility_type: str  # 'county', 'municipal', 'juvenile'
    divisions: Optional[List[str]] = None

# Known Cook County Jail Facilities
COOK_COUNTY_JAILS = [
    JailLocation(
        name="Cook County Jail Main",
        official_name="Cook County Department of Corrections",
        address="2700 S California Ave",
        city="Chicago",
        state="IL",
        zip_code="60608",
        latitude=41.8444,
        longitude=-87.6967,
        facility_type="county",
        divisions=["Division 6", "Division 8", "Division 9", "Division 10", "Division 16", "Women's Justice Services"]
    ),
    JailLocation(
        name="Cook County Jail Division 11",
        official_name="Cook County Jail Division 11",
        address="3015 S California Blvd",
        city="Chicago",
        state="IL",
        zip_code="60608",
        latitude=41.8444,
        longitude=-87.6967,
        facility_type="county",
        divisions=["Division 11"]
    ),
    JailLocation(
        name="Cicero Jail",
        official_name="Cicero Police Department Jail",
        address="4901 W Cermak Rd",
        city="Cicero",
        state="IL",
        zip_code="60804",
        latitude=41.8517,
        longitude=-87.7556,
        facility_type="municipal"
    ),
    JailLocation(
        name="Lyons Police Jail",
        official_name="City of Lyons Police Department Jail",
        address="4200 Lawndale Ave",
        city="Lyons",
        state="IL",
        zip_code="60534",
        latitude=41.8125,
        longitude=-87.8208,
        facility_type="municipal"
    ),
    JailLocation(
        name="Juvenile Detention Center",
        official_name="Cook County Juvenile Temporary Detention Center",
        address="1100 S Hamilton Ave",
        city="Chicago",
        state="IL",
        zip_code="60612",
        latitude=41.8706,
        longitude=-87.6667,
        facility_type="juvenile"
    )
]

def get_jail_locations_df() -> pl.DataFrame:
    """Convert jail locations to a Polars DataFrame."""
    data = []
    for jail in COOK_COUNTY_JAILS:
        data.append({
            "jail_name": jail.name,
            "official_name": jail.official_name,
            "address": jail.address,
            "city": jail.city,
            "state": jail.state,
            "zip_code": jail.zip_code,
            "latitude": jail.latitude,
            "longitude": jail.longitude,
            "facility_type": jail.facility_type,
            "divisions": jail.divisions
        })
    
    return pl.DataFrame(data)

def get_jail_by_name(name: str) -> Optional[JailLocation]:
    """Get a jail location by name (case-insensitive)."""
    name_lower = name.lower()
    for jail in COOK_COUNTY_JAILS:
        if name_lower in jail.name.lower() or name_lower in jail.official_name.lower():
            return jail
    return None

def get_jails_by_type(facility_type: str) -> List[JailLocation]:
    """Get all jails of a specific type."""
    return [jail for jail in COOK_COUNTY_JAILS if jail.facility_type == facility_type]

def get_all_jail_names() -> List[str]:
    """Get all jail names for reference."""
    return [jail.name for jail in COOK_COUNTY_JAILS]
