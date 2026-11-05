"""Acceso a SQLite y utilidades de inserción usadas por los scrapers."""
import json
import sqlite3
from pathlib import Path

from . import config

SCHEMA = Path(__file__).with_name("schema.sql")


def connect(readonly: bool = False) -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if readonly:
        conn = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Columnas añadidas después de la primera versión: se crean si faltan (migración simple).
MIGRATIONS = [
    ("weapons", "unlock_rank", "INTEGER"), ("weapons", "unlock_note", "TEXT"),
    ("armor_pieces", "unlock_rank", "INTEGER"), ("armor_pieces", "unlock_note", "TEXT"),
]


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text(encoding="utf8"))
    for table, col, kind in MIGRATIONS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class GameWriter:
    """Inserta los datos de un juego, resolviendo habilidades por nombre."""

    def __init__(self, conn: sqlite3.Connection, game_id: str):
        self.conn = conn
        self.game = game_id
        self._skills: dict[str, int] = {}
        self._bonuses: dict[str, int] = {}

    # ---- limpieza -------------------------------------------------------
    def wipe(self) -> None:
        g = self.game
        c = self.conn
        for tbl, child in (("weapons", "weapon_skills"), ("armor_pieces", "armor_skills"),
                           ("decorations", "decoration_skills"), ("charms", "charm_skills")):
            fk = {"weapon_skills": "weapon_id", "armor_skills": "piece_id",
                  "decoration_skills": "decoration_id", "charm_skills": "charm_id"}[child]
            c.execute(f"DELETE FROM {child} WHERE {fk} IN (SELECT id FROM {tbl} WHERE game_id=?)", (g,))
            c.execute(f"DELETE FROM {tbl} WHERE game_id=?", (g,))
        c.execute("DELETE FROM armor_sets WHERE game_id=?", (g,))
        c.execute("DELETE FROM set_bonus_ranks WHERE bonus_id IN (SELECT id FROM set_bonuses WHERE game_id=?)", (g,))
        c.execute("DELETE FROM set_bonuses WHERE game_id=?", (g,))
        c.execute("DELETE FROM skill_levels WHERE skill_id IN (SELECT id FROM skills WHERE game_id=?)", (g,))
        c.execute("DELETE FROM skills WHERE game_id=?", (g,))

    # ---- habilidades ----------------------------------------------------
    def skill(self, name: str, *, name_es=None, description=None, kind="armor",
              max_level=None, secret_levels=0, levels=None) -> int:
        name = name.strip()
        if name in self._skills:
            sid = self._skills[name]
            if max_level:
                self.conn.execute("UPDATE skills SET max_level=MAX(max_level, ?) WHERE id=?", (max_level, sid))
            if name_es:
                self.conn.execute("UPDATE skills SET name_es=COALESCE(name_es, ?) WHERE id=?", (name_es, sid))
            if description:
                self.conn.execute("UPDATE skills SET description=COALESCE(description, ?) WHERE id=?", (description, sid))
        else:
            cur = self.conn.execute(
                "INSERT INTO skills(game_id,name,name_es,description,kind,max_level,secret_levels) VALUES (?,?,?,?,?,?,?)",
                (self.game, name, name_es, description, kind, max_level or 1, secret_levels))
            sid = cur.lastrowid
            self._skills[name] = sid
        for lvl, desc in (levels or {}).items():
            self.conn.execute("INSERT OR REPLACE INTO skill_levels(skill_id,level,description) VALUES (?,?,?)",
                              (sid, lvl, desc))
        return sid

    def _link_skills(self, table: str, fk: str, owner_id: int, skills) -> None:
        for name, level in skills:
            if not name or not level:
                continue
            sid = self.skill(name, max_level=None)
            self.conn.execute(
                f"INSERT INTO {table}({fk},skill_id,level) VALUES (?,?,?) "
                f"ON CONFLICT({fk},skill_id) DO UPDATE SET level=level+excluded.level",
                (owner_id, sid, int(level)))
        # Garantiza que max_level cubra lo que aportan las piezas.
        self.conn.execute(
            f"UPDATE skills SET max_level=MAX(max_level, (SELECT MAX(level) FROM {table} t WHERE t.skill_id=skills.id)) "
            f"WHERE id IN (SELECT skill_id FROM {table} WHERE {fk}=?)", (owner_id,))

    # ---- set bonus ------------------------------------------------------
    def bonus(self, name: str, ranks, name_es=None) -> int:
        """ranks: [(piezas, habilidad_otorgada, descripcion)]"""
        if name in self._bonuses:
            return self._bonuses[name]
        cur = self.conn.execute("INSERT INTO set_bonuses(game_id,name,name_es) VALUES (?,?,?)",
                                (self.game, name, name_es))
        bid = cur.lastrowid
        for pieces, skill_name, desc in ranks:
            self.conn.execute("INSERT OR REPLACE INTO set_bonus_ranks(bonus_id,pieces,skill_name,description) VALUES (?,?,?,?)",
                              (bid, int(pieces), skill_name, desc))
        self._bonuses[name] = bid
        return bid

    # ---- equipo ---------------------------------------------------------
    def weapon(self, data: dict, skills=()) -> int:
        data = dict(data, game_id=self.game)
        for k in ("slots", "sharpness", "sharpness_max", "extra"):
            if k in data and not isinstance(data[k], str) and data[k] is not None:
                data[k] = dumps(data[k])
        cols = ",".join(data)
        cur = self.conn.execute(f"INSERT INTO weapons({cols}) VALUES ({','.join('?' * len(data))})", list(data.values()))
        self._link_skills("weapon_skills", "weapon_id", cur.lastrowid, skills)
        return cur.lastrowid

    def armor_set(self, data: dict) -> int:
        data = dict(data, game_id=self.game)
        cur = self.conn.execute(f"INSERT INTO armor_sets({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                                list(data.values()))
        return cur.lastrowid

    def armor(self, data: dict, skills=()) -> int:
        data = dict(data, game_id=self.game)
        if not isinstance(data.get("slots", "[]"), str):
            data["slots"] = dumps(data["slots"])
        cur = self.conn.execute(f"INSERT INTO armor_pieces({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                                list(data.values()))
        self._link_skills("armor_skills", "piece_id", cur.lastrowid, skills)
        return cur.lastrowid

    def decoration(self, data: dict, skills=()) -> int:
        data = dict(data, game_id=self.game)
        cur = self.conn.execute(f"INSERT INTO decorations({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                                list(data.values()))
        self._link_skills("decoration_skills", "decoration_id", cur.lastrowid, skills)
        return cur.lastrowid

    def charm(self, data: dict, skills=()) -> int:
        data = dict(data, game_id=self.game)
        cur = self.conn.execute(f"INSERT INTO charms({','.join(data)}) VALUES ({','.join('?' * len(data))})",
                                list(data.values()))
        self._link_skills("charm_skills", "charm_id", cur.lastrowid, skills)
        return cur.lastrowid
