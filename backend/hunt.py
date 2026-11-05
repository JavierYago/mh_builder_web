"""Build contra un monstruo concreto, en un rango de misión concreto.

1. Objetivo: de las zonas de golpe del monstruo se toma la media de sus 3 mejores partes para
   cada tipo de daño (corte/impacto/disparo) y cada elemento -> el optimizador calcula el daño
   real contra ESE monstruo, así que elige solo el arma del elemento al que es débil.
2. Punto débil: en World/Rise solo se activa en zonas >= 45; si el monstruo no tiene, pierde valor.
3. Defensa: según lo que hace el monstruo (ruge, viento, temblores, plagas, estados) se valoran
   Tapones, Antiviento, Antitemblores, resistencias...
4. Rango: bajo / alto / maestro limita el equipo a la rareza máxima de ese rango.
"""
import json
import threading
from collections import OrderedDict
from statistics import mean

from . import catalog, meta, optimizer
from .monster_threats import THREAT_ES

ELEMENTS = optimizer.ELEMENTAL
RANK_EXPANSION = {
    "world": {"low": "world-base", "high": "world-base", "master": "world-iceborne"},
    "rise": {"low": "rise-base", "high": "rise-base", "master": "rise-sunbreak"},
    "wilds": {"low": "wilds-base", "high": "wilds-base"},
}
LOW_RANK_RARITY = {"world": 4, "rise": 3, "wilds": 4}
RANK_ES = {"low": "Rango Bajo", "high": "Rango Alto", "master": "Rango Maestro"}
STATUS_FACTOR = {0: 0.3, 1: 0.7, 2: 1.0, 3: 1.3}
ELEM_ES = {"fire": "Fuego", "water": "Agua", "thunder": "Rayo", "ice": "Hielo", "dragon": "Dragón",
           "poison": "Veneno", "paralysis": "Parálisis", "sleep": "Sueño", "blast": "Nitro"}
DMG_ES = {"cut": "corte", "impact": "impacto", "shot": "disparo"}

# Habilidad defensiva -> (amenaza que la justifica, valor por nivel)
DEFENSE = {
    "roar": [("Earplugs", 0.9)],
    "wind": [("Windproof", 0.5)],
    "tremor": [("Tremor Resistance", 0.6)],
    "fireblight": [("Fire Resistance", 0.25), ("Blight Resistance", 0.3)],
    "waterblight": [("Water Resistance", 0.25), ("Blight Resistance", 0.3)],
    "thunderblight": [("Thunder Resistance", 0.25), ("Blight Resistance", 0.3)],
    "iceblight": [("Ice Resistance", 0.25), ("Blight Resistance", 0.3)],
    "dragonblight": [("Dragon Resistance", 0.25), ("Blight Resistance", 0.3)],
    "blastblight": [("Blast Resistance", 0.4), ("Blight Resistance", 0.3)],
    "poison": [("Poison Resistance", 0.5)],
    "sleep": [("Sleep Resistance", 0.6)],
    "paralysis": [("Paralysis Resistance", 0.7)],
    "bleed": [("Bleeding Resistance", 0.6)],
    "stun": [("Stun Resistance", 0.6)],
}
DEFENSE_SKILLS = {name for opts in DEFENSE.values() for name, _ in opts}


def _top3(values):
    vals = sorted((v or 0 for v in values), reverse=True)[:3]
    return mean(vals) if vals else 0


