-- Esquema relacional de MH Builder.
-- Jerarquía: juego -> expansión (base / DLC) -> equipo. Cada objeto pertenece a UNA expansión.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS games (
    id          TEXT PRIMARY KEY,          -- world | rise | wilds | outlanders
    name        TEXT NOT NULL,
    subtitle    TEXT,
    year        INTEGER,
    platforms   TEXT,
    has_data    INTEGER NOT NULL DEFAULT 1,
    note        TEXT,
    sort        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS expansions (
    id          TEXT PRIMARY KEY,          -- world-base | world-iceborne ...
    game_id     TEXT NOT NULL REFERENCES games(id),
    name        TEXT NOT NULL,
    rank_label  TEXT NOT NULL,             -- HR | MR
    is_dlc      INTEGER NOT NULL DEFAULT 0,
    min_rarity  INTEGER,
    max_rarity  INTEGER,
    sort        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS weapon_types (
    id          TEXT PRIMARY KEY,          -- great-sword, long-sword ...
    name        TEXT NOT NULL,
    name_en     TEXT NOT NULL,
    ranged      INTEGER NOT NULL DEFAULT 0,
    sort        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS game_weapon_types (
    game_id         TEXT NOT NULL REFERENCES games(id),
    weapon_type_id  TEXT NOT NULL REFERENCES weapon_types(id),
    PRIMARY KEY (game_id, weapon_type_id)
);

CREATE TABLE IF NOT EXISTS skills (
    id          INTEGER PRIMARY KEY,
    game_id     TEXT NOT NULL REFERENCES games(id),
    name        TEXT NOT NULL,             -- nombre en inglés (clave estable)
    name_es     TEXT,
    description TEXT,
    kind        TEXT,                      -- armor | weapon | set | group | secret
    max_level   INTEGER NOT NULL DEFAULT 1,
    secret_levels INTEGER NOT NULL DEFAULT 0, -- niveles que requieren un "Secreto" (World)
    UNIQUE (game_id, name)
);

CREATE TABLE IF NOT EXISTS skill_levels (
    skill_id    INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    level       INTEGER NOT NULL,
    description TEXT,
    PRIMARY KEY (skill_id, level)
);

-- Bonificaciones de set / grupo: se activan por número de piezas.
CREATE TABLE IF NOT EXISTS set_bonuses (
    id          INTEGER PRIMARY KEY,
    game_id     TEXT NOT NULL REFERENCES games(id),
    name        TEXT NOT NULL,
    name_es     TEXT,
    UNIQUE (game_id, name)
);

CREATE TABLE IF NOT EXISTS set_bonus_ranks (
    bonus_id    INTEGER NOT NULL REFERENCES set_bonuses(id) ON DELETE CASCADE,
    pieces      INTEGER NOT NULL,
    skill_name  TEXT NOT NULL,             -- habilidad que otorga
    description TEXT,
    PRIMARY KEY (bonus_id, pieces)
);

CREATE TABLE IF NOT EXISTS weapons (
    id              INTEGER PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(id),
    expansion_id    TEXT NOT NULL REFERENCES expansions(id),
    weapon_type_id  TEXT NOT NULL REFERENCES weapon_types(id),
    source_id       TEXT,
    name            TEXT NOT NULL,
    name_es         TEXT,
    rarity          INTEGER NOT NULL,
    rank            TEXT,                  -- low | high | master
    attack_display  INTEGER,
    attack_raw      REAL,
    affinity        INTEGER DEFAULT 0,
    element         TEXT,
    element_value   REAL,
    element2        TEXT,
    element2_value  REAL,
    element_hidden  INTEGER DEFAULT 0,
    defense_bonus   INTEGER DEFAULT 0,
    elderseal       TEXT,
    slots           TEXT NOT NULL DEFAULT '[]',   -- JSON [3,1]
    sharpness       TEXT,                          -- JSON {red:..}
    sharpness_max   TEXT,                          -- JSON con Artesanía al máximo
    extra           TEXT,                          -- JSON (fial, munición, notas...)
    previous_name   TEXT,
    image_url       TEXT,
    image_local     TEXT
);
CREATE INDEX IF NOT EXISTS ix_weapons_lookup ON weapons(game_id, weapon_type_id, rarity);

CREATE TABLE IF NOT EXISTS weapon_skills (
    weapon_id   INTEGER NOT NULL REFERENCES weapons(id) ON DELETE CASCADE,
    skill_id    INTEGER NOT NULL REFERENCES skills(id),
    level       INTEGER NOT NULL,
    PRIMARY KEY (weapon_id, skill_id)
);

CREATE TABLE IF NOT EXISTS armor_sets (
    id              INTEGER PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(id),
    expansion_id    TEXT NOT NULL REFERENCES expansions(id),
    name            TEXT NOT NULL,
    name_es         TEXT,
    rank            TEXT,
    rarity          INTEGER,
    bonus_id        INTEGER REFERENCES set_bonuses(id),
    group_bonus_id  INTEGER REFERENCES set_bonuses(id)
);

CREATE TABLE IF NOT EXISTS armor_pieces (
    id              INTEGER PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(id),
    expansion_id    TEXT NOT NULL REFERENCES expansions(id),
    set_id          INTEGER REFERENCES armor_sets(id),
    source_id       TEXT,
    kind            TEXT NOT NULL,         -- head | chest | arms | waist | legs
    name            TEXT NOT NULL,
    name_es         TEXT,
    rarity          INTEGER NOT NULL,
    rank            TEXT,
    defense_base    INTEGER,
    defense_max     INTEGER,
    res_fire        INTEGER DEFAULT 0,
    res_water       INTEGER DEFAULT 0,
    res_thunder     INTEGER DEFAULT 0,
    res_ice         INTEGER DEFAULT 0,
    res_dragon      INTEGER DEFAULT 0,
    slots           TEXT NOT NULL DEFAULT '[]',
    image_url       TEXT,
    image_url_f     TEXT,
    image_local     TEXT
);
CREATE INDEX IF NOT EXISTS ix_armor_lookup ON armor_pieces(game_id, kind, rarity);

CREATE TABLE IF NOT EXISTS armor_skills (
    piece_id    INTEGER NOT NULL REFERENCES armor_pieces(id) ON DELETE CASCADE,
    skill_id    INTEGER NOT NULL REFERENCES skills(id),
    level       INTEGER NOT NULL,
    PRIMARY KEY (piece_id, skill_id)
);

CREATE TABLE IF NOT EXISTS decorations (
    id              INTEGER PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(id),
    expansion_id    TEXT NOT NULL REFERENCES expansions(id),
    source_id       TEXT,
    name            TEXT NOT NULL,
    name_es         TEXT,
    rarity          INTEGER,
    slot            INTEGER NOT NULL,
    kind            TEXT NOT NULL DEFAULT 'any',   -- any | armor | weapon
    color           TEXT
);

CREATE TABLE IF NOT EXISTS decoration_skills (
    decoration_id   INTEGER NOT NULL REFERENCES decorations(id) ON DELETE CASCADE,
    skill_id        INTEGER NOT NULL REFERENCES skills(id),
    level           INTEGER NOT NULL,
    PRIMARY KEY (decoration_id, skill_id)
);

CREATE TABLE IF NOT EXISTS charms (
    id              INTEGER PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(id),
    expansion_id    TEXT NOT NULL REFERENCES expansions(id),
    name            TEXT NOT NULL,
    name_es         TEXT,
    rarity          INTEGER
);

CREATE TABLE IF NOT EXISTS charm_skills (
    charm_id    INTEGER NOT NULL REFERENCES charms(id) ON DELETE CASCADE,
    skill_id    INTEGER NOT NULL REFERENCES skills(id),
    level       INTEGER NOT NULL,
    PRIMARY KEY (charm_id, skill_id)
);

-- Escalones de progresión: rango mínimo a partir del cual cambia el equipo disponible.
CREATE TABLE IF NOT EXISTS progression_tiers (
    id              INTEGER PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(id),
    expansion_id    TEXT NOT NULL REFERENCES expansions(id),
    rank_label      TEXT NOT NULL,
    min_rank        INTEGER NOT NULL,
    max_rarity      INTEGER NOT NULL,
    deco_max_rarity INTEGER,
    deco_max_slot   INTEGER,
    title           TEXT NOT NULL,
    description     TEXT,
    monsters        TEXT,                  -- JSON lista de monstruos que aparecen
    exclude         TEXT,                  -- JSON palabras clave excluidas hasta este rango
    sort            INTEGER NOT NULL
);

-- Builds precalculadas por (expansión, escalón, tipo de arma).
CREATE TABLE IF NOT EXISTS builds (
    id              INTEGER PRIMARY KEY,
    game_id         TEXT NOT NULL,
    expansion_id    TEXT NOT NULL,
    tier_id         INTEGER NOT NULL REFERENCES progression_tiers(id),
    weapon_type_id  TEXT NOT NULL,
    score           REAL,
    data            TEXT NOT NULL,         -- JSON con la build completa
    UNIQUE (tier_id, weapon_type_id)
);

-- Monstruos: zonas de golpe, debilidades, amenazas y rangos en que aparecen.
CREATE TABLE IF NOT EXISTS monsters (
    id          INTEGER PRIMARY KEY,
    game_id     TEXT NOT NULL REFERENCES games(id),
    source_id   TEXT,
    name        TEXT NOT NULL,
    name_es     TEXT,
    species     TEXT,
    ranks       TEXT NOT NULL DEFAULT '[]',   -- JSON ["low","high","master"]
    threats     TEXT NOT NULL DEFAULT '[]',   -- JSON códigos de monster_threats
    threats_source TEXT,                      -- datos | estimado
    icon_url    TEXT,
    icon_local  TEXT,
    variant_of  INTEGER REFERENCES monsters(id),  -- variante especial de otro monstruo (p. ej. Kirin sin cuerno)
    variant_label TEXT,                           -- "Sin cuerno · Orgullo esterlino"
    notes       TEXT NOT NULL DEFAULT '[]',       -- JSON: notas de la misión / estado especial
    UNIQUE (game_id, name)
);

CREATE TABLE IF NOT EXISTS monster_hitzones (
    monster_id  INTEGER NOT NULL REFERENCES monsters(id) ON DELETE CASCADE,
    part        TEXT NOT NULL,
    cut         REAL, impact REAL, shot REAL,
    fire REAL, water REAL, thunder REAL, ice REAL, dragon REAL,
    stun        REAL
);

CREATE TABLE IF NOT EXISTS monster_weaknesses (
    monster_id  INTEGER NOT NULL REFERENCES monsters(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,                 -- element | status
    name        TEXT NOT NULL,                 -- fire... | poison, sleep, paralysis, blast, stun
    stars       INTEGER NOT NULL,              -- 0..3
    PRIMARY KEY (monster_id, kind, name)
);
