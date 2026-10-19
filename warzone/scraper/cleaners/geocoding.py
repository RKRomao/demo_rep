"""
Geocoding & Spatial Normalizer.
Verifica nomes de cidades/nós topográficos e atribui coordenadas WGS84 (Longitude, Latitude).
"""
import re
from typing import Optional, Tuple

# Gazetteer de localidades táticas conhecidas no conflito (WGS84: Longitude, Latitude)
KNOWN_LOCATIONS = {
    "KYIV": (30.5234, 50.4501),
    "KIEV": (30.5234, 50.4501),
    "KHARKIV": (36.2304, 49.9935),
    "POKROVSK": (37.1824, 48.2820),
    "CHASIV YAR": (37.8333, 48.5833),
    "KHERSON": (32.6169, 46.6354),
    "ZAPORIZHZHIA": (35.1396, 47.8388),
    "DNIPRO": (35.0462, 48.4647),
    "SUDZHA": (35.2711, 51.1925),
    "KURSK": (36.1872, 51.7304),
    "KUPYANSK": (37.6167, 49.7167),
    "BAKHMUT": (38.0000, 48.6000),
    "ROBOTYNE": (35.8400, 47.4400),
    "SEVASTOPOL": (33.5224, 44.6166),
}

def extract_coordinates_from_text(text: str) -> Optional[Tuple[float, float]]:
    """
    Procura por coordenadas ou nomes de localidades no texto do evento OSINT.
    Retorna (Longitude, Latitude) se encontrado.
    """
    if not text:
        return None

    # 1. Procura por coordenadas numéricas explícitas (Lat, Long ou Long, Lat)
    coord_pattern = r'(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)'
    match = re.search(coord_pattern, text)
    if match:
        val1, val2 = float(match.group(1)), float(match.group(2))
        # Validar qual é lat (40-55) e long (30-40) na zona do conflito
        if 40.0 <= val1 <= 55.0 and 25.0 <= val2 <= 45.0:
            return (val2, val1) # (long, lat)
        elif 40.0 <= val2 <= 55.0 and 25.0 <= val1 <= 45.0:
            return (val1, val2)

    # 2. Procura no Gazetteer de localidades
    upper_text = text.upper()
    for loc_name, coords in KNOWN_LOCATIONS.items():
        if loc_name in upper_text:
            return coords

    return None
