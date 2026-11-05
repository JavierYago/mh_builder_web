"""API web (FastAPI) + servidor del frontend.

Arranque:  python -m backend.app      (lee host/puerto del .env)
"""
import json
import threading

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import config, db, hunt, thumbs
from .monster_threats import THREAT_ES

app = FastAPI(title="MH Builder", docs_url=None, redoc_url=None, openapi_url=None)
if config.CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET"])

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data: https://assets.mhw-db.com https://cdn.kiranico.net https://mhwilds.kiranico.net; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = CSP
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


_local = threading.local()


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        if not config.DB_PATH.exists():
            raise HTTPException(503, "La base de datos aún no existe. Ejecuta: python -m backend.pipeline")
        c = _local.conn = db.connect(readonly=True)
    return c


def rows(sql, *args):
    return [dict(r) for r in conn().execute(sql, args).fetchall()]


def image(r: dict, key="image_url"):
    if r.get("image_local"):
        return f"/images/{r['image_local']}"
    return r.get(key)


def _expansion(exp_id: str) -> dict:
    found = rows("SELECT * FROM expansions WHERE id=?", exp_id)
    if not found:
        raise HTTPException(404, "Expansión desconocida")
    return found[0]


def _skills_for(table: str, fk: str, ids: list[int]) -> dict[int, list]:
    out: dict[int, list] = {}
    for i in range(0, len(ids), 900):
        chunk = ids[i:i + 900]
        if not chunk:
            continue
        sql = (f"SELECT t.{fk} AS owner, s.name, s.name_es, t.level FROM {table} t JOIN skills s ON s.id=t.skill_id "
               f"WHERE t.{fk} IN ({','.join('?' * len(chunk))})")
        for r in conn().execute(sql, chunk):
            out.setdefault(r["owner"], []).append(dict(name=r["name"], name_es=r["name_es"], level=r["level"]))
    return out


# --------------------------------------------------------------------------- API
@app.get("/api/games")
def games():
    gs = rows("SELECT * FROM games ORDER BY sort")
    exps = rows("SELECT * FROM expansions ORDER BY sort")
    wt = rows("SELECT gw.game_id, t.* FROM game_weapon_types gw JOIN weapon_types t ON t.id=gw.weapon_type_id ORDER BY t.sort")
    counts = {r["expansion_id"]: r for r in rows(
        "SELECT e.id AS expansion_id, "
        "(SELECT COUNT(*) FROM weapons w WHERE w.expansion_id=e.id) AS weapons, "
        "(SELECT COUNT(*) FROM armor_pieces a WHERE a.expansion_id=e.id) AS armor, "
        "(SELECT COUNT(*) FROM decorations d WHERE d.expansion_id=e.id) AS decorations "
        "FROM expansions e")}
    for g in gs:
        g["expansions"] = [dict(e, counts=counts.get(e["id"], {})) for e in exps if e["game_id"] == g["id"]]
        g["weapon_types"] = [{k: v for k, v in t.items() if k != "game_id"} for t in wt if t["game_id"] == g["id"]]
    return gs


@app.get("/api/weapon-types")
def weapon_types():
    types = rows("SELECT * FROM weapon_types ORDER BY sort")
    counts = rows("SELECT weapon_type_id, expansion_id, COUNT(*) AS n FROM weapons GROUP BY 1, 2")
    for t in types:
        t["counts"] = {c["expansion_id"]: c["n"] for c in counts if c["weapon_type_id"] == t["id"]}
        t["games"] = [r["game_id"] for r in rows("SELECT game_id FROM game_weapon_types WHERE weapon_type_id=?", t["id"])]
    return types


@app.get("/api/builds/{expansion_id}/{weapon_type}")
def builds(expansion_id: str, weapon_type: str):
    exp = _expansion(expansion_id)
    tiers = rows("SELECT * FROM progression_tiers WHERE expansion_id=? ORDER BY sort", expansion_id)
    data = {r["tier_id"]: json.loads(r["data"]) for r in rows(
        "SELECT tier_id, data FROM builds WHERE expansion_id=? AND weapon_type_id=?", expansion_id, weapon_type)}
    out, prev_sig = [], None
    for t in tiers:
        b = data.get(t["id"])
        if not b:
            continue
        t["monsters"] = json.loads(t["monsters"] or "[]")
        t.pop("exclude", None)
        sig = b.get("signature")
        if out and sig == prev_sig:
            # Sin cambios respecto al escalón anterior: se mantiene la build y se amplía su rango.
            out[-1]["merged_ranks"].append(t["min_rank"])
            out[-1]["monsters"] = list(dict.fromkeys(out[-1]["monsters"] + t["monsters"]))
            continue
        prev_sig = sig
        out.append(dict(t, build=b, merged_ranks=[]))
    for i, t in enumerate(out):
        t["max_rank"] = out[i + 1]["min_rank"] - 1 if i + 1 < len(out) else None
    wt = rows("SELECT * FROM weapon_types WHERE id=?", weapon_type)
    if not wt:
        raise HTTPException(404, "Tipo de arma desconocido")
    game = rows("SELECT * FROM games WHERE id=?", exp["game_id"])[0]
    return dict(game=game, expansion=exp, weapon_type=wt[0], tiers=out)


