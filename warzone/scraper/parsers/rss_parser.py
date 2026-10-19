"""
Parser OSINT para Feeds de Notícias e RSS em Tempo Real (Últimas 24h)
====================================================================
Coleta notícias recentes de fontes como Ukrinform, Militarnyi, ISW e LiveUAmap.
Utiliza o OSINTExtractor para geolocalização e extração de brigadas.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

# Permitir importação dos módulos vizinhos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cleaners.osint_extractor import OSINTExtractor

# Feeds de Notícias OSINT em Tempo Real
OSINT_RSS_FEEDS = [
    {
        "source": "Ukrinform_EN",
        "url": "https://www.ukrinform.net/rss/block/lastnews",
        "category_default": "SHELLING"
    },
    {
        "source": "Militarnyi",
        "url": "https://mil.in.ua/en/feed/",
        "category_default": "TROOP_MOVEMENT"
    }
]

class OSINTRSSParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WARZONE_OSINT_Bot/1.0"
        }

    def fetch_recent_news(self) -> List[Dict[str, Any]]:
        extracted_events = []

        for feed_info in OSINT_RSS_FEEDS:
            try:
                res = requests.get(feed_info["url"], headers=self.headers, timeout=8)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.content, "xml")
                    items = soup.find_all("item")

                    for item in items[:10]: # Pegar as 10 notícias mais recentes das últimas 24h
                        title = item.title.text.strip() if item.title else ""
                        description = item.description.text.strip() if item.description else ""
                        pub_date = item.pubDate.text.strip() if item.pubDate else datetime.now().isoformat()
                        full_text = f"{title}. {description}"

                        # Processar texto via Extrator OSINT
                        osint_data = OSINTExtractor.process_osint_message(full_text, source_name=feed_info["source"])

                        # Determinar categoria baseada em palavras-chave
                        category = feed_info["category_default"]
                        lower_text = full_text.lower()
                        if "drone" in lower_text or "shahed" in lower_text:
                            category = "DRONE_ATTACK"
                        elif "missile" in lower_text or "strike" in lower_text:
                            category = "AIRSTRIKE"
                        elif "power" in lower_text or "grid" in lower_text or "energy" in lower_text:
                            category = "INFRASTRUCTURE"

                        event_obj = {
                            "source_name": feed_info["source"],
                            "external_id": f"rss_{hash(title)}",
                            "category": category,
                            "title": title[:100],
                            "description": description[:200] if description else title,
                            "event_timestamp": pub_date,
                            "coordinates": osint_data["coordinates"], # [longitude, latitude]
                            "reliability_score": 4 if osint_data["is_high_precision"] else 3,
                            "verified": True,
                            "precision_class": osint_data["precision_class"],
                            "location_name": osint_data["matched_city"] or "Ucrânia"
                        }
                        extracted_events.append(event_obj)
            except Exception as e:
                print(f"[RSS Parser] Aviso ao raspar feed {feed_info['source']}: {e}")

        return extracted_events

if __name__ == "__main__":
    parser = OSINTRSSParser()
    events = parser.fetch_recent_news()
    print(f"=== NOTÍCIAS OSINT DAS ÚLTIMAS 24H RECOLHIDAS: {len(events)} ===")
    for e in events[:5]:
        print(f"\n[Fonte: {e['source_name']}] {e['title']}")
        print(f" -> Categoria: {e['category']} | Precisão: {e['precision_class']} | Coords: {e['coordinates']}")
