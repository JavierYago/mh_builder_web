"""Enriquecimiento de imágenes para el equipo que no las trae de su fuente principal.

* World + Iceborne (armas): render de cada arma en mhworld.kiranico.com.
  La ficha usa la ruta images/wp/factory/<carpeta del tipo>/<id>.jpg, con el id del enlace del listado.
* Wilds (armas y armaduras): miniaturas de mhwilds.kiranico.com.
Las armaduras de Iceborne no tienen imágenes públicas por pieza: el frontend usa el icono del
tipo de pieza coloreado por rareza, igual que hacen los menús del juego.
"""
import re

from bs4 import BeautifulSoup

from .. import config
from .http import fetch_text
from .world import norm

WORLD_TYPES = ["great-sword", "sword-and-shield", "dual-blades", "long-sword", "hammer", "hunting-horn", "lance",
               "gunlance", "switch-axe", "charge-blade", "insect-glaive", "bow", "heavy-bowgun", "light-bowgun"]
WORLD_FOLDERS = {"great-sword": "two", "sword-and-shield": "one", "dual-blades": "sou", "long-sword": "swo",
                 "hammer": "ham", "hunting-horn": "hue", "lance": "lan", "gunlance": "gun", "switch-axe": "saxe",
                 "charge-blade": "caxe", "insect-glaive": "rod", "bow": "bow", "heavy-bowgun": "hbg",
                 "light-bowgun": "lbg"}
WORLD_CDN = "https://cdn.kiranico.net/file/kiranico/mhworld-web/images/wp/factory"


def _key(name: str) -> str:
    return norm(re.sub(r"\(\s*MR\s*\)", "", name))


def world_weapons(conn) -> int:
    base = config.WORLD_KIRANICO_URL
    found: dict[tuple[str, str], str] = {}
    for idx, wtype in enumerate(WORLD_TYPES):
        html = fetch_text(f"{base}/en/weapons?type={idx}")
        for wid, _slug, name in re.findall(
                r'href="https://mhworld\.kiranico\.com/en/weapons/([^/"]+)/([^"]+)"[^>]*>\s*([^<]+?)\s*<', html):
            found.setdefault((wtype, _key(name)), f"{WORLD_CDN}/{WORLD_FOLDERS[wtype]}/{wid}.jpg")
    n = 0
    for row in conn.execute("SELECT id, name, weapon_type_id FROM weapons WHERE game_id='world'").fetchall():
        url = found.get((row["weapon_type_id"], _key(row["name"])))
        if url:
            conn.execute("UPDATE weapons SET image_url=?, image_local=NULL WHERE id=?", (url, row["id"]))
            n += 1
    return n


def _unescape(payload: str) -> str:
    return payload.replace('\\"', '"').replace("\\\\", "\\")


def wilds(conn) -> tuple[int, int]:
    base = config.WILDS_KIRANICO_URL
    # Armas: la lista completa va en el payload de la página (todas las pestañas).
    page = _unescape(fetch_text(f"{base}/data/weapons"))
    weapons = {}
    for m in re.finditer(r'(https://mhwilds\.kiranico\.net/tex_thumbnail/it\d+_\d+\.webp)', page):
        tail = page[m.end():m.end() + 2500]
        nm = re.search(r'"children":\{"ja":"[^"]*","en":"([^"]+)"', tail) or re.search(r'<span>([^<]+)</span>', tail)
        if nm:
            weapons.setdefault(nm.group(1), m.group(1))
    nw = 0
    for row in conn.execute("SELECT id, name FROM weapons WHERE game_id='wilds'").fetchall():
        if row["name"] in weapons:
            conn.execute("UPDATE weapons SET image_url=?, image_local=NULL WHERE id=?", (weapons[row["name"]], row["id"]))
            nw += 1

    # Armaduras: cada serie tiene 5 miniaturas (casco..piernas); las variantes α/β/γ comparten modelo.
    soup = BeautifulSoup(fetch_text(f"{base}/data/armor-series"), "html.parser")
    series: dict[str, list] = {}
    for tr in soup.find_all("tr"):
        a = tr.find("a", href=re.compile(r"/data/armor-series/"))
        if not a:
            continue
        tds = tr.find_all("td")
        idx = next(i for i, td in enumerate(tds) if td.find("a") is a or a in td.descendants)
        imgs = []
        for td in tds[idx + 1: idx + 6]:
            img = td.find("img")
            imgs.append(img["src"] if img and "tex_thumbnail" in img.get("src", "") else None)
        series.setdefault(_series_key(a.get_text(strip=True)), imgs)
    kinds = ["head", "chest", "arms", "waist", "legs"]
    na = 0
    rows = conn.execute("SELECT p.id, p.kind, s.name AS set_name FROM armor_pieces p JOIN armor_sets s ON s.id=p.set_id "
                        "WHERE p.game_id='wilds'").fetchall()
    for row in rows:
        imgs = series.get(_series_key(row["set_name"]))
        if imgs and row["kind"] in kinds:
            url = imgs[kinds.index(row["kind"])]
            if url:
                conn.execute("UPDATE armor_pieces SET image_url=?, image_local=NULL WHERE id=?", (url, row["id"]))
                na += 1
    return nw, na


def _series_key(name: str) -> str:
    return re.sub(r"[\sαβγ]+$", "", name).strip().lower()


def enrich(conn, games) -> None:
    if "world" in games:
        print(f"  [imágenes] World: {world_weapons(conn)} armas")
    if "wilds" in games:
        nw, na = wilds(conn)
        print(f"  [imágenes] Wilds: {nw} armas, {na} piezas de armadura")
    conn.commit()
