"""Generador de builds.

Para cada (expansión, escalón de rango, clase de arma):
  1. Filtra el equipo disponible (rareza <= tope del escalón, expansión permitida, exclusiones).
  2. Puntúa las armas de la clase con un modelo de daño simplificado (bruto + afilado + afinidad
     + elemento, ponderado por el tipo de golpes de cada clase).
  3. Para las mejores armas, busca la combinación de 5 piezas (+ amuleto) con búsqueda en haz
     (beam search) maximizando las habilidades que le rentan a esa clase/elemento, teniendo en
     cuenta topes de nivel, bonificaciones de set y el valor de los huecos para adornos.
  4. Rellena los huecos con adornos de forma voraz y elige la mejor build final.
Las piezas se eligen pieza a pieza, así que el resultado natural son sets MIXTOS; además se
penaliza levemente llevar las 5 piezas del mismo set si no activan ninguna bonificación.
"""
import json
from collections import Counter, defaultdict

from . import meta

KINDS = ["head", "chest", "arms", "waist", "legs"]
SHARP_ORDER = ["purple", "white", "blue", "green", "yellow", "orange", "red"]
SHARP_RAW = {"red": 0.5, "orange": 0.75, "yellow": 1.0, "green": 1.05, "blue": 1.2, "white": 1.32, "purple": 1.39}
SHARP_ELEM = {"red": 0.25, "orange": 0.5, "yellow": 0.75, "green": 1.0, "blue": 1.0625, "white": 1.15, "purple": 1.25}
ELEMENTAL = {"fire", "water", "thunder", "ice", "dragon"}
STATUS = {"poison", "paralysis", "sleep", "blast"}
RANDOM_CATEGORIES = {"Kulve"}  # armas de Kulve Taroth: estadísticas aleatorias
BEAM = 110
PER_KIND = 22
FINAL = 18


# --------------------------------------------------------------------------- datos
class GameData:
    """Todo el equipo de un juego cargado en memoria para optimizar rápido."""

    def __init__(self, conn, game_id: str):
        self.game = game_id
        q = lambda sql, *a: conn.execute(sql, a).fetchall()  # noqa: E731
        self.skills = {r["id"]: dict(r) for r in q("SELECT * FROM skills WHERE game_id=?", game_id)}
        self.skill_by_name = {s["name"]: s for s in self.skills.values()}
        # Secretos (World): "Agitator Secret" desbloquea los niveles altos de "Agitator".
        self.secret_of = {}
        for s in self.skills.values():
            if s["name"].endswith(" Secret"):
                base = s["name"][: -len(" Secret")]
                if base == "Slinger Ammo":
                    base = "Slinger Capacity"
                self.secret_of[s["name"]] = base

        def skill_map(table, fk):
            out = defaultdict(dict)
            for r in q(f"SELECT t.{fk} AS owner, s.name, t.level FROM {table} t JOIN skills s ON s.id=t.skill_id "
                       f"WHERE s.game_id=?", game_id):
                out[r["owner"]][r["name"]] = r["level"]
            return out

        wsk = skill_map("weapon_skills", "weapon_id")
        ask = skill_map("armor_skills", "piece_id")
        dsk = skill_map("decoration_skills", "decoration_id")
        csk = skill_map("charm_skills", "charm_id")

        self.bonuses = {}
        for b in q("SELECT * FROM set_bonuses WHERE game_id=?", game_id):
            ranks = [dict(r) for r in q("SELECT pieces, skill_name, description FROM set_bonus_ranks "
                                         "WHERE bonus_id=? ORDER BY pieces", b["id"])]
            self.bonuses[b["id"]] = dict(id=b["id"], name=b["name"], name_es=b["name_es"], ranks=ranks)
        sets = {r["id"]: dict(r) for r in q("SELECT * FROM armor_sets WHERE game_id=?", game_id)}
        self.sets = sets

        self.weapons = []
        for r in q("SELECT * FROM weapons WHERE game_id=?", game_id):
            d = dict(r)
            d["slots"] = json.loads(d["slots"] or "[]")
            d["sharpness"] = json.loads(d["sharpness"]) if d["sharpness"] else None
            d["sharpness_max"] = json.loads(d["sharpness_max"]) if d["sharpness_max"] else None
            d["extra"] = json.loads(d["extra"]) if d["extra"] else {}
            d["skills"] = wsk.get(d["id"], {})
            self.weapons.append(d)
        self.armor = []
        for r in q("SELECT * FROM armor_pieces WHERE game_id=?", game_id):
            d = dict(r)
            d["slots"] = json.loads(d["slots"] or "[]")
            d["skills"] = ask.get(d["id"], {})
            st = sets.get(d["set_id"]) or {}
            d["bonus_ids"] = [b for b in (st.get("bonus_id"), st.get("group_bonus_id")) if b]
            d["set_name"] = st.get("name")
            d["set_name_es"] = st.get("name_es")
            d["tags"] = " | ".join([d["name"], d["set_name"] or ""] +
                                   [self.bonuses[b]["name"] for b in d["bonus_ids"] if b in self.bonuses])
            self.armor.append(d)
        self.decos = []
        for r in q("SELECT * FROM decorations WHERE game_id=?", game_id):
            d = dict(r)
            d["skills"] = dsk.get(d["id"], {})
            self.decos.append(d)
        self.skill_deco_size = {}
        for d in self.decos:
            for n in d["skills"]:
                self.skill_deco_size[n] = min(self.skill_deco_size.get(n, 9), d["slot"])
        self.charms = []
        for r in q("SELECT * FROM charms WHERE game_id=?", game_id):
            d = dict(r)
            d["skills"] = csk.get(d["id"], {})
            self.charms.append(d)

    def skill_es(self, name):
        s = self.skill_by_name.get(name)
        return (s or {}).get("name_es") or name


