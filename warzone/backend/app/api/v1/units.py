from fastapi import APIRouter, Query
from typing import Optional, List
from datetime import datetime, timedelta
from app.schemas.geojson import GeoJSONFeatureCollection, GeoJSONFeature, GeoJSONGeometry
from app.schemas.unit import UnitCategoryResponse
from app.services.fallback_data import FALLBACK_UNITS, FALLBACK_UNIT_CATEGORIES
from app.services.spatial_service import calculate_effective_range_km, calculate_temporal_decay

router = APIRouter()

# Simular datas de atualização para demonstrar o Decaimento Temporal (Ghosting)
DUMMY_UPDATE_DATES = {
    1: datetime.now() - timedelta(hours=4),        # 47ª Brigada (Hoje - 100% Opacidade)
    2: datetime.now() - timedelta(days=2),         # 82ª Assalto Aéreo (2 Dias - 80% Opacidade)
    3: datetime.now() - timedelta(hours=1),        # Madyar Birds (Recente - 100% Opacidade)
    4: datetime.now() - timedelta(days=5),         # HQ Sul (5 Dias - 55% Opacidade)
    5: datetime.now() - timedelta(hours=12),       # OPFOR 1ª Brigada (12 Horas - 100% Opacidade)
    6: datetime.now() - timedelta(days=9)          # OPFOR HQ Surovikin (9 Dias - 35% Ghosting)
}

@router.get("", response_model=GeoJSONFeatureCollection)
async def get_military_units(
    faction: Optional[str] = Query(None, description="Filtrar por facção: BLUFOR, OPFOR"),
    status: Optional[str] = Query(None, description="Filtrar por estado: ACTIVE, ENGAGED, RESERVE")
):
    """
    Retorna a localização, simbologia NATO APP-6D, raio de alcance de armas (km)
    e atenuação de opacidade por decaimento temporal (OPSEC Ghosting).
    """
    features = []
    category_map = {cat["code"]: cat for cat in FALLBACK_UNIT_CATEGORIES}

    for unit in FALLBACK_UNITS:
        if faction and unit["faction"].upper() != faction.upper():
            continue
        if status and unit["status"].upper() != status.upper():
            continue

        cat_info = category_map.get(unit["category_code"], {})
        
        # 1. Calcular Alcance Efetivo das Armas (km)
        range_km = calculate_effective_range_km(
            unit.get("equipment_summary", ""), 
            unit.get("category_code", "")
        )

        # 2. Calcular Decaimento Temporal (Ghosting OPSEC)
        last_updated = DUMMY_UPDATE_DATES.get(unit["id"], datetime.now())
        decay_info = calculate_temporal_decay(last_updated)

        feature = GeoJSONFeature(
            type="Feature",
            id=unit["id"],
            geometry=GeoJSONGeometry(
                type="Point",
                coordinates=unit["coordinates"] # [long, lat]
            ),
            properties={
                "id": unit["id"],
                "name": unit["name"],
                "category_code": unit["category_code"],
                "category_name": cat_info.get("name", "Destacamento"),
                "nato_symbol_code": cat_info.get("nato_symbol_code", "SFGPU------"),
                "faction": unit["faction"],
                "echelon": unit["echelon"],
                "commander": unit["commander"],
                "equipment_summary": unit["equipment_summary"],
                "personnel_count": unit["personnel_count"],
                "status": unit["status"],
                "effective_range_km": range_km,
                "days_since_update": decay_info["days_since_update"],
                "ghost_opacity": decay_info["ghost_opacity"],
                "last_updated": last_updated.isoformat()
            }
        )
        features.append(feature)

    return GeoJSONFeatureCollection(features=features)

@router.get("/categories", response_model=List[UnitCategoryResponse])
async def get_unit_categories():
    """
    Retorna o catálogo de categorias de unidades com simbologia militar NATO.
    """
    return FALLBACK_UNIT_CATEGORIES
