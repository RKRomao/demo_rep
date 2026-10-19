"""
WARZONE GIS - Ingestor Assíncrono ADS-B Exchange & OpenSky Radar (Transponders Militares ISR)
=============================================================================================
Monitoriza vetores aéreos de inteligência e reconhecimento (RQ-4 Global Hawk, E-3 AWACS, RC-135 Rivet Joint, P-8A Poseidon)
que patrulham o flanco Leste da NATO e a bacia do Mar Negro.
"""

import asyncio
# pyrefly: ignore [missing-import]
import aiohttp
from datetime import datetime
from typing import List, Dict, Any

# Callsigns & ICAO Hex Codes Conhecidos de Vetores Militares de Reconhecimento ISR NATO
NATO_ISR_CALLSIGNS = [
    "FORTE10", "FORTE11", "FORTE12", "FORTE13", "FORTE14",  # RQ-4B Global Hawk (USAF)
    "HOMER11", "HOMER21",                                  # RC-135V/W Rivet Joint (SIGINT)
    "NCHO1", "NCHO2", "NATO01", "NATO02",                  # E-3A Sentry AWACS (NATO)
    "PK01", "PK02", "MADMAX", "DUKE"                        # P-8A Poseidon (US Navy - Mar Negro)
]

OPENSKY_API_URL = "https://opensky-network.org/api/states/all"
# Bounding Box do Flanco Leste NATO / Mar Negro (Polónia, Roménia, Mar Negro)
NATO_EAST_BBOX = {"lamin": 42.0, "lamax": 52.0, "lomin": 20.0, "lomax": 40.0}

class ADSBRadarIngestor:
    def __init__(self):
        self.url = OPENSKY_API_URL

    async def fetch_military_flights(self) -> List[Dict[str, Any]]:
        """
        Consulta os estados de transponder ADS-B ativos na caixa geográfica definida.
        """
        params = {
            "lamin": NATO_EAST_BBOX["lamin"],
            "lamax": NATO_EAST_BBOX["lamax"],
            "lomin": NATO_EAST_BBOX["lomin"],
            "lomax": NATO_EAST_BBOX["lomax"]
        }
        
        headers = {"User-Agent": "WARZONE_GIS_Radar/1.0"}
        military_tracks = []

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(self.url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        states = data.get("states", []) or []
                        military_tracks = self._filter_military_aircraft(states)
                    else:
                        print(f"[ADS-B] Resposta HTTP {response.status} ao consultar OpenSky Network.")
            except Exception as e:
                print(f"[ADS-B] Erro ao consultar transponders ADS-B: {e}.")

        return military_tracks

    def _filter_military_aircraft(self, states: List[List[Any]]) -> List[Dict[str, Any]]:
        tracks = []
        for s in states:
            callsign = (s[1] or "").strip()
            icao24 = s[0]
            lon = s[5]
            lat = s[6]
            altitude_meters = s[7] or s[13] or 0.0
            velocity_m_s = s[9] or 0.0
            heading_deg = s[10] or 0.0

            # Filtrar por callsigns conhecidos ou altitudes estratosféricas (> 14.000m como o RQ-4 Global Hawk)
            is_nato_callsign = any(cs in callsign.upper() for cs in NATO_ISR_CALLSIGNS)
            is_stratos_uav = (altitude_meters > 14000 and velocity_m_s > 120)

            if (is_nato_callsign or is_stratos_uav) and lat and lon:
                track_obj = {
                    "icao24": icao24,
                    "callsign": callsign or "FORTE12_ISR",
                    "latitude": lat,
                    "longitude": lon,
                    "coordinates": [lon, lat],
                    "altitude_meters": altitude_meters,
                    "altitude_feet": round(altitude_meters * 3.28084),
                    "velocity_knots": round(velocity_m_s * 1.94384),
                    "heading_deg": heading_deg,
                    "aircraft_type": "RQ-4B Global Hawk (ISR)" if "FORTE" in callsign else "Aeronave Reconhecimento NATO",
                    "timestamp": datetime.now()
                }
                tracks.append(track_obj)

        return tracks

if __name__ == "__main__":
    async def main():
        ingestor = ADSBRadarIngestor()
        print("[ADS-B Radar] A varrer transponders militares NATO e vetores ISR...")
        tracks = await ingestor.fetch_military_flights()
        print(f"[ADS-B] Vetores de reconhecimento detetados: {len(tracks)}")
        for t in tracks:
            print(f" -> [{t['callsign']}] {t['aircraft_type']} | Posição: {t['coordinates']} | Altitude: {t['altitude_feet']} ft ({t['altitude_meters']}m)")

    asyncio.run(main())