# --------------------------------------------------------------------------- utilidades
def _allowed(item, tier, expansions, excludes):
    if item["expansion_id"] not in expansions:
        return False
    if item.get("rarity") is not None and item["rarity"] > tier["max_rarity"]:
        return False
    if item.get("unlock_rank") and item["unlock_rank"] > tier.get("min_rank", 9999):
        return False  # p. ej. equipo de Dragones Ancianos Elevados antes de su MR
    name = item.get("tags") or item.get("name") or ""
    return not any(x in name for x in excludes)


def _top_sharp(sharp: dict | None):
    if not sharp:
        return None
    total = sum(sharp.values()) or 1
    for col in SHARP_ORDER:
        if sharp.get(col, 0) >= max(15, 0.07 * total):
            return col
    return "red"


IMPACT_CLASSES = {"hammer", "hunting-horn"}


def damage_type(wtype: str) -> str:
    if wtype in meta.RANGED:
        return "shot"
    return "impact" if wtype in IMPACT_CLASSES else "cut"


def weapon_power(w: dict, target: dict | None = None) -> tuple[float, float, str | None]:
    """Devuelve (potencia, peso del elemento, color de afilado efectivo).

    target (opcional): monstruo objetivo con sus zonas de golpe medias en puntos débiles
    {"phys": {"cut": .65, ...}, "elem": {"fire": .25, ...}, "status": {"poison": 1.3, ...}}.
    Sin objetivo se usan valores medios genéricos (0.6 físico, 0.3 elemental)."""
    wtype = w["weapon_type_id"]
    ranged = wtype in meta.RANGED
    color = None if ranged else _top_sharp(w["sharpness"])
    s_raw = 1.0 if ranged else SHARP_RAW.get(color, 1.0)
    s_elem = 1.0 if ranged else SHARP_ELEM.get(color, 1.0)
    hz_phys = target["phys"][damage_type(wtype)] if target else 0.6
    raw = (w["attack_raw"] or 0) * s_raw * (1 + 0.25 * (w["affinity"] or 0) / 100) * meta.MOTION[wtype] * hz_phys
    elem = 0.0
    el = (w["element"] or "").lower()
    if w["element_value"] and not w["element_hidden"]:
        if el in ELEMENTAL:
            hz = target["elem"].get(el, 0) if target else 0.3  # hitzone elemental medio en puntos débiles
            elem = w["element_value"] * s_elem * hz
        elif el in STATUS:
            elem = w["element_value"] * 0.08 * (target["status"].get(el, 1.0) if target else 1.0)
        if w.get("element2_value"):
            el2 = (w.get("element2") or "").lower()
            hz2 = (target["elem"].get(el2, 0) if target else 0.25) if el2 in ELEMENTAL else 0.1
            elem = elem * 0.75 + (w["element2_value"] or 0) * s_elem * hz2 * 0.5
    total = raw + elem
    return total, (elem / total if total else 0.0), color


