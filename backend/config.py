"""Configuración central. Todo valor sensible o dependiente del entorno se lee del .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _path(name: str, default: str) -> Path:
    p = Path(os.getenv(name, default))
    return p if p.is_absolute() else ROOT / p


APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

DB_PATH = _path("DB_PATH", "data/mh_builder.sqlite3")
CACHE_DIR = _path("CACHE_DIR", "data/cache")
IMAGES_DIR = _path("IMAGES_DIR", "data/images")
FRONTEND_DIR = ROOT / "frontend"

USER_AGENT = os.getenv("SCRAPER_USER_AGENT", "mh-builder-web/1.0")
SCRAPER_DELAY = float(os.getenv("SCRAPER_DELAY_SECONDS", "0.5"))
CACHE_HOURS = float(os.getenv("SCRAPER_CACHE_HOURS", "168"))

WORLD_DATA_REPO_URL = os.getenv("WORLD_DATA_REPO_URL", "").rstrip("/")
WORLD_API_URL = os.getenv("WORLD_API_URL", "").rstrip("/")
WILDS_API_URL = os.getenv("WILDS_API_URL", "").rstrip("/")
RISE_SITE_URL = os.getenv("RISE_SITE_URL", "").rstrip("/")
WORLD_KIRANICO_URL = os.getenv("WORLD_KIRANICO_URL", "https://mhworld.kiranico.com").rstrip("/")
WILDS_KIRANICO_URL = os.getenv("WILDS_KIRANICO_URL", "https://mhwilds.kiranico.com").rstrip("/")
