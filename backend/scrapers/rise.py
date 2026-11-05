"""Monster Hunter Rise + Sunbreak — scraping de mhrise.kiranico.com (inglés + español)."""
import re

from bs4 import BeautifulSoup

from .. import config
from ..db import GameWriter
from .http import fetch_text

WEAPON_VIEWS = ["great-sword", "sword-and-shield", "dual-blades", "long-sword", "hammer", "hunting-horn",
                "lance", "gunlance", "switch-axe", "charge-blade", "insect-glaive", "bow", "heavy-bowgun",
                "light-bowgun"]
ELEMENTS = {1: "Fire", 2: "Water", 3: "Thunder", 4: "Ice", 5: "Dragon", 6: "Poison", 7: "Sleep",
            8: "Paralysis", 9: "Blast"}
SHARP_COLORS = {"#BE3843": "red", "#D3673D": "orange", "#C9B232": "yellow", "#81B034": "green",
                "#3A58D7": "blue", "#E2E2E2": "white", "#885AEC": "purple"}
KINDS = ["head", "chest", "arms", "waist", "legs"]

# Palabras que identifican el tipo de pieza en los nombres en inglés.
KIND_WORDS = {
    "head": ["helm", "cap", "headgear", "mask", "hood", "head", "hat", "crown", "headdress", "horn", "hair",
             "vertex", "glare", "brain", "visage", "kabuto", "eyepatch", "glasses", "earrings", "shades",
             "headband", "scarf", "circlet", "feather", "lobos", "cerato", "goggles", "spectacles", "monocle"],
    "chest": ["mail", "vest", "chest", "jacket", "garb", "suit", "robe", "torso", "cuirass", "plate",
              "muscle", "haori", "baulo", "coat", "shirt", "bodice", "tunic"],
    "arms": ["braces", "vambraces", "gloves", "guards", "arms", "gauntlets", "kote", "sleeves", "epine",
             "mittens", "bracers", "fists", "claws", "brachia", "grips"],
    "waist": ["coil", "belt", "tassets", "faulds", "obi", "waist", "ura", "spine", "sash", "coat-tails",
              "skirt", "hip", "girdle", "elytra", "waistcloth"],
    "legs": ["greaves", "leggings", "boots", "trousers", "feet", "legs", "sceros", "socks", "geta", "pants",
             "crura", "heels", "hakama", "shoes", "sandals"],
}


def _url(lang: str, path: str) -> str:
    prefix = "" if lang == "en" else f"/{lang}"
    return f"{config.RISE_SITE_URL}{prefix}/data/{path}"


def _rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    return table.find("tbody").find_all("tr", recursive=False) if table else []


def _id_from(a) -> str | None:
    if a and a.get("href"):
        return a["href"].rstrip("/").split("/")[-1]
    return None


def _slots(node) -> list[int]:
    out = []
    for img in node.find_all("img") if node else []:
        m = re.search(r"deco(\d)\.png", img.get("src", ""))
        if m:
            out.append(int(m.group(1)))
    return sorted(out, reverse=True)


def _sharp(svg):
    vals = {}
    for rect in svg.find_all("rect"):
        col = SHARP_COLORS.get(rect.get("fill", "").upper())
        if col:
            vals[col] = vals.get(col, 0) + int(float(rect.get("width", 0))) * 10
    return vals


def _names_es(path: str) -> dict[str, str]:
    out = {}
    for tr in _rows(fetch_text(_url("es", path))):
        a = tr.find("a")
        if a:
            out[_id_from(a)] = a.get_text(strip=True)
    return out


def _skill_list(td):
    """Devuelve [(id, nombre, nivel)] a partir de enlaces 'Nombre Lv N'."""
    out = []
    for a in td.find_all("a") if td else []:
        if "/skills/" not in a.get("href", ""):
            continue
        txt = a.get_text(" ", strip=True)
        tail = a.next_sibling
        m = re.search(r"^(.*?)\s+Lv\s*(\d+)$", txt)
        if m:
            out.append((_id_from(a), m.group(1).strip(), int(m.group(2))))
        else:
            lvl = re.search(r"Lv\s*(\d+)", str(tail or ""))
            out.append((_id_from(a), txt, int(lvl.group(1)) if lvl else 1))
    return out