# --------------------------------------------------------------------------- talismanes de Rise
# En Rise/Sunbreak los talismanes (las "ciguas" de World) son aleatorios: salen del Crisol de fusión.
# No hay lista fija, así que se genera un talismán OBJETIVO realista para cada etapa: 1-2 habilidades
# útiles con un nivel máximo que depende de la etapa y del tamaño de adorno de la habilidad (las de
# adorno grande salen a niveles bajos), y unos huecos típicos de esa etapa.
TALISMAN_STAGES = [
    # (rareza máx. del escalón, niv. máx. hab.1 por tamaño de adorno, niv. máx. hab.2, huecos, rareza, nombre)
    (3, None, None, [], 0, None),
    (6, {1: 2, 2: 2, 3: 1}, {1: 1, 2: 1}, [1], 5, "Crisol de fusión (Rango Alto)"),
    (7, {1: 3, 2: 2, 3: 2}, {1: 1, 2: 1, 3: 1}, [2, 1], 7, "Fusión «Misterio» (final de Rango Alto)"),
    (9, {1: 3, 2: 2, 3: 2, 4: 1}, {1: 2, 2: 1, 3: 1}, [2, 1], 9, "Fusión de Rango Maestro"),
    (10, {1: 3, 2: 2, 3: 2, 4: 1}, {1: 2, 2: 2, 3: 1, 4: 1}, [2, 1], 10, "Fusión «Arcoíris lunar» (endgame)"),
]


def rise_talismans(data, weights: dict, tier: dict) -> list[dict]:
    stage = next((st for st in TALISMAN_STAGES if tier["max_rarity"] <= st[0]), TALISMAN_STAGES[-1])
    _, cap1, cap2, slots, rarity, method = stage
    if not cap1:
        return []

    def cap(name, caps):
        size = data.skill_deco_size.get(name)
        sk = data.skill_by_name.get(name)
        if not size or not sk:
            return 0
        return min(caps.get(size, 0), sk["max_level"] or 1)

    useful = [n for n, wt in weights.items() if wt > 0]
    first = sorted(((n, cap(n, cap1)) for n in useful), key=lambda x: -weights[x[0]] * x[1])
    first = [(n, c) for n, c in first if c > 0][:12]
    second = sorted(((n, cap(n, cap2)) for n in useful), key=lambda x: -weights[x[0]] * x[1])
    second = [(n, c) for n, c in second if c > 0][:12] + [(None, 0)]
    out = []
    for n1, l1 in first:
        for n2, l2 in second:
            if n2 == n1:
                continue
            skills = {n1: l1}
            if n2:
                skills[n2] = l2
            label = " · ".join(f"{data.skill_es(n)} {lv}" for n, lv in skills.items())
            out.append(dict(id=None, key=f"T:{n1}:{l1}:{n2}:{l2}", name=f"Talisman ({label})",
                            name_es=f"Talismán: {label}", rarity=rarity, skills=skills, slots=list(slots),
                            synthetic=True, method=method))
    return out


class Scorer:
    def __init__(self, data: GameData, weights: dict[str, float]):
        self.data = data
        self.w = weights
        self._caps = {}
        self._bonus_cache = {}

    def cap(self, name: str, unlocked: set[str]) -> int:
        if not unlocked:
            c = self._caps.get(name)
            if c is None:
                c = self._caps[name] = self._cap(name, unlocked)
            return c
        return self._cap(name, unlocked)

    def _cap(self, name: str, unlocked: set[str]) -> int:
        s = self.data.skill_by_name.get(name)
        if not s:
            return 7
        lvl = s["max_level"] or 1
        if s["secret_levels"] and name not in unlocked:
            lvl = max(1, lvl - s["secret_levels"])
        return lvl

    def bonus_effects(self, bonus_counts: Counter):
        """-> (habilidades otorgadas, valor de bonificaciones sin nombre de habilidad estándar)."""
        granted, value = [], 0.0
        for bid, n in bonus_counts.items():
            b = self.data.bonuses.get(bid)
            if not b:
                continue
            active = [r for r in b["ranks"] if n >= r["pieces"]]
            for r in active:
                granted.append(r["skill_name"])
            if active:
                if b["name"] in meta.SET_BONUS_VALUE:
                    value += meta.SET_BONUS_VALUE[b["name"]] * len(active)
                elif not any(r["skill_name"] in self.w for r in active):
                    value += 0.5 * len(active)
        return granted, value

    def value(self, skills: Counter, bonus_counts: Counter) -> float:
        key = tuple(sorted(bonus_counts.items()))
        cached = self._bonus_cache.get(key)
        if cached is None:
            cached = self._bonus_cache[key] = self.bonus_effects(bonus_counts)
        granted, v = cached
        unlocked = {self.data.secret_of[g] for g in granted if g in self.data.secret_of}
        for g in granted:
            v += self.w.get(g, 0.0)
        for name, lvl in skills.items():
            wt = self.w.get(name)
            if wt:
                v += wt * min(lvl, self.cap(name, unlocked))
        return v


