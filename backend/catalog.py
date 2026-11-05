"""Datos estáticos: juegos, expansiones, tipos de arma y escalones de progresión.

Los escalones de progresión definen, para cada expansión, a partir de qué rango (HR/MR)
se desbloquea equipo de una rareza mayor. Son una aproximación basada en la estructura de
cada juego (rareza ligada a estrellas de misión y topes de rango) y se pueden ajustar aquí.
Si entre dos escalones la mejor build no cambia, el pipeline los fusiona automáticamente.
"""

GAMES = [
    dict(id="world", name="Monster Hunter: World", subtitle="El Nuevo Mundo", year=2018,
         platforms="PS4 · Xbox One · PC", has_data=1, sort=1, note=None),
    dict(id="rise", name="Monster Hunter Rise", subtitle="Aldea Kamura", year=2021,
         platforms="Switch · PC · PS · Xbox", has_data=1, sort=2, note=None),
    dict(id="wilds", name="Monster Hunter Wilds", subtitle="Las Tierras Prohibidas", year=2025,
         platforms="PS5 · Xbox Series · PC", has_data=1, sort=3, note=None),
    dict(id="outlanders", name="Monster Hunter Outlanders", subtitle="Supervivencia en mundo abierto", year=2026,
         platforms="iOS · Android", has_data=0, sort=4,
         note="Lanzado el 29/10/2026. Aún no existe ninguna base de datos pública de su equipo; "
              "en cuanto aparezca una fuente fiable se podrá cargar con el mismo pipeline."),
]

EXPANSIONS = [
    dict(id="world-base", game_id="world", name="World", rank_label="HR", is_dlc=0, min_rarity=1, max_rarity=8, sort=1),
    dict(id="world-iceborne", game_id="world", name="Iceborne", rank_label="MR", is_dlc=1, min_rarity=9, max_rarity=12, sort=2),
    dict(id="rise-base", game_id="rise", name="Rise", rank_label="HR", is_dlc=0, min_rarity=1, max_rarity=7, sort=1),
    dict(id="rise-sunbreak", game_id="rise", name="Sunbreak", rank_label="MR", is_dlc=1, min_rarity=8, max_rarity=10, sort=2),
    dict(id="wilds-base", game_id="wilds", name="Wilds", rank_label="HR", is_dlc=0, min_rarity=1, max_rarity=8, sort=1),
    dict(id="outlanders-base", game_id="outlanders", name="Outlanders", rank_label="HR", is_dlc=0, min_rarity=None, max_rarity=None, sort=1),
]

# (id, nombre ES, nombre EN, a distancia)
WEAPON_TYPES = [
    ("great-sword", "Gran espada", "Great Sword", 0),
    ("long-sword", "Espada larga", "Long Sword", 0),
    ("sword-and-shield", "Espada y escudo", "Sword & Shield", 0),
    ("dual-blades", "Espadas dobles", "Dual Blades", 0),
    ("hammer", "Martillo", "Hammer", 0),
    ("hunting-horn", "Cornamusa", "Hunting Horn", 0),
    ("lance", "Lanza", "Lance", 0),
    ("gunlance", "Lanza pistola", "Gunlance", 0),
    ("switch-axe", "Hacha espada", "Switch Axe", 0),
    ("charge-blade", "Hacha cargada", "Charge Blade", 0),
    ("insect-glaive", "Glaive insecto", "Insect Glaive", 0),
    ("light-bowgun", "Ballesta ligera", "Light Bowgun", 1),
    ("heavy-bowgun", "Ballesta pesada", "Heavy Bowgun", 1),
    ("bow", "Arco", "Bow", 1),
]

# Outlanders: armas confirmadas en el lanzamiento (web oficial + Charge Blade anunciado).
OUTLANDERS_WEAPONS = ["great-sword", "long-sword", "dual-blades", "hammer", "lance",
                      "heavy-bowgun", "bow", "charge-blade"]


def _t(rank, rarity, title, desc, monsters, deco_rarity=None, deco_slot=None, exclude=()):
    return dict(min_rank=rank, max_rarity=rarity, title=title, description=desc,
                monsters=monsters, deco_max_rarity=deco_rarity, deco_max_slot=deco_slot,
                exclude=list(exclude))


