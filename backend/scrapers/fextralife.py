"""Relleno de imágenes de armadura desde los wikis de Fextralife.

Se usa SOLO para las piezas que siguen sin imagen válida tras validate_images (sobre todo
Iceborne, que no tiene imágenes por pieza en ninguna otra fuente). Fextralife publica un render
del set completo (modelo masculino y femenino sobre fondo blanco); de él se recorta la zona de
cada pieza del modelo masculino: cabeza -> casco, torso -> peto, etc.
"""
import io
import re

import requests
from PIL import Image, ImageDraw

from .. import config
from .validate_images import local_name

WIKIS = {"world": "monsterhunterworld", "rise": "monsterhunterrise", "wilds": "monsterhunterwilds"}
_session = requests.Session()
_session.headers["User-Agent"] = "Mozilla/5.0 (compatible; mh-builder-web/1.0)"

# Zona de cada pieza dentro del modelo (fracciones de x0, y0, x1, y1).
REGIONS = {"head": (0.12, 0.0, 0.88, 0.27), "chest": (0.0, 0.14, 1.0, 0.5), "arms": (0.0, 0.24, 0.6, 0.62),
           "waist": (0.08, 0.4, 0.92, 0.68), "legs": (0.1, 0.58, 0.9, 1.0)}
SIZE = 128


def key(name: str) -> str:
    n = name.lower().replace("α", " alpha ").replace("β", " beta ").replace("γ", " gamma ").replace("+", " plus ")
    words = [w for w in re.findall(r"[a-z0-9]+", n) if w not in ("armor", "set", "the")]
    return " ".join(words)


def _get(url: str):
    try:
        r = _session.get(url, timeout=40)
        return r if r.status_code == 200 else None
    except requests.RequestException:
        return None


def set_links(game: str) -> dict[str, str]:
    site = WIKIS[game]
    r = _get(f"https://{site}.wiki.fextralife.com/Armor")
    if not r:
        return {}
    out = {}
    for link in set(re.findall(r'href="/([^"#?:]+)"', r.text)):
        if re.search(r"(Set|Armor_Set)$", link):
            out.setdefault(key(requests.utils.unquote(link).replace("_", " ")), f"https://{site}.wiki.fextralife.com/{link}")
    return out


def set_image(page_url: str, site: str) -> str | None:
    """Primera imagen de contenido de la página (el render del set), descartando iconos."""
    r = _get(page_url)
    if not r:
        return None
    for src in re.findall(r'<img[^>]+src="([^"]+)"', r.text):
        low = src.lower()
        if f"/file/{site}/" not in low or any(x in low for x in ("icon", "logo", "_s.png", "gem_level", "slot")):
            continue
        px = re.search(r"/(\d+)px-", low)
        if px and int(px.group(1)) < 150:
            continue
        if low.split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            return src if src.startswith("http") else "https:" + src
    return None


def _male_figure(im: Image.Image) -> Image.Image:
    src = im.convert("RGBA")  # algunas imágenes ya traen transparencia: se aplana sobre blanco
    im = Image.new("RGBA", src.size, (255, 255, 255, 255))
    im.alpha_composite(src)
    im = im.convert("RGB")
    w, h = im.size
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(im, corner, (255, 0, 255), thresh=40)
    rgba = im.convert("RGBA")
    px = rgba.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][:3] == (255, 0, 255):
                px[x, y] = (0, 0, 0, 0)
    alpha = rgba.getchannel("A")
    cols = [sum(1 for y in range(0, h, 2) if alpha.getpixel((x, y)) > 0) for x in range(w)]
    mid = range(int(w * 0.35), int(w * 0.65))
    gap = min(mid, key=lambda x: cols[x]) if mid else w // 2
    left = rgba.crop((0, 0, gap, h))
    box = left.getchannel("A").getbbox()
    return left.crop(box) if box else left