# --------------------------------------------------------------------------- optimizador
def optimize(data: GameData, tier: dict, expansions: set[str], weapon_type: str, excludes: list[str],
             target: dict | None = None, adjust=None):
    """target: monstruo objetivo (ver weapon_power). adjust(weights, weapon) -> weights: ajuste de pesos."""
    weapons = [w for w in data.weapons if w["weapon_type_id"] == weapon_type
               and _allowed(w, tier, expansions, excludes)
               and w["extra"].get("category") not in RANDOM_CATEGORIES
               and (w["attack_raw"] or 0) > 0]
    if not weapons:
        return None
    ranked = sorted(((weapon_power(w, target), w) for w in weapons), key=lambda x: -x[0][0])
    picks, seen_elem = [], set()
    for (power, share, color), w in ranked:
        key = (w["element"] or "raw").lower()
        if len(picks) < 2 or (key not in seen_elem and len(picks) < 4 and power >= ranked[0][0][0] * 0.82):
            picks.append((power, share, color, w))
            seen_elem.add(key)
    armor = [a for a in data.armor if _allowed(a, tier, expansions, excludes)]
    deco_cap_r = tier.get("deco_max_rarity")
    deco_cap_s = tier.get("deco_max_slot") or 4
    decos = [d for d in data.decos if d["expansion_id"] in expansions and d["slot"] <= deco_cap_s
             and (deco_cap_r is None or (d["rarity"] or 0) <= deco_cap_r)]
    if deco_cap_r == 0:
        decos = []
    charms = [c for c in data.charms if _allowed(c, tier, expansions, excludes)]

    best = None
    for power, share, color, w in picks:
        weights = meta.profile(weapon_type, w["element"], share)
        if adjust:
            weights = adjust(weights, w)
        charm_pool = rise_talismans(data, weights, tier) if data.game == "rise" else charms
        result = _optimize_armor(data, w, weights, armor, decos, charm_pool)
        score = power * (1 + result["value"] / 100)
        if best is None or score > best["score"]:
            best = dict(score=score, power=power, share=share, color=color, weapon=w, weights=weights, **result)
    best["alternatives"] = [w for _, w in ranked[:6] if w["id"] != best["weapon"]["id"]][:4]
    best["target"] = target
    return best


def _slot_values(decos, weights):
    best = {s: 0.0 for s in range(1, 5)}
    best_kind = {"armor": dict(best), "weapon": dict(best)}
    for d in decos:
        v = sum(weights.get(n, 0) * l for n, l in d["skills"].items())
        for s in range(d["slot"], 5):
            for k in ("armor", "weapon"):
                if d["kind"] in (k, "any"):
                    best_kind[k][s] = max(best_kind[k][s], v)
    return best_kind


