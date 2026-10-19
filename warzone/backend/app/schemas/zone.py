from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date

class ZoneCreate(BaseModel):
    name: str
    zone_type: str # SOVEREIGN, OCCUPIED, LIBERATED, ACTIVE_CONFLICT, INCURSION
    valid_from: date
    valid_to: Optional[date] = None
    coordinates: List[Any] # Coordinates array for polygon
    fill_color: str = "#FF0000"
    stroke_color: str = "#880000"
    fill_opacity: float = 0.35
    notes: Optional[str] = None

class ZoneResponse(BaseModel):
    id: int
    name: str
    zone_type: str
    fill_color: str
    stroke_color: str
    fill_opacity: float
    area_sq_km: float
    notes: Optional[str] = None
    coordinates: List[Any]

    class Config:
        from_attributes = True