@app.get("/api/weapons")
def weapons(type: str = Query(..., max_length=40), expansion: str = Query(..., max_length=40),
            q: str = Query("", max_length=60)):
    _expansion(expansion)
    sql = "SELECT * FROM weapons WHERE weapon_type_id=? AND expansion_id=?"
    args = [type, expansion]
    if q:
        sql += " AND (name LIKE ? OR name_es LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    ws = rows(sql + " ORDER BY rarity, id", *args)
    sk = _skills_for("weapon_skills", "weapon_id", [w["id"] for w in ws])
    for w in ws:
        for k in ("slots", "sharpness", "sharpness_max", "extra"):
            w[k] = json.loads(w[k]) if w[k] else None
        w["image"] = image(w)
        w["skills"] = sk.get(w["id"], [])
        for k in ("image_url", "image_local", "source_id", "game_id"):
            w.pop(k, None)
    return ws


@app.get("/api/armor")
def armor(expansion: str = Query(..., max_length=40), q: str = Query("", max_length=60)):
    _expansion(expansion)
    sets = rows("SELECT s.*, b.name AS bonus_name, b.name_es AS bonus_name_es, g.name AS group_name, g.name_es AS group_name_es "
                "FROM armor_sets s LEFT JOIN set_bonuses b ON b.id=s.bonus_id LEFT JOIN set_bonuses g ON g.id=s.group_bonus_id "
                "WHERE s.expansion_id=? ORDER BY s.rarity, s.id", expansion)
    pieces = rows("SELECT * FROM armor_pieces WHERE expansion_id=? ORDER BY id", expansion)
    sk = _skills_for("armor_skills", "piece_id", [p["id"] for p in pieces])
    ranks = {}
    for r in rows("SELECT r.*, COALESCE(s.name_es, r.skill_name) AS skill_es FROM set_bonus_ranks r "
                  "JOIN set_bonuses b ON b.id=r.bonus_id "
                  "LEFT JOIN skills s ON s.game_id=b.game_id AND s.name=r.skill_name "
                  "WHERE b.game_id=(SELECT game_id FROM expansions WHERE id=?) ORDER BY pieces", expansion):
        ranks.setdefault(r["bonus_id"], []).append(dict(pieces=r["pieces"], skill=r["skill_es"], description=r["description"]))
    by_set: dict[int, list] = {}
    order = {"head": 0, "chest": 1, "arms": 2, "waist": 3, "legs": 4}
    for p in pieces:
        p["slots"] = json.loads(p["slots"] or "[]")
        p["skills"] = sk.get(p["id"], [])
        p["image"] = image(p)
        by_set.setdefault(p["set_id"], []).append(p)
    out = []
    ql = q.lower()
    for s in sets:
        ps = sorted(by_set.get(s["id"], []), key=lambda p: order.get(p["kind"], 9))
        if not ps:
            continue
        if ql and ql not in (s["name"] or "").lower() and ql not in (s["name_es"] or "").lower() and not any(
                ql in (p["name"] or "").lower() or ql in (p["name_es"] or "").lower() for p in ps):
            continue
        s["pieces"] = ps
        s["bonus_ranks"] = ranks.get(s["bonus_id"], [])
        s["group_ranks"] = ranks.get(s["group_bonus_id"], [])
        out.append(s)
    return out


@app.get("/api/decorations")
def decorations(expansion: str = Query(..., max_length=40)):
    _expansion(expansion)
    ds = rows("SELECT * FROM decorations WHERE expansion_id=? ORDER BY slot, rarity, name", expansion)
    sk = _skills_for("decoration_skills", "decoration_id", [d["id"] for d in ds])
    for d in ds:
        d["skills"] = sk.get(d["id"], [])
    return ds


