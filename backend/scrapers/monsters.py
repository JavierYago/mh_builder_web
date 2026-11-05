"""Monstruos de cada juego: zonas de golpe, debilidades, amenazas, rangos e icono.

* World + Iceborne: MHWorldData (hitzones, debilidades, ailments, recompensas por rango) + icono de Kiranico.
* Rise + Sunbreak: Kiranico (tabla de fisiología, eficacia de estados, recompensas por rango).
* Wilds: API mhdb (partes con multiplicadores, debilidades, recompensas por rango) + icono de Kiranico.
Amenazas: de los datos de World cuando existen; si no, tabla propia (monster_threats.CURATED).
"""
import csv
import io
import json
import re
from statistics import mean

from bs4 import BeautifulSoup

from .. import config
from ..monster_threats import CURATED
from . import validate_images
from .http import fetch_json, fetch_text

ELEMENTS = ["fire", "water", "thunder", "ice", "dragon"]
WORLD_THREAT_COLS = {"roar": "roar", "wind": "wind", "tremor": "tremor", "fireblight": "fireblight",
                     "waterblight": "waterblight", "thunderblight": "thunderblight", "iceblight": "iceblight",
                     "dragonblight": "dragonblight", "blastblight": "blastblight", "poison": "poison",
                     "sleep": "sleep", "paralysis": "paralysis", "bleed": "bleed", "stun": "stun"}


def _csv(name):
    return list(csv.DictReader(io.StringIO(fetch_text(f"{config.WORLD_DATA_REPO_URL}/monsters/{name}.csv"))))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _world_threats() -> dict[str, list[str]]:
    out = {}
    for r in _csv("monster_ailments"):
        out[r["base_name_en"]] = [code for col, code in WORLD_THREAT_COLS.items() if r.get(col)]
    return out


def _threats(name: str, world: dict) -> tuple[list[str], str]:
    if name in world and world[name]:
        return world[name], "datos"
    base = re.sub(r"^(Apex|Risen|Guardian|Scorned|Violet|Chaotic|Lucent|Furious|Flaming|Magma|Aurora|Primordial) ", "", name)
    if name in CURATED:
        return CURATED[name], "estimado"
    if base in world and world[base]:
        return world[base], "datos"
    return CURATED.get(base, ["roar"]), "estimado"


def _elem_stars(hz_rows) -> dict[str, int]:
    """Estrellas de debilidad elemental a partir de las zonas de golpe (media de las 3 mejores)."""
    out = {}
    for e in ELEMENTS:
        vals = sorted((r[e] or 0 for r in hz_rows), reverse=True)[:3]
        v = mean(vals) if vals else 0
        out[e] = 3 if v >= 25 else 2 if v >= 15 else 1 if v >= 10 else 0
    return out


def _save_icon(conn, mid, url):
    if url and validate_images.check(url) is True:
        conn.execute("UPDATE monsters SET icon_local=? WHERE id=?", (validate_images.local_name(url), mid))
        return
    # Respaldo: imagen de la ficha del monstruo en el wiki de Fextralife.
    from . import fextralife
    game, name = conn.execute("SELECT game_id, name FROM monsters WHERE id=?", (mid,)).fetchone()
    found = fextralife._page_image(fextralife.WIKIS[game], name)
    if found:
        src, data = found
        local = validate_images.local_name(src)
        (config.IMAGES_DIR / local).write_bytes(data)
        conn.execute("UPDATE monsters SET icon_url=?, icon_local=? WHERE id=?", (src, local, mid))


def _insert(conn, game, data, hitzones, weaknesses):
    cur = conn.execute(
        "INSERT INTO monsters(game_id,source_id,name,name_es,species,ranks,threats,threats_source,icon_url) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (game, data.get("source_id"), data["name"], data.get("name_es"), data.get("species"),
         json.dumps(data["ranks"]), json.dumps(data["threats"]), data["threats_source"], data.get("icon")))
    mid = cur.lastrowid
    for h in hitzones:
        conn.execute("INSERT INTO monster_hitzones(monster_id,part,cut,impact,shot,fire,water,thunder,ice,dragon,stun) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (mid, h["part"], h["cut"], h["impact"], h["shot"], h["fire"], h["water"], h["thunder"],
                      h["ice"], h["dragon"], h.get("stun")))
    for (kind, name), stars in weaknesses.items():
        conn.execute("INSERT OR REPLACE INTO monster_weaknesses VALUES (?,?,?,?)", (mid, kind, name, int(stars)))
    _save_icon(conn, mid, data.get("icon"))
    return mid


