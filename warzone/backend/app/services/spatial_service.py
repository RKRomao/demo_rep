"""
Serviço de Análise Espacial e Cálculo Militar com Especificações Reais de Armamento (FastAPI + GIS)
===================================================================================================
Calcula o alcance efetivo real (em quilómetros) com base nas tabelas de tiro de sistemas de artilharia,
mísseis, defesa aérea e drones utilizados no conflito.
"""

from datetime import datetime
from typing import Dict, Any

# Tabela de Alcances Reais baseada em Doutrina Militar e Tabelas de Tiro Reais (em KM)
REAL_WEAPON_RANGE_MAP = {
    # 1. Drones Estratégicos e de Longo Alcance (Deep Strike)
    "SHAHED": 1500.0,         # Shahed-136 / Geran-2 (1500 km - 2500 km)
    "GERAN": 1500.0,
    "LYUTYI": 1000.0,         # Drone de ataque longo alcance ucraniano (1000 km)
    "BOBER": 800.0,           # Drone Kamikaze Bober (800 km)
    "MAGURA": 800.0,          # Drone Naval USV Magura V5 (800 km)
    "SEA BABY": 1000.0,       # USV Marítimo Sea Baby (1000 km)
    
    # 2. Drones de Reconhecimento e Loitering Munitions (Média Distância)
    "ORLAN": 120.0,           # Orlan-10 / Orlan-30 (120 km)
    "SHARK": 80.0,            # UAV Reconhecimento Shark (80 km)
    "LELEKA": 50.0,           # Leleka-100 (50 km)
    "LANCET": 45.0,           # ZALA Lancet-3 Kamikaze (45 km)
    "SWITCHBLADE": 40.0,      # Switchblade 600 (40 km)
    "WARMATE": 30.0,          # Warmate (30 km)
    
    # 3. Drones Táticos de Linha da Frente (FLOT)
    "MADYAR": 25.0,           # Força FPV com antenas de transmissão/revezamento (25 km)
    "FPV": 18.0,              # Drones FPV Kamikaze com repeater (18 km)
    "BABA YAGA": 12.0,        # Heavy Bomber Quad/Octocopter Noturno (12 km)
    "MAVIC": 7.0,             # DJI Mavic 3 Reconhecimento Tático (7 km)
    
    # 4. Artilharia de Foguetes & Mísseis Táticos
    "ATACMS": 300.0,
    "HIMARS": 84.0,           # GMLRS M31 (84 km)
    "M270": 84.0,             # GMLRS M31 (84 km)
    "TORNADO-S": 120.0,
    "SMERCH": 90.0,           # BM-30 Smerch 300mm (90 km)
    "URAGAN": 35.0,           # BM-27 Uragan 220mm (35 km)
    "GRAD": 20.4,             # BM-21 Grad 122mm (20.4 km)
    
    # 5. Defesa Aérea (SAM / Air Defense)
    "S-400": 250.0,           # Míssil 48N6DM (250 km)
    "PATRIOT": 160.0,         # PAC-2 / PAC-3 (160 km)
    "S-300": 120.0,
    "SAMP/T": 120.0,
    "IRIS-T": 40.0,           # IRIS-T SLM (40 km)
    "NASAMS": 40.0,           # AMRAAM-ER (40 km)
    "GEPARD": 4.5,
    
    # 6. Artilharia de Campanha 155mm / 152mm (Tubo L/52 vs L/39)
    "PZH 2000": 40.0,         # Tubo L/52 (40 km conv / 54 km Vulcano)
    "CAESAR": 42.0,           # Tubo L/52 (42 km ERFB)
    "ARCHER": 40.0,           # Tubo L/52 (40 km / 50 km Excalibur)
    "KRAB": 40.0,
    "2S22 BOHDANA": 42.0,
    "2S19 MSTA-S": 29.0,
    "M777": 30.0,             # Tubo L/39 (24.7 km conv / 30-40 km Excalibur)
    "M109": 30.0,
    "D-20": 17.4,
    "2S3 AKATSIYA": 18.5,
    "2S1 GVOZDIKA": 15.2,
    "D-30": 15.4,
    "MORTEIRO": 7.2,
    "120MM": 7.2
}

def calculate_effective_range_km(equipment_summary: str, category_code: str) -> float:
    """
    Calcula o alcance efetivo real (em km) baseado no equipamento do destacamento.
    """
    if not equipment_summary:
        return 20.0

    eq_upper = equipment_summary.upper()
    for weapon_keyword, range_km in REAL_WEAPON_RANGE_MAP.items():
        if weapon_keyword in eq_upper:
            return range_km

    # Fallback por Categoria Militar Padrão
    if "DRONE" in category_code:
        return 20.0
    elif "ARTILLERY" in category_code:
        return 30.0
    elif "HQ" in category_code:
        return 5.0

    return 10.0

def calculate_temporal_decay(last_updated_date: datetime) -> Dict[str, Any]:
    if not last_updated_date:
        return {"days_since_update": 0, "ghost_opacity": 1.0}

    now = datetime.now()
    if isinstance(last_updated_date, str):
        try:
            last_updated_date = datetime.fromisoformat(last_updated_date.replace("Z", "+00:00"))
        except ValueError:
            return {"days_since_update": 0, "ghost_opacity": 1.0}

    days_old = (now - last_updated_date.replace(tzinfo=None)).days
    days_old = max(0, days_old)

    if days_old <= 1:
        opacity = 1.0
    elif days_old <= 3:
        opacity = 0.8
    elif days_old <= 7:
        opacity = 0.55
    else:
        opacity = 0.35

    return {
        "days_since_update": days_old,
        "ghost_opacity": opacity
    }
