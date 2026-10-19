from fastapi import APIRouter
from app.api.v1 import zones, units, events, tactical, analytics

api_router = APIRouter()
api_router.include_router(zones.router, prefix="/zones", tags=["Zones"])
api_router.include_router(units.router, prefix="/units", tags=["Units"])
api_router.include_router(events.router, prefix="/events", tags=["OSINT Events"])
api_router.include_router(tactical.router, prefix="/tactical", tags=["Tactical Board"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
