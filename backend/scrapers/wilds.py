"""Monster Hunter Wilds — API pública wilds.mhdb.io (inglés + español)."""
from .. import config
from ..db import GameWriter
from .http import fetch_json

KIND_MAP = {"sword-shield": "sword-and-shield"}


def _get(lang: str, path: str):
    return fetch_json(f"{config.WILDS_API_URL}/{lang}/{path}")


def _by_id(rows):
    return {r["id"]: r for r in rows}


def load(conn) -> dict:
    w = GameWriter(conn, "wilds")
    w.wipe()
    counts = {}

    skills_en, skills_es = _get("en", "skills"), _by_id(_get("es", "skills"))
    skill_name_by_id = {}
    bonus_by_skill = {}
    for s in skills_en:
        es = skills_es.get(s["id"], {})
        skill_name_by_id[s["id"]] = s["name"]
        if s["kind"] in ("set", "group"):
            ranks = []
            es_ranks = {r["id"]: r for r in es.get("ranks", [])}
            for r in s["ranks"]:
                granted = r.get("name") or s["name"]
                w.skill(granted, name_es=es_ranks.get(r["id"], {}).get("name"), description=r.get("description"),
                        kind=s["kind"], max_level=1)
                ranks.append((r.get("setPiecesRequired") or 2, granted, es_ranks.get(r["id"], {}).get("description") or r.get("description")))
            bonus_by_skill[s["id"]] = w.bonus(s["name"], ranks, name_es=es.get("name"))
        else:
            es_ranks = {r["level"]: r.get("description") for r in es.get("ranks", [])}
            levels = {r["level"]: es_ranks.get(r["level"]) or r.get("description") for r in s["ranks"]}
            w.skill(s["name"], name_es=es.get("name"), description=es.get("description") or s.get("description"),
                    kind=s["kind"], max_level=max(levels) if levels else 1, levels=levels)
    counts["skills"] = len(skills_en)

    def plain_skills(entries):
        out = []
        for e in entries or []:
            sk = e.get("skill") or {}
            if sk.get("id") in bonus_by_skill:
                continue
            name = skill_name_by_id.get(sk.get("id")) or sk.get("name")
            if name:
                out.append((name, e.get("level", 1)))
        return out

    # ---- armas ----------------------------------------------------------
    weapons_es = _by_id(_get("es", "weapons"))
    n = 0
    for x in _get("en", "weapons"):
        wtype = KIND_MAP.get(x["kind"], x["kind"])
        elems = [s for s in x.get("specials") or []]
        e1 = elems[0] if elems else None
        e2 = elems[1] if len(elems) > 1 else None
        hc = x.get("handicraft") or []
        sharp_max = None
        if x.get("sharpness") and hc:
            sharp_max = dict(x["sharpness"])
            order = ["red", "orange", "yellow", "green", "blue", "white", "purple"]
            start = max((i for i, c in enumerate(order) if sharp_max.get(c)), default=0)
            for i, extra in enumerate(hc):
                col = order[min(start + i, len(order) - 1)]
                sharp_max[col] = sharp_max.get(col, 0) + extra
        extra = {}
        for k in ("phial", "shell", "coatings", "ammo", "melody", "kinsectLevel", "shellType"):
            if x.get(k):
                extra[k] = x[k]
        if x.get("series"):
            extra["series"] = x["series"].get("name")
        w.weapon(dict(expansion_id="wilds-base", weapon_type_id=wtype, source_id=str(x["id"]), name=x["name"],
                      name_es=weapons_es.get(x["id"], {}).get("name"), rarity=x["rarity"],
                      rank="high" if x["rarity"] >= 5 else "low",
                      attack_display=x["damage"]["display"], attack_raw=x["damage"]["raw"], affinity=x.get("affinity", 0),
                      element=(e1.get("element") or e1.get("status")) if e1 else None,
                      element_value=e1["damage"]["raw"] if e1 else None,
                      element2=(e2.get("element") or e2.get("status")) if e2 else None,
                      element2_value=e2["damage"]["raw"] if e2 else None,
                      element_hidden=1 if e1 and e1.get("hidden") else 0,
                      defense_bonus=x.get("defenseBonus", 0), elderseal=x.get("elderseal"),
                      slots=x.get("slots") or [], sharpness=x.get("sharpness"), sharpness_max=sharp_max,
                      extra=extra),
                 skills=plain_skills(x.get("skills")))
        n += 1
    counts["weapons"] = n

    # ---- armaduras ------------------------------------------------------
    sets_es = _by_id(_get("es", "armor/sets"))
    n = 0
    for s in _get("en", "armor/sets"):
        es = sets_es.get(s["id"], {})
        es_pieces = {p["id"]: p for p in es.get("pieces", [])}
        bonus = bonus_by_skill.get((s.get("bonus") or {}).get("skill", {}).get("id"))
        group = bonus_by_skill.get((s.get("groupBonus") or {}).get("skill", {}).get("id"))
        rank = s["pieces"][0]["rank"] if s.get("pieces") else None
        sid = w.armor_set(dict(expansion_id="wilds-base", name=s["name"], name_es=es.get("name"), rank=rank,
                               rarity=max((p["rarity"] for p in s.get("pieces", [])), default=None),
                               bonus_id=bonus, group_bonus_id=group))
        for p in s.get("pieces", []):
            res = p.get("resistances") or {}
            w.armor(dict(expansion_id="wilds-base", set_id=sid, source_id=str(p["id"]), kind=p["kind"],
                         name=p["name"], name_es=es_pieces.get(p["id"], {}).get("name"), rarity=p["rarity"],
                         rank=p.get("rank"), defense_base=p["defense"]["base"], defense_max=p["defense"]["max"],
                         res_fire=res.get("fire", 0), res_water=res.get("water", 0), res_thunder=res.get("thunder", 0),
                         res_ice=res.get("ice", 0), res_dragon=res.get("dragon", 0), slots=p.get("slots") or []),
                    skills=plain_skills(p.get("skills")))
            n += 1
    counts["armor"] = n

    # ---- adornos --------------------------------------------------------
    deco_es = _by_id(_get("es", "decorations"))
    n = 0
    for d in _get("en", "decorations"):
        w.decoration(dict(expansion_id="wilds-base", source_id=str(d["id"]), name=d["name"],
                          name_es=deco_es.get(d["id"], {}).get("name"), rarity=d.get("rarity"), slot=d["slot"],
                          kind=d.get("kind", "any"), color=(d.get("icon") or {}).get("color")),
                     skills=plain_skills(d.get("skills")))
        n += 1
    counts["decorations"] = n

    # ---- amuletos (solo los fabricables, no los aleatorios) -------------
    charms_es = _by_id(_get("es", "charms"))
    n = 0
    for c in _get("en", "charms"):
        if c.get("random"):
            continue
        es_ranks = {r["id"]: r for r in charms_es.get(c["id"], {}).get("ranks", [])}
        for r in c.get("ranks", []):
            w.charm(dict(expansion_id="wilds-base", name=r["name"], name_es=es_ranks.get(r["id"], {}).get("name"),
                         rarity=r.get("rarity")),
                    skills=plain_skills(r.get("skills")))
            n += 1
    counts["charms"] = n
    return counts
