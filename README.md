# 🐉 Monster Hunter Build Crafter & Guide

An interactive, full-stack web application designed to serve as a comprehensive guide and dynamic build optimizer for the Monster Hunter franchise. This tool currently supports *Monster Hunter World (Iceborne)*, *Monster Hunter Rise (Sunbreak)*, *Monster Hunter Wilds*, and *Monster Hunter Outlanders*.

## 🎯 Core Features

* **Hunter Rank (HR/MR) Progression System:** Filters available equipment and recommends optimal builds based strictly on the player's current progression level. It ensures users only see gear they can actually craft at their exact stage in the game.
* **Smart Build Recommender:** The algorithm prioritizes mixed armor sets over full monster sets to maximize crucial weapon-specific skills (e.g., Elemental Damage, Sharpness, Affinity for Dual Blades, etc.).
* **Comprehensive Database:** A meticulously structured catalog of weapons, armor pieces, decorations, and skills, strictly segregated by base game and expansions (DLCs).
* **Thematic UI/UX:** A highly interactive, custom-designed frontend tailored to the Monster Hunter aesthetic, focusing on smooth navigation through different weapon classes and progression tiers.

## 🛠️ Tech Stack

* **Frontend:** HTML5, CSS3, and Vanilla JavaScript.
* **Backend & Data Extraction:** Python (Data processing and API consumption/Web Scraping).
* **Database:** Relational Database model to handle the complex many-to-many relationships between armor pieces, decorations, and skills.
* **Security:** Strict management of sensitive data and credentials using environment variables (`.env`).

## 🚀 Getting Started

Requirements: Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
copy .env.example .env            # cp on Linux/macOS — edit values if needed
python -m backend.pipeline        # downloads all data into SQLite and precomputes builds (~8 min)
python -m backend.app             # http://127.0.0.1:8000
```

Useful pipeline flags: `--games world rise` (reload only some games), `--builds-only` (recompute builds
without downloading), `--images` (cache every remote image locally in `data/images`).

### Project layout

| Path | Purpose |
|------|---------|
| `backend/scrapers/` | One loader per game: World + Iceborne (MHWorldData CSVs + mhw-db images), Rise + Sunbreak (Kiranico), Wilds (mhdb API) |
| `backend/schema.sql` | Relational schema: game → expansion → weapons / armor / decorations / charms / skills / set bonuses |
| `backend/catalog.py` | Games, DLCs, weapon classes and the **rank progression tiers** (which rarity unlocks at which HR/MR) |
| `backend/meta.py` | Skill weights per weapon class (what each weapon wants: raw, element, sharpness, ammo…) |
| `backend/optimizer.py` | Build generator: weapon damage model + beam search over armor pieces + greedy decoration fill |
| `backend/app.py` | FastAPI JSON API + static frontend server (read-only DB, CSP and security headers) |
| `frontend/` | Vanilla HTML/CSS/JS single-page app |

### Data sources

* World / Iceborne: [MHWorldData](https://github.com/gatheringhallstudios/MHWorldData) (incl. Spanish names) and [mhw-db.com](https://mhw-db.com) for images.
* Rise / Sunbreak: [mhrise.kiranico.com](https://mhrise.kiranico.com) (English + Spanish pages).
* Wilds: [wilds.mhdb.io](https://wilds.mhdb.io) (English + Spanish).
* Outlanders: no public database exists yet (game launched 29 Oct 2026); the game and its 8 weapon classes are registered and ready for a loader.

### Hunt mode (build against a monster)

`#/caceria` lets you pick a monster (183 across World/Iceborne, Rise/Sunbreak and Wilds), the quest rank
(low / high / master) and a weapon class; `/api/hunt/{monster}?rank=&weapon=` computes the build on demand
(cached in memory, < 1 s).

* Monster data (`backend/scrapers/monsters.py`): hitzones per part, elemental/status weaknesses, ranks it
  appears in (from reward tables), icon. World from MHWorldData, Rise from Kiranico, Wilds from mhdb.
* The optimizer receives the monster's weak-point hitzones (average of its 3 best parts per damage type
  and element) instead of generic values, so the weapon element and raw/element balance adapt to it.
  Weakness Exploit loses value if the monster has no ≥45 hitzone (World/Rise).
* Defensive skills (Earplugs, Windproof, resistances…) are valued according to what the monster does.
  World has this data; for Rise/Wilds-exclusive monsters it comes from a hand-written table
  (`backend/monster_threats.py`, flagged as "estimado" in the UI).
* Quest rank sets the gear cap; the optional player HR/MR (`&hr=`) narrows it to the progression tier the
  player has reached (same tiers as the rank builds). It warns if the HR/MR is below the quest's minimum.
* Special encounters are stored as variants of a monster (`VARIANTS` in `monsters.py`), e.g. Iceborne's
  "Sterling Pride" Kirin: horn already broken, permanently enraged (charged body hitzones), 13,400 HP vs 21,440
  and x11.30 attack vs x10.50 (parsed from Kiranico's quest table).

### Images

* World / Iceborne weapons: 4K renders from mhworld.kiranico.com, served through `/thumb` (downloaded once, cropped to the weapon and cached as 256 px WebP in `data/images/thumbs`; host whitelisted).
* Wilds weapons and armor: mhwilds.kiranico.com thumbnails. Rise: Kiranico. World base armor: mhw-db.
* Every image is validated (exists, decodes, not blank) and stored locally in `data/images`, so the site never depends on hotlinks.
* Gaps are filled from the Fextralife wikis: weapon/piece pages, and for Iceborne armor each piece is cropped from the full-set render.
* The ~1.5% with no public image anywhere (mostly Rise collab/event gear) show the weapon class icon or the piece silhouette tinted by rarity; failed loads fall back the same way in the browser.

### Known limitations

* Progression tiers are mapped by rarity per rank milestone (see `backend/catalog.py`), not per individual item unlock.
* Random-roll gear is excluded from recommendations (Kulve Taroth weapons, Rise talismans, Wilds random charms).
* Rise rampage slots/decorations are not used by the optimizer.
