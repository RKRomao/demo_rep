"""
Parser para Anomalias Térmicas / Incêndios de Combate da NASA FIRMS API/CSV.
"""
import requests
import csv
import io
from datetime import datetime
from typing import List, Dict, Any

class NASAFirmsParser:
    def __init__(self, url: str):
        self.url = url

    def fetch_thermal_events(self) -> List[Dict[str, Any]]:
        events = []
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                reader = csv.DictReader(io.StringIO(response.text))
                for row in reader:
                    lat = float(row.get("latitude", 0))
                    long = float(row.get("longitude", 0))
                    # Filtrar apenas a zona de conflito (Ucrânia/Kursk: Lat 44-53, Long 26-40)
                    if 44.0 <= lat <= 53.0 and 26.0 <= long <= 40.0:
                        brightness = float(row.get("brightness", 0))
                        confidence = int(row.get("confidence", 0))
                        if confidence > 50:
                            events.append({
                                "source_name": "NASA_FIRMS",
                                "external_id": f"firms_{lat}_{long}_{row.get('acq_date')}",
                                "category": "SHELLING",
                                "title": f"Anomalia Térmica de Combate ({brightness}K)",
                                "description": f"Foco térmico detectado por satélite com {confidence}% de confiança.",
                                "event_timestamp": datetime.now().isoformat(),
                                "longitude": long,
                                "latitude": lat,
                                "reliability_score": 5,
                                "verified": True
                            })
        except Exception as e:
            print(f"[NASA FIRMS Scraper] Aviso ao raspar NASA FIRMS: {e}")
        return events
