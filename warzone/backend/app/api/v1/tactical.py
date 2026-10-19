from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.schemas.tactical import TacticalDrawingCreate, TacticalDrawingResponse
from app.services.fallback_data import FALLBACK_DRAWINGS

router = APIRouter()

@router.get("", response_model=List[TacticalDrawingResponse])
async def get_tactical_drawings(
    session_id: Optional[str] = Query("default_session", description="ID de sessão do utilizador")
):
    """
    Retorna os elementos desenhados no quadro tático pelo utilizador (setas, polígonos, medições).
    """
    user_drawings = [d for d in FALLBACK_DRAWINGS if d.get("user_session_id") == session_id]
    return user_drawings

@router.post("", response_model=TacticalDrawingResponse)
async def create_tactical_drawing(payload: TacticalDrawingCreate):
    """
    Guarda um novo elemento tático desenhado no mapa.
    """
    new_id = len(FALLBACK_DRAWINGS) + 1
    drawing_dict = {
        "id": new_id,
        "user_session_id": payload.user_session_id,
        "title": payload.title,
        "drawing_type": payload.drawing_type,
        "geometry": payload.geometry,
        "style_properties": payload.style_properties,
        "tactical_notes": payload.tactical_notes
    }
    FALLBACK_DRAWINGS.append(drawing_dict)
    return drawing_dict

@router.delete("/{drawing_id}")
async def delete_tactical_drawing(drawing_id: int):
    """
    Remove um elemento tático do mapa.
    """
    global FALLBACK_DRAWINGS
    initial_len = len(FALLBACK_DRAWINGS)
    FALLBACK_DRAWINGS = [d for d in FALLBACK_DRAWINGS if d["id"] != drawing_id]
    if len(FALLBACK_DRAWINGS) == initial_len:
        raise HTTPException(status_code=404, detail="Desenho tático não encontrado")
    return {"status": "success", "message": f"Desenho tático {drawing_id} eliminado."}