def piece_crop(fig: Image.Image, kind: str) -> Image.Image:
    fw, fh = fig.size
    x0, y0, x1, y1 = REGIONS[kind]
    part = fig.crop((int(fw * x0), int(fh * y0), int(fw * x1), int(fh * y1)))
    box = part.getchannel("A").getbbox()
    if box:
        part = part.crop(box)
    side = max(part.size) + 6
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(part, ((side - part.width) // 2, (side - part.height) // 2))
    return square.resize((SIZE, SIZE), Image.LANCZOS)


def _rise_series_keys(pieces: list[str]) -> list[str]:
    """Rise: 'Aelucanth Vertex S' + 'Aelucanth Thorax S' -> 'aelucanth s'."""
    words = [p.split() for p in pieces]
    prefix = []
    for parts in zip(*words):
        if all(x == parts[0] for x in parts):
            prefix.append(parts[0])
        else:
            break
    suffix = words[0][-1] if all(w[-1] == words[0][-1] for w in words) and words[0][-1] in ("S", "X") else ""
    base = " ".join(prefix or words[0][:1])
    return [key(f"{base} {suffix}"), key(base)]


def fill(conn, game: str) -> int:
    links = set_links(game)
    if not links:
        return 0
    site = WIKIS[game]
    rows = conn.execute("SELECT p.id, p.kind, p.name, p.set_id, s.name AS set_name FROM armor_pieces p "
                        "LEFT JOIN armor_sets s ON s.id=p.set_id WHERE p.game_id=? AND p.image_local IS NULL",
                        (game,)).fetchall()
    by_set: dict = {}
    for r in rows:
        by_set.setdefault(r["set_id"], []).append(r)
    done = 0
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for _sid, pieces in by_set.items():
        all_names = [r["name"] for r in conn.execute("SELECT name FROM armor_pieces WHERE set_id=?", (_sid,))]
        cands = [key(pieces[0]["set_name"] or "")] + (_rise_series_keys(all_names) if game == "rise" else [])
        page = next((links[c] for c in cands if c in links), None)
        img_url = set_image(page, site) if page else None
        if not img_url:  # no está en el índice: se prueba la URL directa del set
            base = (pieces[0]["set_name"] or "").replace("α", "Alpha").replace("β", "Beta").replace("γ", "Gamma")
            base = re.sub(r"\+", " Plus", base).strip().replace(" ", "_")
            for suffix in ("_Set", "_Armor_Set", "_Armor"):
                img_url = set_image(f"https://{site}.wiki.fextralife.com/{base}{suffix}", site)
                if img_url:
                    break
        resp = _get(img_url) if img_url else None
        if not resp:
            continue
        try:
            fig = _male_figure(Image.open(io.BytesIO(resp.content)))
        except Exception:  # noqa: BLE001
            continue
        for p in pieces:
            if p["kind"] not in REGIONS:
                continue
            ref = f"{img_url}#{p['kind']}"
            name = local_name(ref).rsplit(".", 1)[0] + ".webp"
            piece_crop(fig, p["kind"]).save(config.IMAGES_DIR / name, "WEBP", quality=85)
            conn.execute("UPDATE armor_pieces SET image_url=?, image_local=? WHERE id=?", (ref, name, p["id"]))
            done += 1
    conn.commit()
    return done


def _title_variants(name: str) -> list[str]:
    t = name.replace("α", "Alpha").replace("β", "Beta").replace("γ", "Gamma").replace("+", " Plus").strip()
    out = [t]
    if "/" in t:
        out += [t.replace("/", " "), t.replace("/", "_"), t.split("/")[0]]
    if '"' in t:
        out.append(re.sub(r"\s+", " ", t.replace('"', "")).strip())
    return list(dict.fromkeys(out))


def _page_image(site: str, name: str):
    """Primera imagen de contenido de la ficha del objeto -> (url, bytes) o None."""
    from .validate_images import _visible

    for title in _title_variants(name):
        url = f"https://{site}.wiki.fextralife.com/" + requests.utils.quote(title.replace(" ", "+"), safe="+")
        src = set_image(url, site)
        if not src:
            continue
        img = _get(src)
        if img and _visible(img.content):
            return src, img.content
    return None


def _fill(conn, game: str, table: str, where: str) -> int:
    site = WIKIS[game]
    rows = conn.execute(f"SELECT id, name FROM {table} WHERE game_id=? AND {where}", (game,)).fetchall()
    done = 0
    for r in rows:
        found = _page_image(site, r["name"])
        if not found:
            continue
        src, data = found
        name = local_name(src)
        (config.IMAGES_DIR / name).write_bytes(data)
        conn.execute(f"UPDATE {table} SET image_url=?, image_local=? WHERE id=?", (src, name, r["id"]))
        done += 1
    conn.commit()
    return done


def fill_weapons(conn, game: str) -> int:
    """Armas sin imagen válida: ficha del arma en el wiki."""
    return _fill(conn, game, "weapons", "image_local IS NULL AND (image_url IS NULL OR image_url NOT LIKE '%/wp/factory/%')")


def fill_piece_pages(conn, game: str) -> int:
    """Último recurso para armaduras: ficha individual de la pieza en el wiki."""
    return _fill(conn, game, "armor_pieces", "image_local IS NULL")
