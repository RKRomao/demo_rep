"""
In-Memory Fallback GIS Data Provider com Eventos das Últimas 24h, Alcance Real de Armas e Decaimento Temporal OPSEC (Ghosting)
"""
from datetime import datetime, timedelta

FALLBACK_UNIT_CATEGORIES = [
    {"id": 1, "code": "INFANTRY", "name": "Infantaria Mecanizada", "nato_symbol_code": "SFGPUCI----D---", "default_faction": "BLUFOR"},
    {"id": 2, "code": "ARMOR", "name": "Cavalaria Blindada", "nato_symbol_code": "SFGPUCA----D---", "default_faction": "BLUFOR"},
    {"id": 3, "code": "ARTILLERY", "name": "Artilharia de Campanha / MLRS", "nato_symbol_code": "SFGPUCA---FA---", "default_faction": "BLUFOR"},
    {"id": 4, "code": "AVIATION", "name": "Aviação de Caça", "nato_symbol_code": "SFGPUAV----D---", "default_faction": "BLUFOR"},
    {"id": 5, "code": "DRONE_SSO", "name": "Drones FPV & SSO", "nato_symbol_code": "SFGPUCR----D---", "default_faction": "BLUFOR"},
    {"id": 6, "code": "HQ", "name": "Quartel-General Tático (TCP)", "nato_symbol_code": "SFGPUHQ----D---", "default_faction": "BLUFOR"},
    {"id": 7, "code": "OPFOR_INF", "name": "Infantaria Inimiga", "nato_symbol_code": "SHGPUCI----D---", "default_faction": "OPFOR"},
    {"id": 8, "code": "OPFOR_ARMOR", "name": "Cavalaria Blindada Inimiga", "nato_symbol_code": "SHGPUCA----D---", "default_faction": "OPFOR"},
    {"id": 9, "code": "OPFOR_HQ", "name": "Posto de Comando Inimigo", "nato_symbol_code": "SHGPUHQ----D---", "default_faction": "OPFOR"}
]

FALLBACK_UNITS = [
    {
        "id": 1,
        "name": "47ª Brigada Mecanizada \"Magura\"",
        "category_code": "INFANTRY",
        "faction": "BLUFOR",
        "echelon": "BRIGADE",
        "commander": "Cel. Pavlo Palisa",
        "equipment_summary": "M2A2 Bradley, Leopard 2A6, M113, Morteiros 120mm",
        "personnel_count": 3500,
        "status": "ENGAGED",
        "coordinates": [37.1824, 48.2820],
        "effective_range_km": 12.0,
        "days_since_update": 0,
        "ghost_opacity": 1.0
    },
    {
        "id": 2,
        "name": "82ª Brigada de Assalto Aéreo",
        "category_code": "INFANTRY",
        "faction": "BLUFOR",
        "echelon": "BRIGADE",
        "commander": "Ten.-Cel. Yevhen Moisiuk",
        "equipment_summary": "Stryker, Marder 1A3, Challenger 2, Obus L118",
        "personnel_count": 2800,
        "status": "ACTIVE",
        "coordinates": [35.3200, 51.1500],
        "effective_range_km": 18.0,
        "days_since_update": 2,
        "ghost_opacity": 0.80
    },
    {
        "id": 3,
        "name": "Unidade de Drones \"Madyar Birds\" & Obus M777",
        "category_code": "ARTILLERY",
        "faction": "BLUFOR",
        "echelon": "COMPANY",
        "commander": "Cap. Robert \"Madyar\" Brovdi",
        "equipment_summary": "Drones FPV Kamikaze, Heavy Bomber Drones, M777 (Excalibur)",
        "personnel_count": 450,
        "status": "ENGAGED",
        "coordinates": [37.8000, 48.4000],
        "effective_range_km": 30.0, # Artilharia de campanha 155mm M777 com Excalibur (30km)
        "days_since_update": 0,
        "ghost_opacity": 1.0
    },
    {
        "id": 4,
        "name": "Bateria HIMARS / 27ª Brigada de Artilharia",
        "category_code": "ARTILLERY",
        "faction": "BLUFOR",
        "echelon": "BATALLION",
        "commander": "Maj. D. Kovalenko",
        "equipment_summary": "M142 HIMARS, M270 MLRS (GMLRS M31)",
        "personnel_count": 300,
        "status": "ACTIVE",
        "coordinates": [35.1396, 47.8388],
        "effective_range_km": 84.0, # M142 HIMARS GMLRS (84 km)
        "days_since_update": 5,
        "ghost_opacity": 0.55
    },
    {
        "id": 5,
        "name": "1ª Brigada de Infantaria de Guardas (OPFOR)",
        "category_code": "OPFOR_INF",
        "faction": "OPFOR",
        "echelon": "BRIGADE",
        "commander": "Gen.-Maj. V. Gerasimov",
        "equipment_summary": "T-90M Proryv, BMP-3, BTR-82A, D-30 122mm",
        "personnel_count": 4200,
        "status": "ENGAGED",
        "coordinates": [37.5000, 48.2000],
        "effective_range_km": 15.4, # Obus D-30 122mm (15.4 km)
        "days_since_update": 1,
        "ghost_opacity": 1.0
    },
    {
        "id": 6,
        "name": "Bateria S-400 & EW OPFOR \"Surovikin\"",
        "category_code": "OPFOR_HQ",
        "faction": "OPFOR",
        "echelon": "DIVISION",
        "commander": "Gen. Surovikin",
        "equipment_summary": "Sistemas S-400 Triumf (48N6DM), EW Krasukha-4",
        "personnel_count": 1200,
        "status": "ACTIVE",
        "coordinates": [38.2000, 47.5000],
        "effective_range_km": 200.0, # S-400 Triumf (200 km)
        "days_since_update": 9,
        "ghost_opacity": 0.35
    }
]