def _wipe(conn, game):
    conn.execute("DELETE FROM monster_hitzones WHERE monster_id IN (SELECT id FROM monsters WHERE game_id=?)", (game,))
    conn.execute("DELETE FROM monster_weaknesses WHERE monster_id IN (SELECT id FROM monsters WHERE game_id=?)", (game,))
    conn.execute("DELETE FROM monsters WHERE game_id=?", (game,))


# --------------------------------------------------------------------------- World
def load_world(conn, world_threats) -> int:
    _wipe(conn, "world")
    es = {r["name_en"]: r.get("name_es") for r in _csv("monster_base_translations")}
    large = [r["name_en"] for r in _csv("monster_base") if r["size"] == "large"]
    hz = {}
    for r in _csv("monster_hitzones"):
        hz.setdefault(r["base_name_en"], []).append(dict(
            part=r["hitzone_en"], cut=_f(r["cut"]), impact=_f(r["impact"]), shot=_f(r["shot"]),
            **{e: _f(r[e]) for e in ELEMENTS}, stun=_f(r.get("ko"))))
    weak = {}
    for r in _csv("monster_weaknesses"):
        if r["form"] == "normal" or r["name_en"] not in weak:
            weak[r["name_en"]] = r
    ranks = {}
    for r in _csv("monster_rewards"):
        ranks.setdefault(r["base_name_en"], set()).add({"LR": "low", "HR": "high", "MR": "master"}.get(r["rank"]))
    icons = {}
    html = fetch_text(f"{config.WORLD_KIRANICO_URL}/en/monsters")
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        img = re.search(r'src="([^"]+em\d+[^"]*_ID\.png)"', row)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", row)).strip()
        if img:
            for name in large:
                if txt.startswith(name + " ") and (name not in icons or len(name) > 3):
                    icons.setdefault(name, img.group(1))
    n = 0
    for name in large:
        if name not in hz or not ranks.get(name):
            continue
        w = weak.get(name, {})
        stars = {("element", e): _f(w.get(e)) or 0 for e in ELEMENTS}
        stars.update({("status", s): _f(w.get(s)) or 0 for s in ("poison", "sleep", "paralysis", "blast", "stun")})
        threats, src = _threats(name, world_threats)
        _insert(conn, "world", dict(name=name, name_es=es.get(name), ranks=sorted(r for r in ranks[name] if r),
                                    threats=threats, threats_source=src, icon=icons.get(name)), hz[name], stars)
        n += 1
    return n


# --------------------------------------------------------------------------- Rise
RISE_STATUS = {"Poison": "poison", "Sleep": "sleep", "Paralysis": "paralysis", "Blast": "blast", "Stun": "stun"}


def load_rise(conn, world_threats) -> int:
    _wipe(conn, "rise")
    base = config.RISE_SITE_URL

    def listing(lang):
        prefix = "" if lang == "en" else f"/{lang}"
        soup = BeautifulSoup(fetch_text(f"{base}{prefix}/data/monsters?view=lg"), "html.parser")
        icons = {img["alt"]: img["src"].replace("http://", "https://")
                 for img in soup.find_all("img") if img.get("alt") and "/icons/em" in img.get("src", "")}
        out = {}
        for a in soup.find_all("a", href=re.compile(r"/data/monsters/\d+$")):
            name = a.get_text(strip=True)
            if name:
                out.setdefault(a["href"].rstrip("/").split("/")[-1], (name, icons.get(name)))
        return out

    en, es = listing("en"), listing("es")
    n = 0
    for mid, (name, icon) in en.items():
        soup = BeautifulSoup(fetch_text(f"{base}/data/monsters/{mid}"), "html.parser")
        tables = soup.find_all("table")
        if not tables:
            continue
        hitzones = []
        for tr in tables[0].find_all("tr")[1:]:
            c = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(c) < 11 or c[1] not in ("0", ""):
                continue
            v = [_f(x) for x in c[2:11]]
            hitzones.append(dict(part=c[0], cut=v[0], impact=v[1], shot=v[2], fire=v[3], water=v[4], ice=v[5],
                                 thunder=v[6], dragon=v[7], stun=v[8]))
        if not hitzones:
            continue
        ranks, status = set(), {}
        for tb in tables:
            heads = [th.get_text(strip=True) for th in tb.find_all("th")]
            if "Quest Rank" in heads:
                col = heads.index("Quest Rank")
                for tr in tb.find_all("tr")[1:]:
                    c = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(c) > col:
                        ranks.add({"Low Rank": "low", "High Rank": "high", "Master Rank": "master"}.get(c[col]))
            if heads[:2] == ["Ailment", "Buildup"]:
                for tr in tb.find_all("tr")[1:]:
                    c = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                    key = RISE_STATUS.get(c[0]) if c else None
                    first = re.match(r"\s*(\d+)", c[1]) if key and len(c) > 1 else None
                    if first:
                        b = int(first.group(1))
                        status[("status", key)] = 3 if b <= 150 else 2 if b <= 220 else 1
        ranks.discard(None)
        if not ranks:
            continue
        stars = {("element", e): s for e, s in _elem_stars(hitzones).items()}
        stars.update(status)
        threats, src = _threats(name, world_threats)
        _insert(conn, "rise", dict(source_id=mid, name=name, name_es=es.get(mid, (None,))[0], ranks=sorted(ranks),
                                   threats=threats, threats_source=src, icon=icon), hitzones, stars)
        n += 1
    return n