def load_monster(conn, monster_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM monsters WHERE id=?", (monster_id,)).fetchone()
    if not row:
        return None
    m = dict(row)
    m["ranks"] = json.loads(m["ranks"])
    m["threats"] = json.loads(m["threats"])
    m["notes"] = json.loads(m.get("notes") or "[]")
    m["hitzones"] = [dict(r) for r in conn.execute("SELECT * FROM monster_hitzones WHERE monster_id=?", (monster_id,))]
    m["weaknesses"] = {(r["kind"], r["name"]): r["stars"] for r in conn.execute(
        "SELECT * FROM monster_weaknesses WHERE monster_id=?", (monster_id,))}
    return m


def target_of(m: dict) -> dict:
    hz = m["hitzones"]
    phys = {k: max(_top3(h[k] for h in hz) / 100, 0.15) for k in ("cut", "impact", "shot")}
    elem = {e: _top3(h[e] for h in hz) / 100 for e in ELEMENTS}
    status = {s: STATUS_FACTOR.get(m["weaknesses"].get(("status", s), 1), 0.7)
              for s in ("poison", "sleep", "paralysis", "blast")}
    best_phys = {k: max((h[k] or 0) for h in hz) for k in ("cut", "impact", "shot")} if hz else {}
    return dict(phys=phys, elem=elem, status=status, best_phys=best_phys, threats=m["threats"])


def rank_tier(game: str, rank: str, player_rank: int | None = None):
    """Escalón de equipo para una misión de `rank` hecha por un jugador de rango `player_rank`.

    Candidatos: los escalones de progresión que corresponden a ese rango de misión (en Rango Bajo
    los de rareza baja, en Rango Alto los de rareza alta del juego base, en Rango Maestro los del DLC).
    Se elige el último cuyo rango mínimo sea <= al del jugador. Sin rango -> el mejor equipo del rango.
    Devuelve (escalón, expansiones permitidas, exclusiones, info para la interfaz)."""
    exp_id = RANK_EXPANSION[game][rank]
    tiers = catalog.PROGRESSION[exp_id]
    cap = LOW_RANK_RARITY[game]
    if rank == "low":
        cands = [i for i, t in enumerate(tiers) if t["max_rarity"] <= cap]
    elif rank == "high":
        cands = [i for i, t in enumerate(tiers) if t["max_rarity"] > cap]
    else:
        cands = list(range(len(tiers)))
    too_low = False
    if player_rank is None:
        idx = cands[-1]
    else:
        ok = [i for i in cands if tiers[i]["min_rank"] <= player_rank]
        too_low = not ok
        idx = ok[-1] if ok else cands[0]
    tier = dict(tiers[idx])
    excludes = sorted({x for t in tiers[idx:] for x in t["exclude"]}) if player_rank is not None else []
    exps = {e["id"] for e in catalog.EXPANSIONS if e["game_id"] == game and
            (e["id"] == exp_id or not e["is_dlc"])}
    label = next(e["rank_label"] for e in catalog.EXPANSIONS if e["id"] == exp_id)
    info = dict(expansion=exp_id, rank_label=label, player_rank=player_rank, tier_title=tier["title"],
                tier_min_rank=tier["min_rank"], max_rarity=tier["max_rarity"], too_low=too_low,
                min_rank_for_quest=tiers[cands[0]]["min_rank"], tier_index=idx)
    return tier, exps, excludes, info


def _adjuster(game: str, target: dict, weapon_type: str):
    def adjust(weights, weapon):
        w = dict(weights)
        if game != "wilds":  # en Wilds Punto débil también funciona en heridas
            best = target["best_phys"].get(optimizer.damage_type(weapon_type), 0)
            factor = 1.0 if best >= 45 else 0.35
            for k in ("Weakness Exploit",):
                if k in w:
                    w[k] *= factor
        for threat in target["threats"]:
            for name, val in DEFENSE.get(threat, []):
                w[name] = max(w.get(name, 0), val)
        if "frenzy" in target["threats"]:
            w["Antivirus"] = w.get("Antivirus", 0) + 1.0
        return w
    return adjust


def explain(m: dict, rank: str, build: dict, target: dict, weapon_type: str) -> list[str]:
    out = []
    weak = sorted(((e, m["weaknesses"].get(("element", e), 0)) for e in ELEMENTS), key=lambda x: -x[1])
    top = [f"{ELEM_ES[e]} ({'★' * s})" for e, s in weak if s >= 2]
    name = m["name_es"] or m["name"]
    out.append(f"{name} en {RANK_ES[rank]}: " + (f"débil a {', '.join(top)}." if top else "sin debilidades elementales marcadas."))
    out.extend(m.get("notes") or [])
    w = build["weapon"]
    el = (w.get("element") or "").lower()
    best_el = max(ELEMENTS, key=lambda e: target["elem"].get(e, 0))
    if el in ELEMENTS and w.get("element_value") and not w.get("element_hidden"):
        pct = target["elem"].get(el, 0) * 100
        if el == best_el:
            out.append(f"Arma de {ELEM_ES[el]}: es su mayor debilidad (sus zonas débiles reciben un {pct:.0f}% de ese elemento).")
        elif build.get("element_share", 0) < 0.15:
            out.append(f"Su mayor debilidad es {ELEM_ES[best_el]}, pero en esta clase el elemento pesa poco: "
                       f"se elige el arma con más daño bruto efectivo, que es de {ELEM_ES[el]} ({pct:.0f}%).")
        else:
            out.append(f"Su mayor debilidad es {ELEM_ES[best_el]}, pero las armas de ese elemento disponibles en este rango "
                       f"rinden menos en conjunto; esta de {ELEM_ES[el]} ({pct:.0f}%) da más daño total.")
    elif el in ELEM_ES:
        out.append(f"Arma de {ELEM_ES[el]}: estado eficaz contra este monstruo.")
    else:
        out.append("Arma sin elemento: contra este monstruo pesa más el daño bruto.")
    dt = optimizer.damage_type(weapon_type)
    best = target["best_phys"].get(dt, 0)
    out.append(f"Su mejor zona al {DMG_ES[dt]} recibe {best:.0f}% de daño"
               + (" (activa Punto débil)." if best >= 45 or m["game_id"] == "wilds" else "; Punto débil apenas se activa, así que pesa menos."))
    defs = [THREAT_ES[t] for t in target["threats"] if t in THREAT_ES]
    if defs:
        out.append("Ataques a tener en cuenta: " + ", ".join(defs) + ". Se valoran las habilidades que los contrarrestan.")
    if m.get("threats_source") == "estimado":
        out.append("Nota: las amenazas de este monstruo son una estimación (su fuente de datos no las publica).")
    return out + build["explanation"]


class HuntService:
    """Calcula builds contra monstruos bajo demanda, con caché en memoria."""

    def __init__(self, conn_factory):
        self._conn_factory = conn_factory
        self._data: dict[str, optimizer.GameData] = {}
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def _game_data(self, conn, game):
        if game not in self._data:
            self._data[game] = optimizer.GameData(conn, game)
        return self._data[game]

    def build(self, monster_id: int, rank: str, weapon_type: str, player_rank: int | None = None) -> dict | None:
        game = None
        conn = self._conn_factory()
        row = conn.execute("SELECT game_id FROM monsters WHERE id=?", (monster_id,)).fetchone()
        if row and rank in RANK_EXPANSION.get(row[0], {}):
            game = row[0]
        tier_idx = rank_tier(game, rank, player_rank)[3]["tier_index"] if game else None
        key = (monster_id, rank, weapon_type, tier_idx, player_rank)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            m = load_monster(conn, monster_id)
            if not m or rank not in m["ranks"] or rank not in RANK_EXPANSION.get(m["game_id"], {}):
                return None
            data = self._game_data(conn, m["game_id"])
            tier, exps, excludes, info = rank_tier(m["game_id"], rank, player_rank)
            target = target_of(m)
            res = optimizer.optimize(data, tier, exps, weapon_type, excludes, target=target,
                                     adjust=_adjuster(m["game_id"], target, weapon_type))
            if not res:
                return None
            build = optimizer.serialize(data, res)
            for s in build["skills"]:
                if s["name"] in DEFENSE_SKILLS:
                    s["category"] = "defensa"
            build["explanation"] = explain(m, rank, build, target, weapon_type)
            if player_rank is not None:
                note = (f"Con {info['rank_label']} {player_rank} puedes forjar equipo de hasta rareza {info['max_rarity']} "
                        f"({info['tier_title']}).")
                if info["too_low"]:
                    note = (f"Las misiones de {RANK_ES[rank]} piden al menos {info['rank_label']} {info['min_rank_for_quest']}: "
                            f"se muestra el equipo de esa etapa.")
                build["explanation"].insert(1, note)
            build["tier"] = info
            self._cache[key] = build
            if len(self._cache) > 400:
                self._cache.popitem(last=False)
            return build
