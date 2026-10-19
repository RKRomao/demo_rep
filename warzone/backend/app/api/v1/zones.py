from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.schemas.geojson import GeoJSONFeatureCollection, GeoJSONFeature, GeoJSONGeometry
from app.services.fallback_data import FALLBACK_ZONES

router = APIRouter()

@router.get("", response_model=GeoJSONFeatureCollection)
async def get_territorial_zones(
    target_date: Optional[str] = Query(None, description="Data YYYY-MM-DD para a Máquina do Tempo Histórica")
):
    """
    Retorna as zonas de controlo territorial (ocupadas, libertadas, faixas de conflito)
    no formato padrão GeoJSON FeatureCollection.
    """
    features = []
    for zone in FALLBACK_ZONES:
        feature = GeoJSONFeature(
            type="Feature",
            id=zone["id"],
            geometry=GeoJSONGeometry(
                type="Polygon",
                coordinates=zone["coordinates"]
            ),
            properties={
                "id": zone["id"],
                "name": zone["name"],
                "zone_type": zone["zone_type"],
                "fill_color": zone["fill_color"],
                "stroke_color": zone["stroke_color"],
                "fill_opacity": zone["fill_opacity"],
                "area_sq_km": zone["area_sq_km"],
                "notes": zone["notes"]
            }
        )
        features.append(feature)

    return GeoJSONFeatureCollection(features=features)
