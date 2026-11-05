"""Monster Hunter: World + Iceborne.

Fuente principal: dataset abierto de MHWorldData (gatheringhallstudios) — incluye Iceborne
completo y traducciones al español. Imágenes: API mhw-db.com (solo contenido base y armaduras MR).
"""
import csv
import re
import io

from .. import config
from ..db import GameWriter
from .http import fetch_json, fetch_text

# Multiplicador de "inflado" del ataque mostrado en World -> ataque real.
BLOAT = {"great-sword": 4.8, "long-sword": 3.3, "sword-and-shield": 1.4, "dual-blades": 1.4,
         "hammer": 5.2, "hunting-horn": 4.2, "lance": 2.3, "gunlance": 2.3, "switch-axe": 3.5,
         "charge-blade": 3.6, "insect-glaive": 3.1, "light-bowgun": 1.3, "heavy-bowgun": 1.5, "bow": 1.2}

KIND = {"head": "head", "chest": "chest", "arms": "arms", "waist": "waist", "legs": "legs"}
RANK = {"LR": "low", "HR": "high", "MR": "master"}


def _csv(name: str):
    text = fetch_text(f"{config.WORLD_DATA_REPO_URL}/{name}.csv")
    return list(csv.DictReader(io.StringIO(text)))


def _es(rows, key="name_en"):
    return {r[key]: (r.get("name_es") or "").strip() or None for r in rows}


def _int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _slots(row):
    return [s for s in (_int(row.get("slot_1")), _int(row.get("slot_2")), _int(row.get("slot_3"))) if s > 0]


_ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7"}


def norm(name: str) -> str:
    """Normaliza nombres para cruzar fuentes ('Leather Headgear α+' == 'Leather Headgear Alpha +')."""
    n = name.lower().replace("α", " alpha ").replace("β", " beta ").replace("γ", " gamma ").replace("+", " plus ")
    words = re.findall(r"[a-z0-9']+", n)
    if words and words[-1] in _ROMAN:
        words[-1] = _ROMAN[words[-1]]
    return " ".join(words)


def _images():
    """Mapas nombre -> imagen desde mhw-db (si la API falla, seguimos sin imágenes)."""
    weapons, armor = {}, {}
    try:
        for w in fetch_json(f"{config.WORLD_API_URL}/weapons"):
            assets = w.get("assets") or {}
            if assets.get("image") or assets.get("icon"):
                weapons[norm(w["name"])] = assets.get("image") or assets.get("icon")
        for a in fetch_json(f"{config.WORLD_API_URL}/armor"):
            assets = a.get("assets") or {}
            if assets.get("imageMale") or assets.get("imageFemale"):
                armor[norm(a["name"])] = (assets.get("imageMale"), assets.get("imageFemale"))
    except Exception as exc:  # noqa: BLE001 - las imágenes son opcionales
        print(f"  [world] aviso: sin imágenes de mhw-db ({exc})")
    return weapons, armor


