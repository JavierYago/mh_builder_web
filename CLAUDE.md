# Contexto Global del Proyecto: Monster Hunter Web Builder

## Objetivo
Desarrollar una aplicación web interactiva que sirva como guía y creador de builds (equipamiento) para la saga Monster Hunter. Los juegos incluidos en esta versión son: Monster Hunter World (y DLC Iceborne), Monster Hunter Rise (y DLC Sunbreak), Monster Hunter Wilds, y Monster Hunter Outlanders.

## Stack Tecnológico Principal
* **Backend y Extracción de Datos (Scraping/API):** Python.
* **Frontend:** HTML, CSS y JavaScript puro (enfocado en una UI/UX muy visual y temática, evitando botones genéricos).
* **Base de Datos:** Estructura relacional para gestionar la interconexión entre juegos, armas, armaduras y habilidades.

## Reglas de Negocio (Core Logic)
1. **Jerarquía de Datos:** Toda la información (armas, armaduras, adornos, habilidades, imágenes) debe estar estrictamente categorizada por Juego y por DLC (ej. el contenido de Iceborne no debe mezclarse con el de World base a menos que el jugador esté en el rango correspondiente).
2. **Sistema de Rangos (Rango de Cazador - HR/MR):** Las builds mostradas deben estar limitadas por el rango exacto del jugador. No se debe recomendar equipamiento de HR 30 a un jugador de HR 5. Si no hay mejoras disponibles entre dos rangos consecutivos, se mantiene la build del rango anterior.
3. **Lógica de Construcción de Builds:** El algoritmo de recomendación debe priorizar los "sets mixtos" (combinar partes de diferentes monstruos) sobre las armaduras completas para maximizar habilidades clave según la clase de arma (ej. daño elemental o filo en Espadas Dobles).
4. **Seguridad y Buenas Prácticas:** Toda clave, credencial o variable sensible debe ir obligatoriamente en un archivo `.env` y nunca exponerse en el código fuente.
