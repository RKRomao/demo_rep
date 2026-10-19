from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class TacticalDrawingCreate(BaseModel):
    user_session_id: str = "default_session"
    title: Optional[str] = "Desenho Tático"
    drawing_type: str # ADVANCE_ARROW, DEFENSIVE_POLY, FLANKING_LINE, MEASUREMENT, NOTE_MARKER
    geometry: Dict[str, Any] # GeoJSON Geometry
    style_properties: Dict[str, Any]
    tactical_notes: Optional[str] = None

class TacticalDrawingResponse(BaseModel):
    id: int
    user_session_id: str
    title: Optional[str] = None
    drawing_type: str
    geometry: Dict[str, Any]
    style_properties: Dict[str, Any]
    tactical_notes: Optional[str] = None

    class Config:
        from_attributes = True
