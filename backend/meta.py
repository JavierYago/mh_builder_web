"""Meta de habilidades: qué le renta a cada clase de arma.

Valores = % aproximado de daño (o de comodidad equivalente) que aporta cada NIVEL de la
habilidad. Se agrupan en:
  * RAW: escalan con el daño bruto del arma.
  * ELEMENT: escalan con la parte elemental (se multiplican por el peso del elemento del arma).
  * UTILITY: comodidad / supervivencia, peso bajo para desempatar.
Los nombres coinciden con los nombres en inglés de cada juego (las variantes se listan todas;
las que no existen en un juego simplemente se ignoran).

Referencias de consenso de la comunidad (guías de builds de World/Iceborne, Rise/Sunbreak y
Wilds): Punto débil, Bonus crítico, Ojo crítico, Agitador y Bonus de ataque son el núcleo de
daño bruto; las armas elementales (Espadas dobles, Arco, Espada y escudo...) priorizan Ataque
de elemento + Elemento crítico; Artesanía/Afilado rápido para armas que dependen del filo.
"""

# Fracción del "valor de movimiento" típico de cada clase: cuanto menor, más pesa el elemento.
MOTION = {"great-sword": 1.0, "long-sword": 0.32, "sword-and-shield": 0.2, "dual-blades": 0.12,
          "hammer": 0.5, "hunting-horn": 0.35, "lance": 0.27, "gunlance": 0.3, "switch-axe": 0.33,
          "charge-blade": 0.33, "insect-glaive": 0.24, "light-bowgun": 0.18, "heavy-bowgun": 0.22, "bow": 0.11}

RANGED = {"light-bowgun", "heavy-bowgun", "bow"}

RAW = {
    "Attack Boost": 2.2, "Critical Eye": 1.3, "Weakness Exploit": 3.6, "Critical Boost": 2.6,
    "Agitator": 2.4, "Peak Performance": 1.6, "Maximum Might": 2.0, "Latent Power": 1.0, "Burst": 2.5,
    "Counterstrike": 1.6, "Offensive Guard": 1.0, "Coalescence": 1.5, "Dereliction": 3.0, "Bloodlust": 2.2,
    "Mail of Hellfire": 2.6, "Chain Crit": 2.0, "Foray": 1.6, "Resentment": 0.6, "Resuscitate": 1.0,
    "Adrenaline Rush": 1.4, "Heroics": 0.9, "Fortify": 0.6, "Non-elemental Boost": 0.0,
    "Ambush": 0.5, "Adrenaline": 0.6, "Convert Element": 0.0, "Antivirus": 2.2, "Frenzy": 1.0,
    "Weakness Exploit/Wex": 0.0, "Agitator Secret": 3.0, "Maximum Might Secret": 1.5,
    "Latent Power Secret": 1.0, "Master's Touch": 0.0, "Dragonheart": 0.6, "Strife": 1.2,
    "Berserk": 1.6, "Inheritance": 3.0, "Transcendance": 4.5, "Dragonvein Awakening": 3.0,
    "True Dragonvein Awakening": 6.0, "Black Eclipse": 2.0, "Arkveld's Hunger": 2.0,
    "Coalescence ": 0.0, "Wind Mantle": 1.5, "Grinder (S)": 1.5, "Status Trigger": 0.5,
    "Power Prolonger": 0.0,
}

ELEMENT = {
    "Fire Attack": 2.6, "Water Attack": 2.6, "Thunder Attack": 2.6, "Ice Attack": 2.6, "Dragon Attack": 2.6,
    "Critical Element": 3.2, "True Critical Element": 3.5, "Elemental Exploit": 3.0, "Element Exploit": 3.0,
    "Element Acceleration": 1.5, "True Element Acceleration": 2.0, "Element Conversion": 3.0,
    "Free Elem/Ammo Up": 0.0, "Fire Alignment": 1.5, "Water Alignment": 1.5, "Thunder Alignment": 1.5,
    "Ice Alignment": 1.5, "Dragon Alignment": 1.5,
}

# Habilidades de comodidad comunes a todas las clases.
UTILITY = {
    "Health Boost": 0.6, "Divine Blessing": 0.3, "Evade Window": 0.5, "Evade Extender": 0.4,
    "Earplugs": 0.5, "Flinch Free": 0.4, "Tremor Resistance": 0.3, "Windproof": 0.15, "Stun Resistance": 0.3,
    "Recovery Up": 0.15, "Recovery Speed": 0.25, "Partbreaker": 0.25, "Speed Eating": 0.1,
    "Constitution": 0.3, "Stamina Surge": 0.3, "Defense Boost": 0.2, "Wirebug Whisperer": 0.3,
    "Wall Runner": 0.05, "Free Meal": 0.05, "Quick Sheathe": 0.15, "Hasten Recovery": 0.4,
    "Guts": 0.4, "Super Recovery": 0.2, "Rajang's Rage": 0.0, "Mind's Eye/Ballistics": 0.8,
    "Protective Polish": 1.5, "Razor Sharp/Spare Shot": 0.5, "Item Prolonger": 0.1, "Blight Resistance": 0.15,
    "Agitator Secret ": 0.0, "Gaia's Veil": 0.3, "True Gaia's Veil": 0.6, "Intimidator": 0.0,
    "Elemental Absorption": 0.0, "Second Wind": 0.4, "Survival Expert": 0.2, "Speed Sharpening": 0.0,
}

