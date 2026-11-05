"""Pipeline completo: descarga datos, los guarda en SQLite y precalcula las builds.

Uso:
    python -m backend.pipeline                 # todo
    python -m backend.pipeline --games world   # solo un juego
    python -m backend.pipeline --builds-only   # recalcula builds sin volver a descargar
    python -m backend.pipeline --images        # además descarga las imágenes a data/images
"""
import argparse
import hashlib
import json
import time

from . import catalog, config, db, optimizer
from .scrapers import fextralife, http, images, monsters, rise, validate_images, wilds, world

LOADERS = {"world": world.load, "rise": rise.load, "wilds": wilds.load}


def seed_catalog(conn):
    for g in catalog.GAMES:
        conn.execute("INSERT OR REPLACE INTO games(id,name,subtitle,year,platforms,has_data,note,sort) "
                     "VALUES (:id,:name,:subtitle,:year,:platforms,:has_data,:note,:sort)", g)
    for e in catalog.EXPANSIONS:
        conn.execute("INSERT OR REPLACE INTO expansions(id,game_id,name,rank_label,is_dlc,min_rarity,max_rarity,sort) "
                     "VALUES (:id,:game_id,:name,:rank_label,:is_dlc,:min_rarity,:max_rarity,:sort)", e)
    for i, (wid, es, en, ranged) in enumerate(catalog.WEAPON_TYPES):
        conn.execute("INSERT OR REPLACE INTO weapon_types(id,name,name_en,ranged,sort) VALUES (?,?,?,?,?)",
                     (wid, es, en, ranged, i))
    conn.execute("DELETE FROM game_weapon_types")
    for g in ("world", "rise", "wilds"):
        for wid, *_ in catalog.WEAPON_TYPES:
            conn.execute("INSERT INTO game_weapon_types VALUES (?,?)", (g, wid))
    for wid in catalog.OUTLANDERS_WEAPONS:
        conn.execute("INSERT INTO game_weapon_types VALUES (?,?)", ("outlanders", wid))



def _tiers(exp_id):
    """Escalones del catálogo como dicts (con 'sort' y exclusiones en JSON, igual que en la BD)."""
    exp = next(e for e in catalog.EXPANSIONS if e["id"] == exp_id)
    return [dict(t, sort=i, game_id=exp["game_id"], expansion_id=exp_id, rank_label=exp["rank_label"],
                 monsters=json.dumps(t["monsters"], ensure_ascii=False),
                 exclude=json.dumps(t["exclude"], ensure_ascii=False))
            for i, t in enumerate(catalog.PROGRESSION.get(exp_id, []))]


def compute_builds(conn, games):
    """Calcula TODAS las builds en memoria y las publica de golpe (escalones + builds en una
    sola transacción), para que la web nunca muestre armas sin build mientras se recalcula."""
    results = []  # (expansion_id, tier_sort, weapon_type, score, json)
    for game in games:
        if game not in LOADERS:
            continue
        t0 = time.time()
        data = optimizer.GameData(conn, game)
        exps = [e for e in catalog.EXPANSIONS if e["game_id"] == game]
        n = 0
        for exp in exps:
            # Las expansiones incluyen el contenido del juego base (p. ej. Iceborne usa también armas de World).
            allowed = {e["id"] for e in exps if e["sort"] <= exp["sort"]}
            tiers = _tiers(exp["id"])
            for idx, tier in enumerate(tiers):
                # Las exclusiones de un escalón se aplican también a los anteriores.
                excludes = sorted({x for t in tiers[idx:] for x in json.loads(t["exclude"] or "[]")})
                for wid, *_ in catalog.WEAPON_TYPES:
                    res = optimizer.optimize(data, tier, allowed, wid, excludes)
                    if not res:
                        print(f"  AVISO: sin build para {exp['id']} / {tier['min_rank']} / {wid}")
                        continue
                    build = optimizer.serialize(data, res)
                    results.append((exp["id"], tier["sort"], wid, build["score"], db.dumps(build)))
                    n += 1
        print(f"  [{game}] {n} builds en {time.time() - t0:.0f}s")

    with conn:  # transacción atómica
        conn.execute("DELETE FROM builds")
        conn.execute("DELETE FROM progression_tiers")
        tier_ids = {}
        for exp_id in catalog.PROGRESSION:
            for t in _tiers(exp_id):
                cur = conn.execute(
                    "INSERT INTO progression_tiers(game_id,expansion_id,rank_label,min_rank,max_rarity,deco_max_rarity,"
                    "deco_max_slot,title,description,monsters,exclude,sort) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (t["game_id"], exp_id, t["rank_label"], t["min_rank"], t["max_rarity"], t["deco_max_rarity"],
                     t["deco_max_slot"], t["title"], t["description"], t["monsters"], t["exclude"], t["sort"]))
                tier_ids[(exp_id, t["sort"])] = cur.lastrowid
        exp_game = {e["id"]: e["game_id"] for e in catalog.EXPANSIONS}
        conn.executemany("INSERT INTO builds(game_id,expansion_id,tier_id,weapon_type_id,score,data) VALUES (?,?,?,?,?,?)",
                         [(exp_game[e], e, tier_ids[(e, s)], w, sc, js) for e, s, w, sc, js in results])


