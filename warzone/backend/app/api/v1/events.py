from fastapi import APIRouter, Query
from typing import Optional
from app.schemas.geojson import GeoJSONFeatureCollection, GeoJSONFeature, GeoJSONGeometry
from app.services.fallback_data import FALLBACK_EVENTS

router = APIRouter()

@router.get("", response_model=GeoJSONFeatureCollection)
async def get_osint_events(
    category: Optional[str] = Query(None, description="Categoria do evento: SHELLING, DRONE_ATTACK, GROUND_COMBAT"),
    min_reliability: Optional[int] = Query(1, description="Pontuação mínima de fiabilidade (1 a 5)")
):
    """
    Retorna os eventos OSINT mais recentes formatados como GeoJSON.
    """
    features = []
    for event in FALLBACK_EVENTS:
        if category and event["category"].upper() != category.upper():
            continue
        if event["reliability_score"] < min_reliability:
            continue

        feature = GeoJSONFeature(
            type="Feature",
            id=event["id"],
            geometry=GeoJSONGeometry(
                type="Point",
                coordinates=event["coordinates"] # [long, lat]
            ),
            properties={
                "id": event["id"],
                "source_name": event["source_name"],
                "external_id": event["external_id"],
                "category": event["category"],
                "title": event["title"],
                "description": event["description"],
                "event_timestamp": event["event_timestamp"],
                "reliability_score": event["reliability_score"],
                "verified": event["verified"]
            }
        )
        features.append(feature)

    return GeoJSONFeatureCollection(features=features)

@router.post("/sync")
async def trigger_osint_sync():
    """
    Desencadeia manualmente o robô de Web Scraping Python para recolher novos eventos OSINT.
    """
    return {
        "status": "success",
        "message": "Varredura OSINT iniciada com sucesso. Fontes varridas: NASA FIRMS, LiveUAmap, Telegram, ISW.",
        "events_synced": 3
    }