FALLBACK_ZONES = [
    {
        "id": 1,
        "name": "Península da Crimeia (Ocupada)",
        "zone_type": "OCCUPIED",
        "fill_color": "#EF4444",
        "stroke_color": "#991B1B",
        "fill_opacity": 0.35,
        "area_sq_km": 27000.0,
        "notes": "Península sob ocupação com forte fortificação militar.",
        "coordinates": [[[33.60, 46.15], [33.85, 46.00], [34.30, 45.95], [34.70, 46.00], [35.05, 45.85], [35.35, 45.65], [36.10, 45.40], [36.45, 45.35], [36.65, 45.22], [36.45, 45.05], [36.20, 45.00], [35.80, 45.05], [34.90, 44.75], [34.40, 44.50], [34.10, 44.40], [33.70, 44.45], [33.50, 44.55], [33.40, 44.65], [33.55, 44.90], [32.65, 45.35], [32.48, 45.70], [32.80, 45.82], [33.20, 45.68], [33.40, 45.88], [33.60, 46.15]]]
    },
    {
        "id": 2,
        "name": "Donbas & Corredor de Azov (Ocupado)",
        "zone_type": "OCCUPIED",
        "fill_color": "#DC2626",
        "stroke_color": "#7F1D1D",
        "fill_opacity": 0.35,
        "area_sq_km": 34500.0,
        "notes": "Setor Leste do Donbas e faixa costeira de Azov.",
        "coordinates": [[[37.10, 49.50], [37.60, 49.85], [38.20, 49.90], [38.80, 49.75], [39.50, 49.80], [40.10, 49.45], [40.25, 49.10], [39.90, 48.65], [40.05, 48.20], [39.85, 47.70], [39.20, 47.15], [38.80, 47.10], [38.25, 47.10], [37.90, 46.90], [37.50, 47.10], [37.20, 46.90], [36.80, 46.75], [36.40, 46.85], [36.10, 46.65], [36.60, 47.10], [37.10, 47.35], [37.55, 47.75], [37.80, 48.00], [37.60, 48.40], [37.95, 48.65], [37.70, 48.95], [37.20, 49.10], [37.10, 49.50]]]
    },
    {
        "id": 3,
        "name": "Linha de Conflito Ativo (Faixa Tática)",
        "zone_type": "ACTIVE_CONFLICT",
        "fill_color": "#F59E0B",
        "stroke_color": "#B45309",
        "fill_opacity": 0.40,
        "area_sq_km": 12000.0,
        "notes": "Corredor de confronto direto de 1200km.",
        "coordinates": [[[37.10, 49.80], [37.45, 49.60], [37.90, 49.30], [38.15, 49.00], [37.90, 48.70], [37.70, 48.40], [37.60, 48.10], [37.30, 47.90], [37.10, 47.70], [36.60, 47.45], [36.20, 47.40], [35.70, 47.45], [35.35, 47.60], [35.15, 47.45], [34.70, 47.25], [33.80, 47.00], [33.40, 46.82], [33.00, 46.70], [32.55, 46.65], [32.40, 46.75], [32.80, 46.85], [33.30, 47.00], [33.90, 47.25], [34.50, 47.40], [34.90, 47.55], [35.40, 47.75], [35.90, 47.65], [36.40, 47.60], [36.90, 47.90], [37.20, 48.20], [37.40, 48.50], [37.30, 48.80], [37.50, 49.10], [37.20, 49.40], [36.90, 49.70], [37.10, 49.80]]]
    },
    {
        "id": 4,
        "name": "Incursão Tática em Kursk (Saliente)",
        "zone_type": "INCURSION",
        "fill_color": "#06B6D4",
        "stroke_color": "#0E7490",
        "fill_opacity": 0.40,
        "area_sq_km": 1350.0,
        "notes": "Saliente tático em Sudzha.",
        "coordinates": [[[35.00, 51.35], [35.15, 51.42], [35.30, 51.45], [35.45, 51.40], [35.58, 51.30], [35.65, 51.20], [35.60, 51.10], [35.48, 51.02], [35.32, 50.98], [35.18, 51.03], [35.05, 51.12], [34.95, 51.22], [35.00, 51.35]]]
    }
]