def classify_kinds(names: list[str]) -> list[str]:
    """Asigna head/chest/arms/waist/legs a una lista ordenada de piezas de la misma rareza."""
    def by_word(name):
        words = re.findall(r"[a-z\-]+", name.lower())
        for kind, keys in KIND_WORDS.items():
            if any(w in keys for w in words[-2:]):
                return kind
        return None

    kinds = [by_word(n) for n in names]
    # Relleno por posición: dentro de una serie (mismo primer término) el orden es fijo.
    i = 0
    while i < len(names):
        first = names[i].split()[0]
        j = i
        while j + 1 < len(names) and names[j + 1].split()[0] == first and j - i < 4:
            j += 1
        group = list(range(i, j + 1))
        if len(group) == 5:
            for pos, idx in enumerate(group):
                kinds[idx] = kinds[idx] or KINDS[pos]
        else:
            for idx in group:
                if kinds[idx] is None:
                    prev = kinds[idx - 1] if idx > 0 else None
                    kinds[idx] = KINDS[(KINDS.index(prev) + 1) % 5] if prev else "head"
        i = j + 1
    return kinds


def load(conn) -> dict:
    w = GameWriter(conn, "rise")
    w.wipe()
    counts = {}

    # ---- habilidades ----------------------------------------------------
    skills_es = {}
    for tr in _rows(fetch_text(_url("es", "skills"))):
        a = tr.find("a")
        tds = tr.find_all("td")
        if a:
            skills_es[_id_from(a)] = (a.get_text(strip=True), tds[1].get_text(" ", strip=True) if len(tds) > 1 else None)
    skill_name = {}
    n = 0
    for tr in _rows(fetch_text(_url("en", "skills"))):
        a = tr.find("a")
        if not a:
            continue
        sid = _id_from(a)
        name = a.get_text(strip=True)
        tds = tr.find_all("td")
        desc_txt = tds[1].get_text(" ", strip=True) if len(tds) > 1 else ""
        levels = {int(m.group(1)): m.group(2).strip()
                  for m in re.finditer(r"Lv\s*(\d+)\s+(.*?)(?=\s+Lv\s*\d+\s|$)", desc_txt)}
        desc = re.split(r"\s+Lv\s*1\s", desc_txt)[0] if "Lv" in desc_txt else desc_txt
        es_name, es_desc = skills_es.get(sid, (None, None))
        if es_desc and "Lv" in es_desc:
            es_desc = re.split(r"\s+(?:Lv|Nv\.?)\s*1\s", es_desc)[0]
        w.skill(name, name_es=es_name, description=es_desc or desc, max_level=max(levels) if levels else 1,
                levels=levels)
        skill_name[sid] = name
        n += 1
    counts["skills"] = n

    def skills_of(td):
        return [(skill_name.get(sid, nm), lv) for sid, nm, lv in _skill_list(td)]

    # ---- armas ----------------------------------------------------------
    n = 0
    for view, wtype in enumerate(WEAPON_VIEWS):
        es = _names_es(f"weapons?view={view}")
        for tr in _rows(fetch_text(_url("en", f"weapons?view={view}"))):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 8:
                continue
            a = tds[1].find("a")
            wid = _id_from(a)
            img = tds[0].find("img")
            slot_divs = tds[2].find_all("div", recursive=False)
            slots = _slots(slot_divs[0]) if slot_divs else []
            rampage_slots = _slots(slot_divs[1]) if len(slot_divs) > 1 else []
            attack = int(re.sub(r"\D", "", tds[3].get_text()) or 0)
            info = tds[4]
            elems = []
            for span in info.find_all("span", attrs={"data-key": "element"}):
                val = span.find("span", attrs={"data-key": "elementAttack"})
                elems.append((ELEMENTS.get(int(span["data-value"]), span["data-value"]),
                              float(val["data-value"]) if val else None))
            txt = info.get_text(" ", strip=True)
            aff = re.search(r"Affinity\s*([+-]?\d+)%", txt)
            dfn = re.search(r"Defense Bonus\s*\+?(\d+)", txt)
            svgs = tds[5].find_all("svg")
            sharp = _sharp(svgs[0]) if svgs else None
            sharp_max = _sharp(svgs[1]) if len(svgs) > 1 else None
            rampage = [x.get_text(" ", strip=True) for x in tds[6].find_all(["a", "div"]) if x.get_text(strip=True)]
            rarity = int(re.sub(r"\D", "", tds[7].get_text()) or 1)
            extra = {}
            if rampage_slots:
                extra["rampage_slots"] = rampage_slots
            if rampage:
                extra["rampage_skills"] = rampage[:12]
            extra_info = re.sub(r"Affinity\s*[+-]?\d+%|Defense Bonus\s*\+?\d+", "", txt).strip()
            if extra_info and not elems:
                extra["notes"] = extra_info
            w.weapon(dict(expansion_id="rise-sunbreak" if rarity >= 8 else "rise-base", weapon_type_id=wtype,
                          source_id=wid, name=a.get_text(strip=True), name_es=es.get(wid), rarity=rarity,
                          rank="master" if rarity >= 8 else "high" if rarity >= 4 else "low",
                          attack_display=attack, attack_raw=attack, affinity=int(aff.group(1)) if aff else 0,
                          element=elems[0][0] if elems else None, element_value=elems[0][1] if elems else None,
                          element2=elems[1][0] if len(elems) > 1 else None,
                          element2_value=elems[1][1] if len(elems) > 1 else None,
                          defense_bonus=int(dfn.group(1)) if dfn else 0, slots=slots,
                          sharpness=sharp or None, sharpness_max=sharp_max or None, extra=extra,
                          image_url=img["src"].replace("http://", "https://") if img else None))
            n += 1
    counts["weapons"] = n

    # ---- armaduras ------------------------------------------------------
    n = 0
    for view in range(10):
        rarity = view + 1
        exp = "rise-sunbreak" if rarity >= 8 else "rise-base"
        rank = "master" if rarity >= 8 else "high" if rarity >= 4 else "low"
        es = _names_es(f"armors?view={view}")
        parsed = []
        for tr in _rows(fetch_text(_url("en", f"armors?view={view}"))):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 7:
                continue
            a = tds[2].find("a")
            imgs = [td.find("img") for td in tds[:2]]
            nums = [int(x) for x in re.findall(r"-?\d+", tds[4].get_text(" ") + " " + tds[5].get_text(" "))]
            parsed.append(dict(id=_id_from(a), name=a.get_text(strip=True), slots=_slots(tds[3]), nums=nums,
                               skills=skills_of(tds[6]),
                               img_m=imgs[0]["src"].replace("http://", "https://") if imgs[0] else None,
                               img_f=imgs[1]["src"].replace("http://", "https://") if imgs[1] else None))
        kinds = classify_kinds([p["name"] for p in parsed])
        set_ids = {}
        for p, kind in zip(parsed, kinds):
            series = p["name"].split()[0]
            key = (series, rarity)
            if key not in set_ids:
                set_ids[key] = w.armor_set(dict(expansion_id=exp, name=series, name_es=None, rank=rank, rarity=rarity))
            nums = p["nums"] + [0] * 6
            # Orden en la tabla: defensa, fuego, agua | hielo, trueno, dragón
            w.armor(dict(expansion_id=exp, set_id=set_ids[key], source_id=p["id"], kind=kind, name=p["name"],
                         name_es=es.get(p["id"]), rarity=rarity, rank=rank, defense_base=nums[0],
                         defense_max=nums[0], res_fire=nums[1], res_water=nums[2], res_ice=nums[3],
                         res_thunder=nums[4], res_dragon=nums[5], slots=p["slots"],
                         image_url=p["img_m"], image_url_f=p["img_f"]),
                    skills=p["skills"])
            n += 1
    counts["armor"] = n

    # Nombre de serie legible: usa el nombre común más largo de sus piezas.
    for sid, in conn.execute("SELECT id FROM armor_sets WHERE game_id='rise'").fetchall():
        names = [r[0] for r in conn.execute("SELECT name FROM armor_pieces WHERE set_id=?", (sid,))]
        names_es = [r[0] for r in conn.execute("SELECT name_es FROM armor_pieces WHERE set_id=? AND name_es IS NOT NULL", (sid,))]
        conn.execute("UPDATE armor_sets SET name=?, name_es=? WHERE id=?",
                     (_series_name(names), _series_name(names_es) if names_es else None, sid))

    # ---- adornos --------------------------------------------------------
    es = _names_es("decorations")
    n = 0
    for tr in _rows(fetch_text(_url("en", "decorations"))):
        tds = tr.find_all("td", recursive=False)
        a = tds[0].find("a") if tds else None
        if not a:
            continue
        name = a.get_text(strip=True)
        m = re.search(r"(\d)\s*$", name)
        slot = int(m.group(1)) if m else 1
        did = _id_from(a)
        w.decoration(dict(expansion_id="rise-sunbreak" if slot == 4 or "+" in name else "rise-base",
                          source_id=did, name=name, name_es=es.get(did), rarity=None, slot=slot, kind="any"),
                     skills=skills_of(tds[1] if len(tds) > 1 else None))
        n += 1
    counts["decorations"] = n
    return counts


def _series_name(names: list[str]) -> str:
    if not names:
        return "?"
    if len(names) == 1:
        return names[0]
    words = [n.split() for n in names]
    common = []
    for parts in zip(*words):
        if all(p == parts[0] for p in parts):
            common.append(parts[0])
        else:
            break
    return " ".join(common) or names[0]