# --------------------------------------------------------------------------- Wilds
WILDS_STATUS = {"poison": "poison", "sleep": "sleep", "paralysis": "paralysis", "blastblight": "blast"}


def load_wilds(conn, world_threats) -> int:
    _wipe(conn, "wilds")
    en = fetch_json(f"{config.WILDS_API_URL}/en/monsters")
    es = {m["id"]: m.get("name") for m in fetch_json(f"{config.WILDS_API_URL}/es/monsters")}
    page = validate_images_unescape(fetch_text(f"{config.WILDS_KIRANICO_URL}/data/monsters"))
    icons = {}
    for m in re.finditer(r"(https://mhwilds\.kiranico\.net/em_icon/EM\d+_\d+_\d\.webp)", page):
        nm = re.search(r'"en":"(?!/)([^"]+)"', page[m.end():m.end() + 1500])
        if nm:
            icons.setdefault(nm.group(1), m.group(1))
    n = 0
    for m in en:
        if m.get("kind") != "large":
            continue
        hitzones = []
        for p in m.get("parts") or []:
            mu = p.get("multipliers") or {}
            pct = lambda k: round((mu.get(k) or 0) * 100, 1)  # noqa: E731
            hitzones.append(dict(part=p.get("name") or p.get("kind"), cut=pct("slash"), impact=pct("blunt"),
                                 shot=pct("pierce"), **{e: pct(e) for e in ELEMENTS}, stun=pct("stun")))
        stars = {("element", e): 0 for e in ELEMENTS}
        for wk in m.get("weaknesses") or []:
            if wk.get("kind") == "element" and wk.get("element") in ELEMENTS:
                stars[("element", wk["element"])] = max(stars[("element", wk["element"])], wk.get("level", 1))
            elif wk.get("kind") == "status" and wk.get("status") in WILDS_STATUS:
                stars[("status", WILDS_STATUS[wk["status"]])] = wk.get("level", 1)
            elif wk.get("kind") == "effect" and wk.get("effect") == "stun":
                stars[("status", "stun")] = wk.get("level", 1)
        if hitzones:  # completa con las zonas si la API no marca la debilidad
            for e, s in _elem_stars(hitzones).items():
                stars[("element", e)] = max(stars[("element", e)], s)
        ranks = {c.get("rank") for r in m.get("rewards") or [] for c in r.get("conditions") or []}
        ranks = sorted(r for r in ranks if r in ("low", "high")) or ["low", "high"]
        threats, src = _threats(m["name"], world_threats)
        _insert(conn, "wilds", dict(source_id=str(m["id"]), name=m["name"], name_es=es.get(m["id"]),
                                    species=m.get("species"), ranks=ranks, threats=threats, threats_source=src,
                                    icon=icons.get(m["name"])), hitzones, stars)
        n += 1
    return n


