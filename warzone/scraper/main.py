"""
WARZONE OSINT PYTHON SCRAPER WORKER
===================================
Loop contínuo de varredura autónoma de fontes OSINT e Satélite (NASA FIRMS).
Salva e atualiza dados dinâmicos reais diretamente na base de dados MariaDB.
"""
import os
import time
import asyncio
import pymysql
from datetime import datetime
from firms_ingestor import NASAirmsIngestor
from fusion_engine import TacticalDataFusionEngine
from cleaners.geocoding import extract_coordinates_from_text
from xml.etree import ElementTree as ET
import aiohttp

# Configurações do MariaDB
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "warzone_db")
SCRAPER_INTERVAL = int(os.getenv("SCRAPER_INTERVAL_SECONDS", 300))

def get_db_connection():
    try:
        return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"[DB] Erro de conexão com MariaDB ({DB_HOST}:{DB_PORT}): {e}")
        return None

def save_events_to_mariadb(events):
    conn = get_db_connection()
    if not conn:
        print("[DB] Ignorando persistência neste ciclo (MariaDB indisponível).")
        return 0

    inserted_count = 0
    try:
        with conn.cursor() as cursor:
            for ev in events:
                try:
                    lon, lat = ev["coordinates"][0], ev["coordinates"][1]
                    wkt_point = f"POINT({lon} {lat})"
                    sql = """
                    INSERT INTO osint_events (
                        source_name, external_id, category, title, description,
                        event_timestamp, location, reliability_score, verified
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s), %s, %s
                    ) ON DUPLICATE KEY UPDATE
                        title=VALUES(title),
                        description=VALUES(description),
                        reliability_score=VALUES(reliability_score);
                    """
                    raw_ts = ev.get("timestamp") or ev.get("event_timestamp")
                    if isinstance(raw_ts, datetime):
                        ts_str = raw_ts.strftime("%Y-%m-%d %H:%M:%S")
                    elif isinstance(raw_ts, str):
                        ts_str = raw_ts
                    else:
                        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    cursor.execute(sql, (
                        ev.get("source_name", "NASA_FIRMS"),
                        ev.get("external_id", f"firm_{lon}_{lat}_{time.time()}"),
                        ev.get("category", "SHELLING"),
                        ev.get("title", "Anomalia Térmica de Combate"),
                        ev.get("description", "Deteção espacial por satélite"),
                        ts_str,
                        wkt_point,
                        ev.get("reliability_score", 5),
                        1 if ev.get("verified", True) else 0
                    ))
                    inserted_count += 1
                except Exception as err:
                    print(f"[DB Save Error]: {err}")
                    continue
            conn.commit()
    finally:
        conn.close()
    return inserted_count

async def fetch_live_osint_news() -> list:
    """
    Scraper dinâmico de feeds RSS de notícias militares reais em tempo real (sem dados hardcoded).
    """
    rss_urls = [
        "https://www.ukrinform.net/rss/block/lastnews",
        "https://defense-blog.com/feed/"
    ]
    events = []
    headers = {"User-Agent": "Mozilla/5.0 (WARZONE OSINT Intelligence Bot)"}

    async with aiohttp.ClientSession(headers=headers) as session:
        for url in rss_urls:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        root = ET.fromstring(content)
                        for item in root.findall(".//item"):
                            title = item.findtext("title") or ""
                            desc = item.findtext("description") or ""
                            
                            # Extração dinâmica de coordenadas WGS84 do texto do artigo via Geocoder
                            coords = extract_coordinates_from_text(f"{title} {desc}")
                            if coords:
                                lon, lat = coords
                                events.append({
                                    "source_name": "RSS_OSINT_LIVE",
                                    "external_id": f"rss_{abs(hash(title))}",
                                    "category": "GROUND_COMBAT",
                                    "title": title[:255],
                                    "description": desc[:500],
                                    "timestamp": datetime.now(),
                                    "coordinates": [lon, lat],
                                    "reliability_score": 4,
                                    "verified": True
                                })
            except Exception as e:
                print(f"[RSS Scraper] Aviso ao consultar {url}: {e}")
                continue
    return events

async def run_scraper_loop():
    print("WARZONE OSINT PYTHON SCRAPER WORKER INICIADO")
    print(f"-> MariaDB Target: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"-> Intervalo de varredura: {SCRAPER_INTERVAL} segundos")

    ingestor = NASAirmsIngestor()
    fusion_engine = TacticalDataFusionEngine()

    while True:
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{timestamp_str}] A iniciar recolha de telemetria satélite & OSINT...")

        # 1. Recolha da NASA FIRMS em tempo real (14 dias / 2 semanas)
        firms_anomalies = await ingestor.fetch_thermal_anomalies(days=14)
        print(f"-> NASA FIRMS: {len(firms_anomalies)} anomalias térmicas espaciais capturadas (14 Dias).")

        # 2. Feeds OSINT reais recolhidos dinamicamente de RSS
        live_news = await fetch_live_osint_news()
        print(f"-> Feeds RSS OSINT: {len(live_news)} notícias com geolocalização capturadas.")

        # 3. Executar Fusão e Triangulação Tática (Satélite + Terrestre)
        fused_events = fusion_engine.fuse_intel_sources(firms_anomalies, live_news)
        print(f"-> Fusão Tática: {len(fused_events)} eventos consolidados.")

        # 4. Guardar na MariaDB
        saved = save_events_to_mariadb(fused_events)
        print(f"{saved} eventos sincronizados com sucesso na MariaDB!")

        print(f"A aguardar {SCRAPER_INTERVAL}s até ao próximo ciclo...")
        await asyncio.sleep(SCRAPER_INTERVAL)

if __name__ == "__main__":
    asyncio.run(run_scraper_loop())