def download_images(conn):
    """Descarga las imágenes remotas a IMAGES_DIR y guarda la ruta local."""
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for table in ("weapons", "armor_pieces"):
        rows = conn.execute(f"SELECT id, image_url FROM {table} WHERE image_url IS NOT NULL AND image_local IS NULL").fetchall()
        print(f"  imágenes {table}: {len(rows)}")
        for i, (rid, url) in enumerate(rows):
            ext = url.rsplit(".", 1)[-1].split("?")[0][:5] or "png"
            name = hashlib.sha1(url.encode()).hexdigest()[:20] + "." + ext
            dest = config.IMAGES_DIR / name
            try:
                if not dest.exists():
                    dest.write_bytes(http.fetch(url))
                conn.execute(f"UPDATE {table} SET image_local=? WHERE id=?", (name, rid))
            except Exception as exc:  # noqa: BLE001
                print(f"    aviso: {url}: {exc}")
            if i % 200 == 0:
                conn.commit()
        conn.commit()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", nargs="*", default=list(LOADERS), choices=list(LOADERS))
    ap.add_argument("--builds-only", action="store_true")
    ap.add_argument("--monsters-only", action="store_true", help="solo recarga los monstruos")
    ap.add_argument("--images", action="store_true")
    args = ap.parse_args()

    conn = db.connect()
    db.init_schema(conn)
    seed_catalog(conn)
    conn.commit()
    if args.monsters_only:
        print(f"Monstruos: {monsters.load(conn, tuple(args.games))}")
        conn.close()
        return
    if not args.builds_only:
        for game in args.games:
            t0 = time.time()
            print(f"Descargando {game}...")
            counts = LOADERS[game](conn)
            conn.commit()
            print(f"  [{game}] {counts} en {time.time() - t0:.0f}s")
        print("Cargando monstruos...")
        print(f"  {monsters.load(conn, tuple(args.games))}")
        images.enrich(conn, args.games)
        print("Validando y guardando imágenes en local...")
        print(f"  {validate_images.run(conn, tuple(args.games))}")
        for game in args.games:
            print(f"  [{game}] armaduras completadas desde Fextralife: {fextralife.fill(conn, game)}")
            print(f"  [{game}] armas completadas desde Fextralife: {fextralife.fill_weapons(conn, game)}")
            print(f"  [{game}] piezas sueltas desde Fextralife: {fextralife.fill_piece_pages(conn, game)}")
    print("Calculando builds...")
    compute_builds(conn, list(LOADERS))
    if args.images:
        download_images(conn)
    conn.close()
    print("Listo.")


if __name__ == "__main__":
    main()
