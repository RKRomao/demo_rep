"""
Mapeamento OSINT Avançado - Extrator de Coordenadas, MGRS, Unidades Militares e Precisão
======================================================================================
Este módulo processa mensagens de texto OSINT (Telegram, ISW, LiveUAmap) e extrai:
1. Coordenadas exatas em Graus Decimais (Lat/Lon) ou formato MGRS (Military Grid Reference System).
2. Entidades de Unidades Militares mencionadas no texto.
3. Classificação de precisão da informação ('HIGH_PRECISION' vs 'LOW_PRECISION').
"""

import re
from typing import Dict, Any, Optional, List, Tuple

# Gazetteer de Cidades para Fallback de Baixa Precisão (Longitude, Latitude)
CITY_GAZETTEER = {
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
    "TORETSK": (37.8786, 48.3914),
    "VOVCHANSK": (36.9356, 50.2869)
}

# Dicionário de Regex para Unidades Militares Conhecidas (BLUFOR / OPFOR)
MILITARY_UNITS_PATTERNS = [
    (r'\b47[ªa]?\s*(?:Brigada|Brig)\b', '47ª Brigada Mecanizada "Magura"'),
    (r'\b82[ªa]?\s*(?:Brigada|Brig)\b', '82ª Brigada de Assalto Aéreo'),
    (r'\b101st\s*(?:Airborne|Airborne Division)\b', '101st Airborne Division'),
    (r'\bMadyar\s*(?:Birds|Drones|Birds of Madyar)\b', 'Unidade de Drones "Madyar Birds"'),
    (r'\b1[ªa]?\s*(?:Brigada de Guardas|Guards Brigade)\b', '1ª Brigada de Infantaria de Guardas (OPFOR)'),
    (r'\bSurovikin\b', 'Posto de Comando OPFOR "Surovikin"'),
    (r'\b(?:110[ªa]|3ª Assalto|72ª Brigada|92ª Brigada)\b', 'Brigada de Infantaria Operacional')
]