# Extras por clase (se suman a lo anterior).
CLASS_EXTRA = {
    "great-sword": {"Focus": 2.0, "Critical Draw": 3.2, "Punishing Draw": 0.8, "Handicraft": 1.2,
                    "Master's Touch": 2.5, "Razor Sharp": 0.6, "Speed Sharpening": 0.3, "Power Prolonger": 0.0,
                    "Slugger": 0.4, "Partbreaker": 0.3},
    "long-sword": {"Handicraft": 1.4, "Master's Touch": 2.6, "Razor Sharp": 0.8, "Speed Sharpening": 0.4,
                   "Evade Window": 0.6, "Critical Draw": 0.3, "Focus": 0.4, "Protective Polish": 0.8},
    "sword-and-shield": {"Handicraft": 1.0, "Master's Touch": 2.0, "Razor Sharp": 1.0, "Speed Sharpening": 0.6,
                         "Guard": 0.3, "Slugger": 0.4},
    "dual-blades": {"Handicraft": 1.0, "Master's Touch": 2.2, "Razor Sharp": 1.2, "Speed Sharpening": 0.6,
                    "Constitution": 0.8, "Stamina Surge": 0.8, "Evade Window": 0.6, "Evade Extender": 0.5,
                    "Power Prolonger": 0.5, "Bladescale Hone": 0.0},
    "hammer": {"Handicraft": 1.1, "Master's Touch": 2.2, "Razor Sharp": 0.6, "Slugger": 0.8, "Focus": 0.8,
               "Speed Sharpening": 0.3, "Punishing Draw": 0.4},
    "hunting-horn": {"Horn Maestro": 1.6, "Handicraft": 1.0, "Master's Touch": 2.0, "Razor Sharp": 0.6,
                     "Slugger": 0.5, "Earplugs": 1.0},
    "lance": {"Guard": 1.6, "Guard Up": 1.4, "Offensive Guard": 2.0, "Handicraft": 1.0, "Master's Touch": 2.2,
              "Razor Sharp": 0.8, "Counterstrike": 0.4},
    "gunlance": {"Artillery": 3.0, "Load Shells": 1.0, "Guard": 1.2, "Guard Up": 0.8, "Offensive Guard": 1.2,
                 "Razor Sharp": 1.6, "Speed Sharpening": 0.6, "Master's Touch": 1.4, "Handicraft": 0.6,
                 "Artillery Secret": 2.0, "Bombardier": 0.0},
    "switch-axe": {"Power Prolonger": 1.2, "Rapid Morph": 1.2, "Handicraft": 1.0, "Master's Touch": 2.0,
                   "Razor Sharp": 0.7, "Focus": 0.4, "Strife": 0.4},
    "charge-blade": {"Artillery": 2.0, "Load Shells": 1.0, "Power Prolonger": 0.6, "Rapid Morph": 1.0,
                     "Guard": 0.8, "Guard Up": 0.4, "Offensive Guard": 1.6, "Focus": 0.8, "Handicraft": 0.8,
                     "Master's Touch": 1.8, "Razor Sharp": 0.6, "Artillery Secret": 1.4},
    "insect-glaive": {"Airborne": 2.4, "Kinsect": 0.0, "Handicraft": 1.0, "Master's Touch": 2.0,
                      "Razor Sharp": 0.8, "Constitution": 0.2},
    "light-bowgun": {"Normal/Rapid Up": 3.6, "Normal Shots": 3.6, "Rapid Fire Up": 3.0, "Pierce Up": 2.6,
                     "Pierce Shots": 2.6, "Spread/Power Shots": 2.0, "Spread Up": 2.0, "Special Ammo Boost": 0.8,
                     "Recoil Down": 1.6, "Reload Speed": 1.6, "Ballistics": 1.0, "Opening Shot": 0.8,
                     "Spare Shot": 0.8, "Razor Sharp/Spare Shot": 0.8, "Evade Extender": 0.6,
                     "Mind's Eye/Ballistics": 1.0, "Ammo Up": 0.0},
    "heavy-bowgun": {"Normal/Rapid Up": 3.4, "Normal Shots": 3.4, "Pierce Up": 3.0, "Pierce Shots": 3.0,
                     "Spread/Power Shots": 3.0, "Spread Up": 3.0, "Special Ammo Boost": 1.2,
                     "Recoil Down": 1.4, "Reload Speed": 1.4, "Ballistics": 1.0, "Opening Shot": 0.8,
                     "Guard": 0.6, "Guard Up": 0.4, "Spare Shot": 0.6, "Razor Sharp/Spare Shot": 0.6,
                     "Mind's Eye/Ballistics": 1.0, "Bombardier": 0.0},
    "bow": {"Normal/Rapid Up": 3.0, "Normal Shots": 3.0, "Rapid Fire Up": 1.0, "Pierce Up": 2.4,
            "Pierce Shots": 2.4, "Spread/Power Shots": 2.4, "Spread Up": 2.4, "Constitution": 1.0,
            "Stamina Surge": 1.0, "Critical Draw": 0.0, "Focus": 0.6, "Ballistics": 0.6, "Opening Shot": 0.4,
            "Bow Charge Plus": 4.0, "Spare Shot": 0.5, "Tetrad Shot": 2.4, "Evade Extender": 0.5,
            "Mind's Eye/Ballistics": 0.8},
}

