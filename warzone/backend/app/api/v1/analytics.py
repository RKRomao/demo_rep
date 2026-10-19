from fastapi import APIRouter

router = APIRouter()

@router.get("/summary")
async def get_conflict_analytics():
    """
    Retorna dados analíticos geopolíticos e táticos em tempo real (2026).
    """
    return {
        "occupied_territory_pct": 17.85,
        "liberated_sq_km": 42100.0,
        "active_frontline_km": 1200.0,
        "interception_rate_pct": 86.40,
        "total_events_logged": 15420,
        "blufor_units_active": 4,
        "opfor_units_active": 2,
        "last_updated": "2026-09-01T19:57:00Z"
    }