def _optimize_armor(data, weapon, weights, armor, decos, charms):
    scorer = Scorer(data, weights)
    useful_decos = [d for d in decos if any(weights.get(n, 0) > 0 for n in d["skills"])]
    slotv = _slot_values(useful_decos, weights)

    def piece_value(p):
        v = sum(weights.get(n, 0) * l for n, l in p["skills"].items())
        v += sum(slotv["armor"][s] * 0.7 for s in p["slots"])
        v += (p["defense_max"] or 0) * 0.002
        for b in p["bonus_ids"]:
            bon = data.bonuses.get(b)
            if bon and (bon["name"] in meta.SET_BONUS_VALUE or any(r["skill_name"] in weights for r in bon["ranks"])):
                v += 0.6
        return v

    top_skills = sorted(weights, key=lambda k: -weights[k])[:10]
    candidates = {}
    for kind in KINDS:
        pieces = [p for p in armor if p["kind"] == kind]
        pieces.sort(key=piece_value, reverse=True)
        chosen = {p["id"]: p for p in pieces[:PER_KIND]}
        for sk in top_skills:
            for p in sorted((p for p in pieces if sk in p["skills"]),
                            key=lambda p: (-p["skills"][sk], -piece_value(p)))[:3]:
                chosen.setdefault(p["id"], p)
        # piezas de sets con bonificación valiosa
        for p in pieces:
            if p["bonus_ids"] and piece_value(p) > 0.6 and len(chosen) < PER_KIND + 14:
                chosen.setdefault(p["id"], p)
        candidates[kind] = list(chosen.values()) or [None]

    # Estado: (piezas, habilidades, bonus, valor de huecos)
    w_skills = Counter(weapon["skills"])
    w_slot_val = sum(slotv["weapon" if data.game == "wilds" else "armor"][s] * 0.7 for s in weapon["slots"])
    beam = [((), w_skills, Counter(), w_slot_val)]
    for kind in KINDS:
        nxt = []
        for pieces, sk, bc, sv in beam:
            for p in candidates[kind]:
                if p is None:
                    nxt.append((pieces + (None,), sk, bc, sv))
                    continue
                s2 = sk + Counter(p["skills"])
                b2 = bc + Counter({b: 1 for b in p["bonus_ids"]})
                sv2 = sv + sum(slotv["armor"][s] * 0.7 for s in p["slots"]) + (p["defense_max"] or 0) * 0.002
                nxt.append((pieces + (p,), s2, b2, sv2))
        nxt.sort(key=lambda st: -(scorer.value(st[1], st[2]) + st[3]))
        beam = nxt[:BEAM]

    # Amuleto
    if charms:
        def charm_slots(c):
            return sum(slotv["armor"][x] * 0.7 for x in c.get("slots") or []) if c else 0

        useful_charms = [c for c in charms if any(weights.get(n, 0) > 0 for n in c["skills"])]
        useful_charms.sort(key=lambda c: -(sum(weights.get(n, 0) * l for n, l in c["skills"].items()) + charm_slots(c)))
        useful_charms = useful_charms[:24] + [None]
        nxt = []
        for pieces, sk, bc, sv in beam[:40]:
            for c in useful_charms:
                s2 = sk + Counter(c["skills"]) if c else sk
                nxt.append((pieces + (c,), s2, bc, sv + charm_slots(c)))
        nxt.sort(key=lambda st: -(scorer.value(st[1], st[2]) + st[3]))
        beam = nxt[:FINAL]
    else:
        beam = [(p + (None,), s, b, v) for p, s, b, v in beam[:FINAL]]

    best = None
    for pieces, sk, bc, _sv in beam:
        armor_pieces, charm = pieces[:5], pieces[5]
        skills, placed = _fill_decos(data, scorer, weapon, armor_pieces, Counter(sk), bc, useful_decos, charm)
        value = scorer.value(skills, bc) + sum((p["defense_max"] or 0) * 0.002 for p in armor_pieces if p)
        set_ids = [p["set_id"] for p in armor_pieces if p]
        if len(set_ids) == 5 and len(set(set_ids)) == 1:
            granted, _ = scorer.bonus_effects(bc)
            if not granted:
                value -= 1.5  # se prefieren sets mixtos (regla de negocio)
        if best is None or value > best["value"]:
            best = dict(value=value, pieces=armor_pieces, charm=charm, skills=skills, bonus_counts=bc, decos=placed)
    return best