# Habilidades de afilado no aplican a armas a distancia.
SHARPNESS_SKILLS = {"Handicraft", "Master's Touch", "Razor Sharp", "Speed Sharpening", "Protective Polish",
                    "Mind's Eye/Ballistics", "Bludgeoner", "Masterful Touch"}

# Bonificaciones de set/grupo cuyo efecto no tiene nombre de habilidad estándar
# (Wilds: "Gore Magala's Tyranny" -> "Black Eclipse I"...). Valor por rango activado.
SET_BONUS_VALUE = {
    "Gore Magala's Tyranny": 2.5, "Arkveld's Hunger": 2.2, "Rey Dau's Voltage": 2.4, "Uth Duna's Cover": 1.6,
    "Jin Dahaad's Revolt": 1.8, "Zoh Shia's Pulse": 2.0, "Doshaguma's Might": 2.0, "Ebony Odogaron's Power": 2.2,
    "Fulgur Anjanath's Will": 1.2, "Nu Udra's Mutiny": 2.0, "Guardian Arkveld's Vitality": 1.2,
    "Mizutsune's Prowess": 2.0, "Rathalos's Flare": 1.4, "Seregios's Tenacity": 2.2, "Leviathan's Fury": 2.2,
    "Gogmapocalypse": 3.0, "Soul of the Dark Knight": 2.8, "Omega Resonance": 3.2, "Lord's Soul": 2.0,
    "Lord's Fury": 2.6, "Guardian's Pulse": 1.0, "Guardian's Protection": 0.6, "Scaling Prowess": 1.4,
    "Master of the Fist": 1.0, "Glory's Favor": 0.6, "Lord's Favor": 0.6, "Blangonga's Spirit": 0.8,
    "Gravios's Protection": 0.6, "Xu Wu's Vigor": 0.8,
}

ELEMENT_NAMES = {"fire": "Fire", "water": "Water", "thunder": "Thunder", "ice": "Ice", "dragon": "Dragon"}
STATUS_SKILL = {"poison": "Poison Attack", "paralysis": "Paralysis Attack", "sleep": "Sleep Attack",
                "blast": "Blast Attack"}


def profile(weapon_type: str, element: str | None, elem_share: float) -> dict[str, float]:
    """Pesos finales (por nivel) para un arma concreta."""
    ranged = weapon_type in RANGED
    raw_factor = 1.0 - 0.6 * elem_share
    weights: dict[str, float] = {}
    for k, v in RAW.items():
        weights[k] = v * raw_factor
    e = (element or "").lower()
    if e in ELEMENT_NAMES:
        for k, v in ELEMENT.items():
            if k.split()[0] in ELEMENT_NAMES.values() and not k.startswith(ELEMENT_NAMES[e]):
                continue  # solo el ataque del elemento propio
            weights[k] = v * elem_share * 2.2
        weights["Non-elemental Boost"] = 0.0
    elif e in STATUS_SKILL:
        weights[STATUS_SKILL[e]] = 1.2 * max(elem_share, 0.25)
        weights["Critical Status"] = 0.8 * max(elem_share, 0.25)
    else:
        weights["Non-elemental Boost"] = 3.0 if not ranged else 0.0
    for k, v in UTILITY.items():
        weights[k] = max(weights.get(k, 0.0), v)
    for k, v in CLASS_EXTRA.get(weapon_type, {}).items():
        weights[k] = weights.get(k, 0.0) + v
    if ranged:
        for k in SHARPNESS_SKILLS:
            if k not in CLASS_EXTRA.get(weapon_type, {}):
                weights[k] = 0.0
        weights["Handicraft"] = 0.0
    return {k: v for k, v in weights.items() if v > 0}