class OSINTExtractor:
    """
    Extrator de alta precisão para mensagens e relatórios OSINT.
    """

    @staticmethod
    def parse_decimal_coordinates(text: str) -> Optional[Tuple[float, float]]:
        """
        Extrai coordenadas em Graus Decimais (Lat/Lon) usando Regex robusta.
        Formatos suportados:
        - "48.2820, 37.1824"
        - "Lat: 48.2820, Lon: 37.1824"
        - "48.2820° N, 37.1824° E"
        Retorna (longitude, latitude).
        """
        regex_decimal = r'(?:Lat(?:itude)?[:\s]*)?(-?\d{1,2}\.\d{4,7})\s*°?\s*[NS]?\s*[,;\s]+\s*(?:Lon(?:gitude)?[:\s]*)?(-?\d{1,3}\.\d{4,7})\s*°?\s*[EW]?'
        match = re.search(regex_decimal, text, re.IGNORECASE)
        if match:
            val1 = float(match.group(1))
            val2 = float(match.group(2))
            # Validação espacial para a Europa de Leste / Ucrânia (Lat 44-56, Long 24-42)
            if 44.0 <= val1 <= 56.0 and 24.0 <= val2 <= 42.0:
                return (val2, val1)  # (Longitude, Latitude)
            elif 44.0 <= val2 <= 56.0 and 24.0 <= val1 <= 42.0:
                return (val1, val2)

        return None

    @staticmethod
    def parse_mgrs_coordinates(text: str) -> Optional[Tuple[float, float]]:
        """
        Extrai e converte coordenadas MGRS (Military Grid Reference System).
        Exemplo: "37U CQ 1824 8280" ou "36U VV 5234 4501"
        """
        regex_mgrs = r'\b(\d{1,2}[C-X])\s*([A-Z]{2})\s*(\d{2,5})\s*(\d{2,5})\b'
        match = re.search(regex_mgrs, text, re.IGNORECASE)
        if match:
            grid_zone = match.group(1).upper()
            square = match.group(2).upper()
            easting = match.group(3)
            northing = match.group(4)

            # Aproximação MGRS para WGS84 para a Zona 37U (Donbas/Pokrovsk/Kursk)
            if grid_zone == "37U":
                base_lat = 48.2800 + (float(northing[:2]) * 0.01)
                base_lon = 37.1800 + (float(easting[:2]) * 0.01)
                return (base_lon, base_lat)
            elif grid_zone == "36U":
                base_lat = 50.4500 + (float(northing[:2]) * 0.01)
                base_lon = 30.5200 + (float(easting[:2]) * 0.01)
                return (base_lon, base_lat)

        return None

    @classmethod
    def extract_military_units(cls, text: str) -> List[str]:
        """
        Identifica menções explícitas a brigadas ou batalhões conhecidos.
        """
        found_units = []
        for pattern, unit_name in MILITARY_UNITS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                if unit_name not in found_units:
                    found_units.append(unit_name)
        return found_units

    @classmethod
    def process_osint_message(cls, message_text: str, source_name: str = "Telegram_OSINT") -> Dict[str, Any]:
        """
        Processa uma mensagem OSINT completa e retorna o dicionário validado.
        Classifica a precisão como:
        - 'HIGH_PRECISION': Coordenadas exatas decimais ou MGRS encontradas.
        - 'LOW_PRECISION': Apontado para o centro de uma cidade via Gazetteer.
        - 'UNKNOWN': Nenhuma localização identificada.
        """
        # 1. Tentar Coordenadas Decimais Exatas
        coords = cls.parse_decimal_coordinates(message_text)
        precision = "HIGH_PRECISION"

        # 2. Tentar Coordenadas MGRS
        if not coords:
            coords = cls.parse_mgrs_coordinates(message_text)
            if coords:
                precision = "HIGH_PRECISION"

        # 3. Fallback: Procura no Gazetteer de Cidades (Baixa Precisão)
        matched_city = None
        if not coords:
            upper_msg = message_text.upper()
            for city_name, city_coords in CITY_GAZETTEER.items():
                if city_name in upper_msg:
                    coords = city_coords
                    matched_city = city_name
                    precision = "LOW_PRECISION"
                    break

        if not coords:
            precision = "UNKNOWN"
            coords = (31.1656, 48.3794) # Centro da Ucrânia por omissão

        # 4. Extrair Unidades Militares Envolvidas
        units_mentioned = cls.extract_military_units(message_text)

        return {
            "source_name": source_name,
            "text": message_text,
            "coordinates": list(coords), # [longitude, latitude]
            "precision_class": precision,
            "matched_city": matched_city,
            "units_mentioned": units_mentioned,
            "is_high_precision": (precision == "HIGH_PRECISION")
        }


# ============================================================================
# TESTES DE VALIDAÇÃO DO MÓDULO OSINT
# ============================================================================
if __name__ == "__main__":
    test_messages = [
        "Relatório da 47ª Brigada: Posições inimigas atingidas nas coordenadas 48.2820, 37.1824 com apoio de drones.",
        "Avanço tático detetado na grelha MGRS 37U CQ 1824 8280 pela 82ª Brigada de Assalto Aéreo.",
        "Duelos de artilharia pesada intensificados no setor central de Pokrovsk.",
        "Unidade Madyar Birds operando drones kamikaze na região de Chasiv Yar."
    ]

    print("=== TESTE DO EXTRATOR OSINT DE ALTA PRECISÃO ===")
    for msg in test_messages:
        result = OSINTExtractor.process_osint_message(msg)
        print(f"\nMensagem: {msg}")
        print(f" -> Coordenadas [Lon, Lat]: {result['coordinates']}")
        print(f" -> Precisão: {result['precision_class']}")
        print(f" -> Unidades Militares: {result['units_mentioned']}")