def load(conn) -> dict:
    w = GameWriter(conn, "world")
    w.wipe()
    counts = {}

    # ---- habilidades ----------------------------------------------------
    skill_base = _csv("skills/skill_base")
    skill_tr = {r["name_en"]: r for r in _csv("skills/skill_base_translations")}
    levels: dict[str, dict[int, str]] = {}
    for r in _csv("skills/skill_levels"):
        levels.setdefault(r["base_name_en"], {})[_int(r["level"])] = r.get("description_es") or r["description_en"]
    for r in skill_base:
        name = r["name_en"]
        tr = skill_tr.get(name, {})
        lv = levels.get(name, {})
        w.skill(name, name_es=tr.get("name_es"), description=tr.get("description_es") or tr.get("description_en"),
                kind="secret" if r.get("unlocks") else "armor", max_level=max(lv) if lv else 1,
                secret_levels=_int(r.get("secret")), levels=lv)
    counts["skills"] = len(skill_base)

    # ---- bonificaciones de set -----------------------------------------
    bonus_es = _es(_csv("armors/armorset_bonus_base_translations"))
    bonus_ids = {}
    for r in _csv("armors/armorset_bonus_base"):
        ranks = []
        for i in (1, 2):
            if r.get(f"skill{i}_name"):
                ranks.append((_int(r[f"skill{i}_required"]), r[f"skill{i}_name"], None))
                w.skill(r[f"skill{i}_name"], kind="set")
        bonus_ids[r["name_en"]] = w.bonus(r["name_en"], ranks, name_es=bonus_es.get(r["name_en"]))

    # ---- armaduras ------------------------------------------------------
    weapon_img, armor_img = _images()
    armor_es = _es(_csv("armors/armor_base_translations"))
    set_es = _es(_csv("armors/armorset_base_translations"))
    piece_skills = {r["base_name_en"]: [(r["skill1_name"], _int(r["skill1_level"])),
                                         (r["skill2_name"], _int(r["skill2_level"]))]
                    for r in _csv("armors/armor_skills_ext")}
    piece_set = {}
    for r in _csv("armors/armorset_base"):
        exp = "world-iceborne" if r["rank"] == "MR" else "world-base"
        sid = w.armor_set(dict(expansion_id=exp, name=r["name_en"], name_es=set_es.get(r["name_en"]),
                               rank=RANK.get(r["rank"]), bonus_id=bonus_ids.get(r["bonus"])))
        for kind in KIND:
            if r.get(kind):
                piece_set[r[kind]] = (sid, r["rank"])
    n = 0
    for r in _csv("armors/armor_base"):
        sid, rank = piece_set.get(r["name_en"], (None, None))
        rarity = _int(r["rarity"])
        rank = rank or ("MR" if rarity >= 9 else "HR" if rarity >= 5 else "LR")
        img = armor_img.get(norm(r["name_en"]), (None, None))
        w.armor(dict(expansion_id="world-iceborne" if rank == "MR" else "world-base", set_id=sid,
                     source_id=r["id"], kind=KIND[r["type"]], name=r["name_en"], name_es=armor_es.get(r["name_en"]),
                     rarity=rarity, rank=RANK[rank], defense_base=_int(r["defense_base"]),
                     defense_max=_int(r["defense_augment_max"]) or _int(r["defense_max"]),
                     res_fire=_int(r["defense_fire"]), res_water=_int(r["defense_water"]),
                     res_thunder=_int(r["defense_thunder"]), res_ice=_int(r["defense_ice"]),
                     res_dragon=_int(r["defense_dragon"]), slots=_slots(r), image_url=img[0], image_url_f=img[1]),
                skills=piece_skills.get(r["name_en"], []))
        n += 1
    conn.execute("UPDATE armor_sets SET rarity=(SELECT MAX(rarity) FROM armor_pieces p WHERE p.set_id=armor_sets.id) WHERE game_id='world'")
    counts["armor"] = n

    # ---- adornos --------------------------------------------------------
    deco_es = _es(_csv("decorations/decoration_base_translations"))
    n = 0
    for r in _csv("decorations/decoration_base"):
        rarity = _int(r["rarity"])
        w.decoration(dict(expansion_id="world-iceborne" if rarity >= 9 else "world-base", source_id=r["id"],
                          name=r["name_en"], name_es=deco_es.get(r["name_en"]), rarity=rarity,
                          slot=_int(r["slot"]), kind="any", color=r.get("icon_color")),
                     skills=[(r["skill1_name"], _int(r["skill1_level"])), (r["skill2_name"], _int(r["skill2_level"]))])
        n += 1
    counts["decorations"] = n

    # ---- amuletos -------------------------------------------------------
    charm_es = _es(_csv("charms/charm_base_translations"))
    n = 0
    for r in _csv("charms/charm_base"):
        rarity = _int(r["rarity"])
        w.charm(dict(expansion_id="world-iceborne" if rarity >= 9 else "world-base", name=r["name_en"],
                     name_es=charm_es.get(r["name_en"]), rarity=rarity),
                skills=[(r["skill1_name"], _int(r["skill1_level"])), (r["skill2_name"], _int(r["skill2_level"]))])
        n += 1
    counts["charms"] = n

    # ---- armas ----------------------------------------------------------
    weapon_es = {}
    for r in _csv("weapons/weapon_base_translations"):
        weapon_es[(r["name_en"], r["weapon_type"])] = r.get("name_es") or None
    sharp = {}
    for r in _csv("weapons/weapon_sharpness"):
        vals = {c: _int(r[c]) for c in ("red", "orange", "yellow", "green", "blue", "white", "purple")}
        sharp[(r["base_name_en"], r["weapon_type"])] = (vals, r["maxed"] == "TRUE")
    n = 0
    for r in _csv("weapons/weapon_base"):
        wtype = r["weapon_type"]
        rarity = _int(r["rarity"])
        disp = _int(r["attack"])
        s, maxed = sharp.get((r["name_en"], wtype), (None, True))
        extra = {k: r[k] for k in ("phial", "phial_power", "shelling", "shelling_level", "kinsect_bonus",
                                    "notes", "ammo_config", "category") if r.get(k)}
        extra["handicraft"] = not maxed
        skills = []
        if r.get("skill"):
            extra["skill"] = r["skill"]
            skills = [(r["skill"], 1)] if "/" not in r["skill"] else []
        w.weapon(dict(expansion_id="world-iceborne" if rarity >= 9 else "world-base", weapon_type_id=wtype,
                      source_id=r["id"], name=r["name_en"], name_es=weapon_es.get((r["name_en"], wtype)),
                      rarity=rarity, rank="master" if rarity >= 9 else "high" if rarity >= 5 else "low",
                      attack_display=disp, attack_raw=round(disp / BLOAT[wtype], 1),
                      affinity=_int(r["affinity"]),
                      element=(r["element1"] or None), element_value=_int(r["element1_attack"]) / 10 if r["element1"] else None,
                      element2=(r["element2"] or None), element2_value=_int(r["element2_attack"]) / 10 if r["element2"] else None,
                      element_hidden=1 if r["element_hidden"] == "TRUE" else 0, defense_bonus=_int(r["defense"]),
                      elderseal=r["elderseal"] or None, slots=_slots(r), sharpness=s, extra=extra,
                      previous_name=r["previous_en"] or None, image_url=weapon_img.get(norm(r["name_en"]))),
                 skills=skills)
        n += 1
    counts["weapons"] = n
    return counts