@app.get("/api/skills/{game_id}")
def skills(game_id: str):
    out = rows("SELECT id, name, name_es, description, kind, max_level FROM skills WHERE game_id=? ORDER BY name", game_id)
    lv = rows("SELECT l.* FROM skill_levels l JOIN skills s ON s.id=l.skill_id WHERE s.game_id=? ORDER BY level", game_id)
    by = {}
    for r in lv:
        by.setdefault(r["skill_id"], []).append(dict(level=r["level"], description=r["description"]))
    for s in out:
        s["levels"] = by.get(s["id"], [])
    return out


_hunt = hunt.HuntService(lambda: db.connect(readonly=True))
RANKS = ("low", "high", "master")


def _monster_row(m: dict, weak: dict) -> dict:
    return dict(id=m["id"], game_id=m["game_id"], name=m["name"], name_es=m["name_es"], species=m["species"],
                ranks=json.loads(m["ranks"]), threats=json.loads(m["threats"]), threats_source=m["threats_source"],
                icon=f"/images/{m['icon_local']}" if m.get("icon_local") else m.get("icon_url"),
                weaknesses=weak.get(m["id"], {}), variant_of=m.get("variant_of"), variant_label=m.get("variant_label"),
                notes=json.loads(m.get("notes") or "[]"))


@app.get("/api/monsters")
def monsters(game: str = Query(..., max_length=20)):
    ms = rows("SELECT * FROM monsters WHERE game_id=? AND variant_of IS NULL ORDER BY COALESCE(name_es, name)", game)
    has_variants = {r["variant_of"] for r in rows("SELECT variant_of FROM monsters WHERE game_id=? AND variant_of IS NOT NULL", game)}
    weak = {}
    for r in rows("SELECT w.* FROM monster_weaknesses w JOIN monsters m ON m.id=w.monster_id WHERE m.game_id=?", game):
        weak.setdefault(r["monster_id"], {})[f"{r['kind']}:{r['name']}"] = r["stars"]
    return [dict(_monster_row(m, weak), has_variants=m["id"] in has_variants) for m in ms]


@app.get("/api/monsters/{monster_id}")
def monster(monster_id: int):
    found = rows("SELECT * FROM monsters WHERE id=?", monster_id)
    if not found:
        raise HTTPException(404, "Monstruo desconocido")
    weak = {monster_id: {f"{r['kind']}:{r['name']}": r["stars"]
                         for r in rows("SELECT * FROM monster_weaknesses WHERE monster_id=?", monster_id)}}
    out = _monster_row(found[0], weak)
    out["hitzones"] = rows("SELECT part, cut, impact, shot, fire, water, thunder, ice, dragon, stun "
                           "FROM monster_hitzones WHERE monster_id=?", monster_id)
    out["threats_es"] = [THREAT_ES.get(t, t) for t in out["threats"]]
    base_id = out["variant_of"] or monster_id
    forms = rows("SELECT id, name, name_es, variant_label FROM monsters WHERE id=? OR variant_of=? ORDER BY variant_of IS NOT NULL, id",
                 base_id, base_id)
    out["forms"] = [dict(id=f["id"], label=f["variant_label"] or "Normal", name=f["name_es"] or f["name"]) for f in forms]         if len(forms) > 1 else []
    return out


@app.get("/api/hunt/{monster_id}")
def hunt_build(monster_id: int, rank: str = Query(..., max_length=10), weapon: str = Query(..., max_length=40),
               hr: int | None = Query(None, ge=1, le=999)):
    if rank not in RANKS:
        raise HTTPException(400, "Rango no válido")
    if not rows("SELECT 1 FROM weapon_types WHERE id=?", weapon):
        raise HTTPException(404, "Tipo de arma desconocido")
    build = _hunt.build(monster_id, rank, weapon, hr)
    if not build:
        raise HTTPException(404, "No hay build para ese monstruo, rango y arma")
    return build


@app.get("/thumb")
def thumb(src: str = Query(..., max_length=200)):
    """Miniatura cacheada de un render remoto pesado (solo URLs de la lista blanca)."""
    if not thumbs.allowed(src):
        raise HTTPException(400, "Origen de imagen no permitido")
    try:
        data = thumbs.get(src)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, "No se pudo obtener la imagen") from exc
    return Response(data, media_type="image/webp", headers={"Cache-Control": "public, max-age=2592000, immutable"})


# --------------------------------------------------------------------------- estáticos
config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=config.IMAGES_DIR), name="images")
app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host=config.APP_HOST, port=config.APP_PORT)
