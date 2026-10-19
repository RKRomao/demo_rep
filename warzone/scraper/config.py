import os

SCRAPER_INTERVAL_SECONDS = 300  # 5 minutos
LIVEUAMAP_URL = "https://ukraine.liveuamap.com/"
NASA_FIRMS_CSV_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"

# MariaDB / Database credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "warzone_gis")