def _fill_decos(data, scorer, weapon, pieces, skills, bonus_counts, decos, charm=None):
    slots = [("weapon", s) for s in weapon["slots"]]
    if charm and charm.get("slots"):
        slots += [("charm", s) for s in charm["slots"]]
    for p in pieces:
        if p:
            slots += [(p["kind"], s) for s in p["slots"]]
    slots.sort(key=lambda x: -x[1])
    placed = []
    granted, _ = scorer.bonus_effects(bonus_counts)
    unlocked = {data.secret_of[g] for g in granted if g in data.secret_of}
    w = scorer.w
    for owner, size in slots:
        need = "weapon" if (data.game == "wilds" and owner == "weapon") else ("armor" if data.game == "wilds" else None)
        best_gain, best_d = 0.0, None
        for d in decos:
            if d["slot"] > size or (need and d["kind"] not in (need, "any")):
                continue
            # Ganancia marginal: solo cambian las habilidades del adorno.
            gain = 0.0
            for n, l in d["skills"].items():
                wt = w.get(n)
                if wt:
                    cap = scorer.cap(n, unlocked)
                    cur = skills.get(n, 0)
                    gain += wt * (min(cur + l, cap) - min(cur, cap))
            if gain > best_gain + 1e-9 or (best_d and abs(gain - best_gain) < 1e-9 and d["slot"] < best_d["slot"]):
                best_gain, best_d = gain, d
        if best_d and best_gain > 0.01:
            skills = skills + Counter(best_d["skills"])
            placed.append((owner, size, best_d))
        else:
            placed.append((owner, size, None))
    return skills, placed


# --------------------------------------------------------------------------- serialización
def _img(item):
    """Imagen servida desde nuestro servidor si está guardada en local; si no, la remota."""
    return f"/images/{item['image_local']}" if item.get("image_local") else item.get("image_url")


def _weapon_card(data, w, color=None):
    return dict(id=w["id"], name=w["name"], name_es=w["name_es"], rarity=w["rarity"], type=w["weapon_type_id"],
                attack=w["attack_display"], attack_raw=w["attack_raw"], affinity=w["affinity"],
                element=w["element"], element_value=w["element_value"], element_hidden=bool(w["element_hidden"]),
                element2=w.get("element2"), element2_value=w.get("element2_value"),
                defense_bonus=w["defense_bonus"], slots=w["slots"], sharpness=w["sharpness"],
                sharpness_max=w["sharpness_max"], sharp_color=color, image=_img(w),
                skills=[dict(name=n, name_es=data.skill_es(n), level=l) for n, l in w["skills"].items()],
                expansion=w["expansion_id"], unlock_note=w.get("unlock_note"))


def serialize(data: GameData, result: dict) -> dict:
    weights = result["weights"]
    scorer = Scorer(data, weights)
    granted, _ = scorer.bonus_effects(result["bonus_counts"])
    unlocked = {data.secret_of[g] for g in granted if g in data.secret_of}
    pieces = []
    for kind, p in zip(KINDS, result["pieces"]):
        if not p:
            pieces.append(dict(kind=kind, empty=True))
            continue
        pieces.append(dict(kind=kind, id=p["id"], name=p["name"], name_es=p["name_es"], rarity=p["rarity"],
                           rank=p["rank"], slots=p["slots"], defense=p["defense_max"], image=_img(p),
                           unlock_note=p.get("unlock_note"),
                           image_f=p["image_url_f"], set_name=p["set_name"], set_name_es=p["set_name_es"],
                           expansion=p["expansion_id"],
                           skills=[dict(name=n, name_es=data.skill_es(n), level=l, useful=weights.get(n, 0) > 0)
                                   for n, l in p["skills"].items()]))
    charm = result["charm"]
    decos = [dict(owner=o, size=s, id=d["id"] if d else None, name=d["name"] if d else None,
                  name_es=d["name_es"] if d else None, color=d["color"] if d else None,
                  skills=[dict(name=n, name_es=data.skill_es(n), level=l) for n, l in d["skills"].items()] if d else [])
             for o, s, d in result["decos"]]

    def category(name):
        if name in meta.ELEMENT or name.endswith(" Attack") and name.split()[0] in meta.ELEMENT_NAMES.values():
            return "elemento"
        if name in meta.UTILITY and name not in meta.CLASS_EXTRA.get(result["weapon"]["weapon_type_id"], {}):
            return "comodidad"
        return "daño"

    skills = []
    for name, lvl in sorted(result["skills"].items(), key=lambda kv: -weights.get(kv[0], 0) * kv[1]):
        cap = scorer.cap(name, unlocked)
        skills.append(dict(name=name, name_es=data.skill_es(name), level=min(lvl, cap), raw_level=lvl, max=cap,
                           weight=round(weights.get(name, 0), 2), category=category(name),
                           description=(data.skill_by_name.get(name) or {}).get("description")))
    bonuses = []
    for bid, n in result["bonus_counts"].items():
        b = data.bonuses.get(bid)
        if not b:
            continue
        bonuses.append(dict(name=b["name"], name_es=b["name_es"], pieces=n,
                            ranks=[dict(pieces=r["pieces"], skill=r["skill_name"], skill_es=data.skill_es(r["skill_name"]),
                                        description=r["description"], active=n >= r["pieces"]) for r in b["ranks"]]))
    w = result["weapon"]
    return dict(
        score=round(result["score"], 2), power=round(result["power"], 2), element_share=round(result["share"], 3),
        weapon=_weapon_card(data, w, result["color"]),
        alternatives=[_weapon_card(data, a, weapon_power(a, result.get("target"))[2]) for a in result["alternatives"]],
        armor=pieces,
        charm=dict(id=charm["id"], name=charm["name"], name_es=charm["name_es"], rarity=charm["rarity"],
                   skills=[dict(name=n, name_es=data.skill_es(n), level=l) for n, l in charm["skills"].items()],
                   slots=charm.get("slots") or [], synthetic=bool(charm.get("synthetic")), method=charm.get("method"))
        if charm else None,
        decorations=decos, skills=skills, set_bonuses=bonuses,
        explanation=_explain(data, result, skills),
        signature=[w["id"]] + [p["id"] if p else 0 for p in result["pieces"]] + [(charm.get("key") or charm["id"]) if charm else 0],
    )