# --------------------------------------------------------------------------- variantes especiales
# Encuentros con estadísticas propias. Las zonas de golpe salen de los datos del monstruo base
# (aplicando el estado indicado) y la vida/ataque de la tabla de misiones de Kiranico.
VARIANTS = {
    "world": [dict(
        base="Kirin", name="Kirin (Sterling Pride)", name_es="Kirin sin cuerno",
        label="Sin cuerno · Orgullo esterlino (M★6)", ranks=["master"],
        state="(Electricity)",  # siempre enfurecido: cuerpo cargado de forma permanente
        kiranico="/en/monsters/BQruK/kirin", quest="Sterling Pride", reference="Lightning Crashes",
        notes=["Misión especial de Rango Maestro (M★6 «Orgullo esterlino»): el Kirin empieza con el cuerno roto.",
               "Está siempre enfurecido: su cuerpo permanece cargado de electricidad, así que torso y patas "
               "reciben mucho menos daño y la cabeza es el único punto débil real."],
    )],
}


def _quest_row(html: str, quest: str):
    """Fila de la tabla de misiones de Kiranico: (vida, ataque) o None."""
    m = re.search(re.escape(quest) + r"\s*</[^>]+>.*?([\d,]{4,}).*?x([\d.]+)", html, re.S)
    if not m:
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", html))
        m = re.search(re.escape(quest) + r"\s*\|[\s|]*([\d,]{4,})[\s|]*x([\d.]+)", txt)
    return (int(m.group(1).replace(",", "")), float(m.group(2))) if m else None


def load_variants(conn, game: str) -> int:
    n = 0
    for v in VARIANTS.get(game, []):
        base = conn.execute("SELECT * FROM monsters WHERE game_id=? AND name=? AND variant_of IS NULL",
                            (game, v["base"])).fetchone()
        if not base:
            continue
        hz = [dict(r) for r in conn.execute("SELECT * FROM monster_hitzones WHERE monster_id=?", (base["id"],))]
        state = {}
        for h in hz:  # primera fila "Parte (Estado)" de cada parte
            if h["part"].endswith(v["state"]):
                state.setdefault(h["part"][: -len(v["state"])].strip(), h)
        rows = []
        for h in hz:
            if h["part"].endswith(v["state"]) or "(" in h["part"]:
                continue
            src = state.get(h["part"], h)
            rows.append(dict(src, part=h["part"] + (" (cargado)" if h["part"] in state else "")))
        notes = list(v["notes"])
        try:
            html = fetch_text(config.WORLD_KIRANICO_URL + v["kiranico"])
            q, ref = _quest_row(html, v["quest"]), _quest_row(html, v["reference"])
            if q and ref:
                notes.append(f"Vida: {q[0]:,} frente a {ref[0]:,} del encuentro normal ({(q[0] / ref[0] - 1) * 100:+.0f}%). "
                             f"Ataque x{q[1]:.2f} frente a x{ref[1]:.2f} ({(q[1] / ref[1] - 1) * 100:+.0f}%).".replace(",", "."))
        except Exception:  # noqa: BLE001 - las notas de vida son opcionales
            pass
        weak = {(r["kind"], r["name"]): r["stars"] for r in conn.execute(
            "SELECT * FROM monster_weaknesses WHERE monster_id=?", (base["id"],))}
        mid = _insert(conn, game, dict(name=v["name"], name_es=v["name_es"], species=base["species"], ranks=v["ranks"],
                                       threats=json.loads(base["threats"]), threats_source=base["threats_source"],
                                       icon=base["icon_url"]), rows, weak)
        conn.execute("UPDATE monsters SET variant_of=?, variant_label=?, notes=?, icon_local=? WHERE id=?",
                     (base["id"], v["label"], json.dumps(notes, ensure_ascii=False), base["icon_local"], mid))
        n += 1
    return n


def validate_images_unescape(text: str) -> str:
    return text.replace('\\"', '"').replace("\\\\", "\\")


def load(conn, games=("world", "rise", "wilds")) -> dict:
    from .. import db
    # Esquema de monstruos con columnas nuevas: se recrea (los datos se vuelven a descargar).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(monsters)")}
    if cols and "variant_of" not in cols:
        conn.executescript("DROP TABLE IF EXISTS monster_hitzones; DROP TABLE IF EXISTS monster_weaknesses; "
                           "DROP TABLE IF EXISTS monsters;")
    db.init_schema(conn)
    world_threats = _world_threats()
    out = {}
    for g, fn in (("world", load_world), ("rise", load_rise), ("wilds", load_wilds)):
        if g in games:
            out[g] = fn(conn, world_threats)
            out[g + "_variantes"] = load_variants(conn, g)
            conn.commit()
    return out