PROGRESSION = {
    "world-base": [
        _t(1, 2, "Primeros pasos · Rango Bajo", "Misiones de 1★ y 2★. Equipo de hueso, aleaciones y los primeros monstruos del Bosque Primigenio.",
           ["Gran Jagras", "Kulu-Ya-Ku", "Pukei-Pukei", "Barroth", "Jyuratodus", "Tobi-Kadachi"], deco_rarity=0),
        _t(3, 3, "Rango Bajo · 3★", "Se abren el Yermo de Agujas y las Tierras Altas Coralinas.",
           ["Anjanath", "Rathian", "Paolumu", "Great Girros", "Tzitzi-Ya-Ku"], deco_rarity=0),
        _t(6, 4, "Final del Rango Bajo", "Misiones de 4★ y 5★ hasta Zorah Magdaros.",
           ["Legiana", "Odogaron", "Radobaan", "Rathalos", "Diablos", "Zorah Magdaros"], deco_rarity=0),
        _t(9, 5, "Inicio del Rango Alto", "Comienza el Rango Alto (6★): equipo de rareza 5 y primeros adornos.",
           ["Kulu-Ya-Ku", "Pukei-Pukei", "Anjanath", "Rathian", "Legiana", "Odogaron"], deco_rarity=6),
        _t(16, 6, "Rango Alto · tope HR 15 superado", "Tras superar el primer tope de rango aparecen Nergigante, Kirin y las variantes.",
           ["Nergigante", "Kirin", "Uragaan", "Lavasioth", "Bazelgeuse", "Black Diablos", "Azure Rathalos", "Pink Rathian"], deco_rarity=6),
        _t(30, 7, "Dragones Ancianos", "Tras el tope de HR 29 llegan los Dragones Ancianos y Deviljho.",
           ["Teostra", "Kushala Daora", "Vaal Hazak", "Deviljho", "Lunastra"], deco_rarity=7),
        _t(50, 8, "Endgame · Templados", "Tras Xeno'jiiva y el tope de HR 49: monstruos templados, Kulve Taroth y equipo de rareza 8.",
           ["Xeno'jiiva", "Kulve Taroth", "Behemoth", "Templados"], deco_rarity=8),
    ],
    "world-iceborne": [
        _t(1, 9, "Rango Maestro · inicio", "Llegada a la Fuente de los Susurros: equipo de rareza 9.",
           ["Banbaro", "Beotodus", "Viper Tobi-Kadachi", "Nightshade Paolumu", "Coral Pukei-Pukei", "Velkhana"], deco_rarity=10),
        _t(6, 10, "Rango Maestro · 2★-3★", "Vuelven los clásicos: Tigrex, Nargacuga, Glavenus y Brachydios.",
           ["Tigrex", "Nargacuga", "Glavenus", "Brachydios", "Shrieking Legiana", "Fulgur Anjanath"], deco_rarity=11),
        _t(15, 11, "Rango Maestro · final de la historia", "Ruiner Nergigante, Namielle y los Dragones Ancianos de Rango Maestro.",
           ["Ruiner Nergigante", "Namielle", "Rajang", "Stygian Zinogre", "Savage Deviljho"], deco_rarity=12),
        _t(24, 12, "Endgame · Tierras Guía", "Tras Shara Ishvalda: Tierras Guía, Safi'jiiva, Alatreon y Raging Brachydios.",
           ["Shara Ishvalda", "Safi'jiiva", "Alatreon", "Raging Brachydios", "Gold Rathian", "Silver Rathalos"],
           deco_rarity=12, exclude=["Fatalis"]),
        _t(100, 12, "MR 100 · Fatalis", "El Dragón Negro: equipo de Fatalis, lo mejor del juego.",
           ["Fatalis"], deco_rarity=12),
    ],
    "rise-base": [
        _t(1, 1, "Rango Bajo · 1★", "Primeras misiones de la Sala de Reunión.",
           ["Great Izuchi", "Arzuros", "Lagombi", "Kulu-Ya-Ku"], deco_slot=1),
        _t(2, 2, "Rango Bajo · 2★", "Misiones de 2★ con nuevos monstruos.",
           ["Aknosom", "Tetranadon", "Barroth", "Khezu", "Royal Ludroth", "Bishaten"], deco_slot=2),
        _t(3, 3, "Rango Bajo · 3★", "Final del Rango Bajo hasta Magnamalo.",
           ["Magnamalo", "Rathian", "Mizutsune", "Tobi-Kadachi", "Zinogre", "Anjanath"], deco_slot=2),
        _t(4, 4, "Rango Alto · 4★", "Comienza el Rango Alto.",
           ["Pukei-Pukei", "Basarios", "Nargacuga", "Goss Harag"], deco_slot=3),
        _t(5, 5, "Rango Alto · 5★", "Monstruos de mayor nivel y equipo de rareza 5.",
           ["Tigrex", "Almudron", "Diablos", "Rathalos", "Rajang"], deco_slot=3),
        _t(6, 6, "Rango Alto · 6★", "Dragones Ancianos en la Sala.",
           ["Kushala Daora", "Teostra", "Chameleos", "Apex"], deco_slot=3),
        _t(7, 7, "Endgame · 7★", "Thunder Serpent Narwa, Allmother Narwa y equipo de rareza 7.",
           ["Thunder Serpent Narwa", "Allmother Narwa", "Valstrax", "Apex"], deco_slot=3),
    ],
    "rise-sunbreak": [
        _t(1, 8, "Rango Maestro · inicio", "Llegada a Elgado: equipo de rareza 8.",
           ["Garangolm", "Lunagaron", "Blood Orange Bishaten", "Daimyo Hermitaur"], deco_slot=4),
        _t(3, 9, "Rango Maestro · 3★-6★", "La historia de Sunbreak avanza: equipo de rareza 9.",
           ["Malzeno", "Seregios", "Astalos", "Gore Magala", "Shagaru Magala", "Espinas"], deco_slot=4),
        _t(10, 10, "Endgame · Rango Maestro", "Tras Gaismagorm: equipo de rareza 10, Amatsu y Malzeno Primigenio.",
           ["Gaismagorm", "Amatsu", "Primordial Malzeno", "Lucent Nargacuga", "Furious Rajang"], deco_slot=4),
        _t(70, 10, "Valstrax de Rango Maestro (MR 70)", "Valstrax Resplandor Carmesí en Rango Maestro: su set «Eclipse» "
           "y sus materiales, necesarios para las últimas mejoras de muchas armas.",
           ["Crimson Glow Valstrax"], deco_slot=4),
        _t(100, 10, "Magnamalo Escarnecido (MR 100)", "Set Rencor Siniestro y armas del Magnamalo Escarnecido; "
           "se abren las investigaciones de anomalías.", ["Scorned Magnamalo", "Afflicted"], deco_slot=4),
        _t(110, 10, "Chameleos Elevado (MR 110)", "Primer Dragón Anciano Elevado: set Mizuha Elevado.",
           ["Risen Chameleos"], deco_slot=4),
        _t(120, 10, "Kushala Daora Elevado (MR 120)", "Set Kushala Elevado.", ["Risen Kushala Daora"], deco_slot=4),
        _t(140, 10, "Teostra Elevado (MR 140)", "Set Káiser Elevado.", ["Risen Teostra"], deco_slot=4),
        _t(160, 10, "Valstrax Elevado (MR 160)", "Set Valstrax «Época».", ["Risen Crimson Glow Valstrax"], deco_slot=4),
        _t(180, 10, "Shagaru Magala Elevado (MR 180)", "Sets Virtud y Prudencia: el último equipo de Sunbreak.",
           ["Risen Shagaru Magala"], deco_slot=4),
    ],
    "wilds-base": [
        _t(1, 2, "Rango Bajo · inicio", "Llanuras Azotavientos y primeros monstruos.",
           ["Chatacabra", "Quematrice", "Lala Barina", "Congalala"], deco_rarity=3),
        _t(4, 3, "Rango Bajo · capítulo 2", "Bosque Escarlata y Cuenca Petrolera.",
           ["Rompopolo", "Balahara", "Doshaguma", "Hirabami"], deco_rarity=4),
        _t(8, 4, "Final del Rango Bajo", "Rey Dau, Uth Duna y Nu Udra.",
           ["Rey Dau", "Uth Duna", "Nu Udra", "Ajarakan", "Guardian Rathalos"], deco_rarity=4),
        _t(10, 5, "Rango Alto · inicio", "Comienza el Rango Alto: equipo alfa de rareza 5.",
           ["Yian Kut-Ku", "Gypceros", "Nerscylla", "Congalala"], deco_rarity=5),
        _t(14, 6, "Rango Alto · medio", "Equipo de rareza 6 de los monstruos de Rango Alto.",
           ["Xu Wu", "Gravios", "Blangonga", "Guardian Ebony Odogaron", "Mizutsune"], deco_rarity=6),
        _t(18, 7, "Rango Alto · final de la historia", "Jin Dahaad, Gore Magala y los Guardianes.",
           ["Jin Dahaad", "Gore Magala", "Rey Dau", "Uth Duna", "Nu Udra"], deco_rarity=7),
        _t(21, 8, "Arkveld y post-historia", "Arkveld y el primer equipo de rareza 8.",
           ["Arkveld", "Guardian Arkveld", "Zoh Shia"], deco_rarity=7,
           exclude=["γ", "Gogmazios", "Omega", "Artian", "Lagiacrus", "Seregios", "Gelidron", "Dragonking"]),
        _t(41, 8, "Endgame · HR 41+", "Templados, Arch-templados, armas Artian y monstruos de las actualizaciones.",
           ["Templados", "Arch-tempered", "Lagiacrus", "Seregios", "Omega Planetes", "Gogmazios"], deco_rarity=7),
    ],
}
