from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UnitCategoryBase(BaseModel):
    code: str
    name: str
    nato_symbol_code: str
    default_faction: str

class UnitCategoryResponse(UnitCategoryBase):
    id: int

    class Config:
        from_attributes = True

class UnitCreate(BaseModel):
    name: str
    category_id: int
    faction: str = "BLUFOR"
    echelon: str = "BRIGADE"
    commander: Optional[str] = None
    equipment_summary: Optional[str] = None
    personnel_count: Optional[int] = 0
    status: str = "ACTIVE"
    longitude: float
    latitude: float

class UnitResponse(BaseModel):
    id: int
    name: str
    category_code: str
    faction: str
    echelon: str
    commander: Optional[str] = None
    equipment_summary: Optional[str] = None
    personnel_count: int
    status: str
    coordinates: List[float] # [longitude, latitude]
    last_updated: Optional[datetime] = None
    # Alcance Militar & Decaimento Temporal (OPSEC Ghosting)
    effective_range_km: float = 25.0
    days_since_update: int = 0
    ghost_opacity: float = 1.0 # 1.0 (recente) a 0.35 (muito antigo / desatualizado)

    class Config:
        from_attributes = True