ELEM_ES = {"fire": "Fuego", "water": "Agua", "thunder": "Rayo", "ice": "Hielo", "dragon": "Dragón", "poison": "Veneno",
           "paralysis": "Parálisis", "sleep": "Sueño", "blast": "Nitro"}
SHARP_ES = {"red": "rojo", "orange": "naranja", "yellow": "amarillo", "green": "verde", "blue": "azul", "white": "blanco",
            "purple": "morado"}


def _explain(data, result, skills):
    w = result["weapon"]
    name = w["name_es"] or w["name"]
    out = []
    el = (w["element"] or "").lower()
    elem_txt = ""
    if w["element_value"] and not w["element_hidden"]:
        elem_txt = f" y {w['element_value']:g} de {ELEM_ES.get(el, w['element'])}"
    out.append(f"Arma: {name} (rareza {w['rarity']}) es la que más daño efectivo ofrece en este rango: "
               f"{w['attack_display']} de ataque{elem_txt}, afinidad {w['affinity']}%"
               + (f" y afilado {SHARP_ES.get(result['color'], result['color'])}" if result["color"] else "") + ".")
    if result["share"] > 0.25 and el in ELEMENTAL:
        out.append("Al ser un arma con mucho peso elemental, la build prioriza Ataque de elemento y Elemento crítico.")
    elif el in ELEMENTAL:
        out.append("El elemento es secundario en esta clase: la build se centra en daño bruto y críticos.")
    key = [s for s in skills if s["weight"] >= 1.0][:6]
    if key:
        out.append("Habilidades clave: " + ", ".join(f"{s['name_es']} {s['level']}/{s['max']}" for s in key) + ".")
    sets = {p["set_id"] for p in result["pieces"] if p}
    if len(sets) > 1:
        out.append(f"Set mixto de {len(sets)} armaduras distintas: cada pieza se elige por lo que aporta, "
                   "no por completar un set.")
    ch = result.get("charm")
    if ch and ch.get("synthetic"):
        out.append(f"Talismán: en Rise son aleatorios (Crisol de fusión). Se propone uno realista para esta etapa "
                   f"({', '.join(f'{data.skill_es(n)} {l}' for n, l in ch['skills'].items())}, huecos "
                   f"{'-'.join(str(x) for x in ch['slots']) or 'ninguno'}); si consigues uno mejor, úsalo.")
    granted, _ = Scorer(data, result["weights"]).bonus_effects(result["bonus_counts"])
    if granted:
        out.append("Bonificaciones de set activas: " + ", ".join(dict.fromkeys(data.skill_es(g) for g in granted)) + ".")
    return out
