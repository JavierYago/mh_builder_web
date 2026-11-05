"""Cliente HTTP educado: caché en disco, retardo entre peticiones y reintentos."""
import hashlib
import json
import time

import requests

from .. import config

_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT
_last_request = 0.0


def _cache_path(url: str):
    key = hashlib.sha1(url.encode()).hexdigest()
    return config.CACHE_DIR / key[:2] / key


def fetch(url: str, *, use_cache: bool = True) -> bytes:
    global _last_request
    path = _cache_path(url)
    if use_cache and path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < config.CACHE_HOURS:
            return path.read_bytes()
    for attempt in range(4):
        wait = config.SCRAPER_DELAY - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()
        try:
            resp = _session.get(url, timeout=90)
            if resp.status_code == 200:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(resp.content)
                return resp.content
            if resp.status_code in (404, 403):
                resp.raise_for_status()
        except requests.RequestException as exc:  # reintento con espera creciente
            if attempt == 3:
                raise RuntimeError(f"No se pudo descargar {url}: {exc}") from exc
        time.sleep(2 ** attempt)
    raise RuntimeError(f"No se pudo descargar {url}")


def fetch_json(url: str):
    return json.loads(fetch(url))


def fetch_text(url: str) -> str:
    return fetch(url).decode("utf8", "replace")
