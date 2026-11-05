"""Valida y guarda en local todas las imágenes de armas y armaduras.

Para cada URL:
  * Se descarga (con reintentos ante límites del CDN) y se comprueba con Pillow que se abre y
    que tiene contenido visible (no es transparente ni de un único color).
  * Si es válida se guarda en IMAGES_DIR y se rellena image_local: la web sirve la imagen desde
    nuestro servidor y no depende de enlaces externos (que pueden fallar o estar limitados).
  * Si falla, se prueba la variante masculina/femenina de la armadura.
  * Renders 4K de World: solo se comprueba que existan; /thumb genera la miniatura local.
Lo que no tiene ninguna imagen válida queda sin imagen y el frontend muestra la silueta por rareza.
"""
import hashlib
import io
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image

from .. import config
from ..thumbs import allowed as is_heavy

_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT
UNKNOWN = "unknown"  # error de red persistente: no se toca la imagen


def _visible(data: bytes) -> bool:
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:  # noqa: BLE001
        return False
    im = im.convert("RGBA")
    if im.width < 8 or im.height < 8:
        return False
    alpha = im.getchannel("A")
    if alpha.getbbox() is None:
        return False
    if sum(alpha.histogram()[32:]) / (im.width * im.height) < 0.03:
        return False
    rgb = im.convert("RGB").resize((32, 32))
    return max(hi - lo for lo, hi in rgb.getextrema()) > 24


def local_name(url: str) -> str:
    ext = url.rsplit(".", 1)[-1].split("?")[0].lower()
    ext = ext if ext in ("png", "webp", "jpg", "jpeg", "gif") else "img"
    return hashlib.sha1(url.encode()).hexdigest()[:24] + "." + ext


def check(url: str):
    """-> True (válida y guardada), False (no existe / vacía) o UNKNOWN (error de red)."""
    dest = config.IMAGES_DIR / local_name(url)
    if not is_heavy(url) and dest.exists():
        return True
    for attempt in range(4):
        try:
            if is_heavy(url):
                code = _session.head(url, timeout=30).status_code
                if code == 200:
                    return True
                if code in (403, 404, 410):
                    return False
            else:
                resp = _session.get(url, timeout=30)
                if resp.status_code == 200:
                    if not _visible(resp.content):
                        return False
                    dest.write_bytes(resp.content)
                    return True
                if resp.status_code in (403, 404, 410):
                    return False
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return UNKNOWN


def _alt(url: str) -> list[str]:
    if url and url.endswith("_m.webp"):
        return [url[:-7] + "_f.webp"]
    if url and url.endswith("_f.webp"):
        return [url[:-7] + "_m.webp"]
    return []


def run(conn, games=("world", "rise", "wilds")) -> dict:
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    marks = ",".join("?" * len(games))
    rows = [("weapons", r["id"], r["image_url"], None) for r in conn.execute(
        f"SELECT id, image_url FROM weapons WHERE game_id IN ({marks}) AND image_url IS NOT NULL", games)]
    rows += [("armor_pieces", r["id"], r["image_url"], r["image_url_f"]) for r in conn.execute(
        f"SELECT id, image_url, image_url_f FROM armor_pieces WHERE game_id IN ({marks}) "
        "AND (image_url IS NOT NULL OR image_url_f IS NOT NULL)", games)]
    urls = {u for _, _, a, b in rows for u in (a, b, *_alt(a), *_alt(b)) if u}
    with ThreadPoolExecutor(max_workers=8) as pool:
        ok = dict(zip(urls, pool.map(check, urls)))
    stats = {"ok": 0, "alternativa": 0, "sin_imagen": 0, "error_red": 0}
    for table, rid, url, url_f in rows:
        res = ok.get(url)
        if res is UNKNOWN:
            stats["error_red"] += 1
            continue
        chosen = url if res is True else next((u for u in [url_f, *_alt(url)] if u and ok.get(u) is True), None)
        local = None if (chosen is None or is_heavy(chosen)) else local_name(chosen)
        conn.execute(f"UPDATE {table} SET image_url=?, image_local=? WHERE id=?", (chosen, local, rid))
        stats["ok" if chosen == url else "alternativa" if chosen else "sin_imagen"] += 1
    conn.commit()
    return stats
