"""
WARZONE GIS - Ingestor Assíncrono NASA FIRMS (VIIRS/MODIS)
=========================================================
Coleta anomalias térmicas de satélite em tempo real (NRT - Near Real-Time) 
para deteção precoce de duelos de artilharia, explosões de paióis e focos de combate.
"""

import asyncio
# pyrefly: ignore [missing-import]
import aiohttp
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os

# Configurações da API NASA FIRMS
NASA_FIRMS_MAP_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "620b7bc1a6beaa2ffcbb5ed77cf968e7") # Chave publica de desenvolvimento / demo
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/country/csv"

# Delimitação Espacial da Zona de Conflito Ucrânia/Mar Negro/Fronteiras (BBOX)
UKRAINE_BBOX = "22.0,44.0,40.5,52.5"  # [min_lon, min_lat, max_lon, max_lat]
MAP_KEY = NASA_FIRMS_MAP_KEY

class NASAirmsIngestor:
    def __init__(self, api_key: str = MAP_KEY):
        self.api_key = api_key
        self.source_instrument = "VIIRS_SNPP_NRT" # Deteção térmica de alta resolução espacial (375m)

    async def fetch_thermal_anomalies(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        Consulta assíncrona de focos de calor térmicos recentes da NASA FIRMS em tempo real via API & Open CSV.
        """
        urls = [
            f"{FIRMS_BASE_URL}/{self.api_key}/{self.source_instrument}/UKR/{min(days, 10)}",
            "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Europe_24h.csv",
            "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Europe_24h.csv"
        ]
        
        anomalies = []
        headers = {
            "User-Agent": "WARZONE_GIS_Intelligence_Engine/2.0 (+https://warzone-tracker.org)"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            for url in urls:
                try:
                    async with session.get(url, timeout=12) as response:
                        if response.status == 200:
                            text_data = await response.text()
                            parsed = self._parse_firms_csv(text_data)
                            if parsed:
                                anomalies.extend(parsed)
                                break
                except Exception as e:
                    print(f"[FIRMS] Erro ao consultar {url}: {e}")
                    continue

        return anomalies

    def _parse_firms_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        """
        Converte o CSV de resposta da NASA FIRMS em objetos GeoJSON / Dicionários estruturados filtrados para a zona do conflito.
        """
        anomalies = []
        reader = csv.DictReader(io.StringIO(csv_text))
        
        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])

                # Filtrar estritamente pelo Bounding Box da Ucrânia / Mar Negro
                if not (44.0 <= lat <= 52.5 and 22.0 <= lon <= 40.5):
                    continue

                brightness = float(row.get("bright_ti4", row.get("brightness", row.get("bright_t31", 300.0))))
                frp = float(row.get("frp", 10.0))
                acq_date = row.get("acq_date", datetime.now().strftime("%Y-%m-%d"))
                acq_time = str(row.get("acq_time", "1200")).zfill(4)
                
                dt_str = f"{acq_date} {acq_time[:2]}:{acq_time[2:]}:00"
                try:
                    timestamp = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    timestamp = datetime.now()

                severity = "low"
                if frp > 100.0 or brightness > 360.0:
                    severity = "critical"
                elif frp > 35.0:
                    severity = "high"

                anomaly_obj = {
                    "external_id": f"firm_{lon:.3f}_{lat:.3f}_{acq_date}_{acq_time}",
                    "title": f"Deteção Térmica de Satélite VIIRS ({frp:.1f} MW)",
                    "description": f"Anomalia radiativa de elevada energia ({frp:.1f} MW) capturada por satélite espacial.",
                    "latitude": lat,
                    "longitude": lon,
                    "coordinates": [lon, lat],
                    "brightness_kelvin": brightness,
                    "frp_mw": frp,
                    "timestamp": timestamp,
                    "confidence": row.get("confidence", "h"),
                    "severity": severity,
                    "sensor": row.get("instrument", "VIIRS"),
                    "source_name": "NASA_FIRMS_VIIRS"
                }
                anomalies.append(anomaly_obj)
            except (ValueError, KeyError):
                continue
                
        return anomalies

if __name__ == "__main__":
    async def main():
        ingestor = NASAirmsIngestor()
        print("[FIRMS] A consultar anomalias térmicas de satélite na Ucrânia...")
        anomalies = await ingestor.fetch_thermal_anomalies(days=1)
        print(f"[FIRMS] Deteções recolhidas: {len(anomalies)}")
        for a in anomalies[:3]:
            print(f" -> [{a['timestamp']}] Coords: {a['coordinates']} | Potência Radiativa (FRP): {a['frp_mw']} MW | Severidade: {a['severity']}")

    asyncio.run(main())