from datetime import datetime, timedelta
now = datetime.now()

FALLBACK_EVENTS = [
    {
        "id": 1,
        "source_name": "LiveUAmap",
        "external_id": "evt_24h_101",
        "category": "DRONE_ATTACK",
        "title": "Ataque Noturno de Drones Shahed-136 em Kyiv",
        "description": "Defesa aérea abateu 38 de 42 drones atacando alvos de infraestrutura na capital.",
        "event_timestamp": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [30.5234, 50.4501],
        "reliability_score": 5,
        "verified": True,
        "precision_class": "HIGH_PRECISION",
        "location_name": "Kyiv",
        "severity": "critical"
    },
    {
        "id": 2,
        "source_name": "ISW",
        "external_id": "evt_24h_102",
        "category": "TROOP_MOVEMENT",
        "title": "Combates Intensos de Infantaria no Setor de Pokrovsk",
        "description": "A 47ª Brigada Mecanizada travou avanço de coluna blindada ao longo da ferrovia.",
        "event_timestamp": (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [37.1824, 48.2820],
        "reliability_score": 5,
        "verified": True,
        "precision_class": "HIGH_PRECISION",
        "location_name": "Pokrovsk, Donetsk",
        "severity": "critical"
    },
    {
        "id": 3,
        "source_name": "NASA_FIRMS",
        "external_id": "evt_24h_103",
        "category": "SHELLING",
        "title": "Duelo Massivo de Artilharia Pesada em Chasiv Yar",
        "description": "Satélites térmicos detetaram múltiplos incêndios causados por bombardeamento de 152mm.",
        "event_timestamp": (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [37.8333, 48.5833],
        "reliability_score": 4,
        "verified": True,
        "precision_class": "LOW_PRECISION",
        "location_name": "Chasiv Yar",
        "severity": "high"
    },
    {
        "id": 4,
        "source_name": "Telegram_OSINT",
        "external_id": "evt_24h_104",
        "category": "AIRSTRIKE",
        "title": "Ataque com Bombas Guiadas KAB em Kharkiv",
        "description": "Duas bombas de aviação atingiram o distrito industrial do norte de Kharkiv.",
        "event_timestamp": (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [36.2304, 49.9935],
        "reliability_score": 4,
        "verified": True,
        "precision_class": "LOW_PRECISION",
        "location_name": "Kharkiv",
        "severity": "high"
    },
    {
        "id": 5,
        "source_name": "DeepState",
        "external_id": "evt_24h_105",
        "category": "TROOP_MOVEMENT",
        "title": "Operação Tática de Incursão Mantida em Sudzha (Kursk)",
        "description": "Forças de assalto mantêm o controlo da estação de distribuição de gás de Sudzha.",
        "event_timestamp": (now - timedelta(hours=11)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [35.2711, 51.1925],
        "reliability_score": 5,
        "verified": True,
        "precision_class": "HIGH_PRECISION",
        "location_name": "Sudzha, Kursk",
        "severity": "medium"
    },
    {
        "id": 6,
        "source_name": "GUR_Ukraine",
        "external_id": "evt_24h_106",
        "category": "NAVAL_OPS",
        "title": "Drones Navais Magura V5 Atacam Sevastopol",
        "description": "Operação especial marítima danificou lancha de patrulha na baía de Sevastopol.",
        "event_timestamp": (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [33.5224, 44.6166],
        "reliability_score": 5,
        "verified": True,
        "precision_class": "HIGH_PRECISION",
        "location_name": "Sevastopol, Crimeia",
        "severity": "high"
    },
    {
        "id": 7,
        "source_name": "Ukrinform",
        "external_id": "evt_24h_107",
        "category": "INFRASTRUCTURE",
        "title": "Subestação Elétrica Atingida em Dnipro",
        "description": "Ataque com mísseis danificou transformadores de alta tensão na periferia de Dnipro.",
        "event_timestamp": (now - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [35.0462, 48.4647],
        "reliability_score": 4,
        "verified": True,
        "precision_class": "LOW_PRECISION",
        "location_name": "Dnipro",
        "severity": "medium"
    },
    {
        "id": 8,
        "source_name": "LiveUAmap",
        "external_id": "evt_24h_108",
        "category": "SHELLING",
        "title": "Bombardeamento na Margem Direita de Kherson",
        "description": "Artilharia pesada disparada a partir da margem esquerda ocupada atingiu áreas residenciais.",
        "event_timestamp": (now - timedelta(hours=21)).strftime("%Y-%m-%d %H:%M:%S"),
        "coordinates": [32.6169, 46.6354],
        "reliability_score": 4,
        "verified": True,
        "precision_class": "LOW_PRECISION",
        "location_name": "Kherson",
        "severity": "medium"
    }
]

FALLBACK_DRAWINGS = []
