"""
WARZONE GIS - Algoritmo de Triangulação Tática e Fusão de Dados (Data Fusion Engine)
====================================================================================
Combina anomalias térmicas de satélite (NASA FIRMS) com relatos geolocalizados de canais
militares diretos (Telegram OSINT). Se a distância espacial <= 5km e a janela temporal <= 60 min,
o evento é fundido e promovido a 'HIGH_CONFIDENCE' com score de fiabilidade máxima (5/5).
"""

import math
from datetime import datetime
from typing import List, Dict, Any

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância geodésica em quilómetros entre dois pontos de coordenadas (Lat/Lon)
    utilizando a fórmula de Haversine.
    """
    R = 6371.0 # Raio médio da Terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class TacticalDataFusionEngine:
    def __init__(self, max_distance_km: float = 5.0, max_time_window_minutes: float = 60.0):
        self.max_distance_km = max_distance_km
        self.max_time_window_minutes = max_time_window_minutes

    def fuse_intel_sources(self, firms_anomalies: List[Dict[str, Any]], telegram_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executa a triangulação e fusão de dados de satélite + relatos militares táticos.
        """
        fused_events = []
        used_firms_indices = set()
        used_telegram_indices = set()

        for i, firm in enumerate(firms_anomalies):
            firm_lat, firm_lon = firm["latitude"], firm["longitude"]
            firm_time = firm["timestamp"]

            for j, tele in enumerate(telegram_events):
                if j in used_telegram_indices:
                    continue

                tele_lat, tele_lon = tele["coordinates"][1], tele["coordinates"][0]
                tele_time = tele["timestamp"] if isinstance(tele["timestamp"], datetime) else datetime.now()

                # 1. Calcular Distância Espacial (km)
                dist_km = haversine_distance_km(firm_lat, firm_lon, tele_lat, tele_lon)
                
                # 2. Calcular Janela Temporal (Minutos)
                time_delta_mins = abs((firm_time - tele_time).total_seconds()) / 60.0

                # 3. CRITÉRIO DE TRIANGULAÇÃO: Distância <= 5km e Janela <= 60 min
                if dist_km <= self.max_distance_km and time_delta_mins <= self.max_time_window_minutes:
                    # FUSÃO DE DADOS COMPROVADA (HIGH_CONFIDENCE)
                    fused_event = {
                        "external_id": f"fused_{firm.get('sensor', 'firms')}_{tele.get('external_id', j)}",
                        "source_name": f"TRIANGULATED_INTEL ({firm['source_name']} + {tele['source_name']})",
                        "category": tele.get("category", "SHELLING"),
                        "title": f"[VALIDADO POR SATELITE + TELEMETRIA] {tele['title']}",
                        "description": f"{tele.get('description', '')} (Anomalia termica de {firm['frp_mw']} MW confirmada por satelite a {dist_km:.2f}km).",
                        "event_timestamp": firm_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "coordinates": [firm_lon, firm_lat],
                        "reliability_score": 5, # Máxima confiança (5/5)
                        "verified": True,
                        "precision_class": "HIGH_PRECISION",
                        "location_name": tele.get("location_name", "Setor Tatico Validado"),
                        "severity": "critical",
                        "fusion_metadata": {
                            "spatial_distance_km": round(dist_km, 2),
                            "temporal_delta_minutes": round(time_delta_mins, 1),
                            "firms_frp_mw": firm["frp_mw"],
                            "confidence": "HIGH_CONFIDENCE_TRIANGULATED"
                        }
                    }
                    fused_events.append(fused_event)
                    used_firms_indices.add(i)
                    used_telegram_indices.add(j)
                    break

        for j, tele in enumerate(telegram_events):
            if j not in used_telegram_indices:
                fused_events.append(tele)

        for i, firm in enumerate(firms_anomalies):
            if i not in used_firms_indices:
                fused_events.append(firm)

        return fused_events

if __name__ == "__main__":
    from datetime import datetime, timedelta
    now = datetime.now()

    firms_sample = [
        {
            "latitude": 48.2820,
            "longitude": 37.1824,
            "brightness_kelvin": 370.0,
            "frp_mw": 125.0,
            "timestamp": now - timedelta(minutes=15),
            "source_name": "NASA_FIRMS_VIIRS",
            "sensor": "VIIRS"
        }
    ]

    telegram_sample = [
        {
            "external_id": "tg_9901",
            "source_name": "DeepState_OSINT",
            "category": "SHELLING",
            "title": "Ataque de Artilharia de 152mm no Setor de Pokrovsk",
            "description": "Explosao de deposito de municao confirmada nas coordenadas 48.280, 37.185.",
            "timestamp": now - timedelta(minutes=20),
            "coordinates": [37.1850, 48.2800],
            "reliability_score": 3,
            "verified": False,
            "location_name": "Pokrovsk"
        }
    ]

    fusion = TacticalDataFusionEngine()
    result = fusion.fuse_intel_sources(firms_sample, telegram_sample)
    print("=== RESULTADO DA FUSAO DE DADOS E TRIANGULACAO ===")
    for ev in result:
        print(f"\n[Fonte: {ev['source_name']}]")
        print(f" -> Titulo: {ev['title']}")
        print(f" -> Fiabilidade: {ev['reliability_score']}/5 | Verificado: {ev['verified']}")
        print(f" -> Coordenadas Fundidas: {ev['coordinates']}")
