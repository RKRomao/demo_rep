from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class OSINTEventCreate(BaseModel):
    source_name: str
    external_id: Optional[str] = None
    category: str
    title: str
    description: Optional[str] = None
    event_timestamp: datetime
    longitude: float
    latitude: float
    reliability_score: int = 4
    verified: bool = True
    raw_data: Optional[Dict[str, Any]] = None

class OSINTEventResponse(BaseModel):
    id: int
    source_name: str
    external_id: Optional[str] = None
    category: str
    title: str
    description: Optional[str] = None
    event_timestamp: str
    coordinates: List[float] # [longitude, latitude]
    reliability_score: int
    verified: bool

    class Config:
        from_attributes = True
