import { classIcon, MONSTERS, ARMOR_ICONS, CHARM_ICON, JEWEL_ICON, UNKNOWN_MONSTER, LOCK } from "./icons.js?v=5";

// ------------------------------------------------------------------ utilidades
const $app = document.getElementById("app");
const cache = new Map();

async function api(path) {
  if (cache.has(path)) return cache.get(path);
  const p = fetch(path).then(async (r) => {
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Error ${r.status}`);
    return r.json();
  });
  cache.set(path, p);
  p.catch(() => cache.delete(path));
  return p;
}

const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nm = (o) => esc(o?.name_es || o?.name || "");
const IMG_HOSTS = /^https:\/\/(assets\.mhw-db\.com|cdn\.kiranico\.net|mhwilds\.kiranico\.net)\//;
const HEAVY = /^https:\/\/cdn\.kiranico\.net\/file\/kiranico\/mhworld-web\/images\/wp\/factory\//;
const safeImg = (u) => {
  if (typeof u !== "string") return null;
  if (HEAVY.test(u)) return `/thumb?src=${encodeURIComponent(u)}`; // render 4K -> miniatura local
  return IMG_HOSTS.test(u) || u.startsWith("/images/") ? u : null;
};
const img = (u, cls = "", alt = "") => {
  const s = safeImg(u);
  return s ? `<img src="${esc(s)}" class="${cls}" alt="${esc(alt)}" loading="lazy" referrerpolicy="no-referrer">` : "";
};
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* sin almacenamiento */ } },
};
const rc = (r) => `r${Math.max(1, Math.min(r || 1, 12))}`;

const ELEMENTS = {
  fire: ["Fuego", "var(--sharpness-red)"], water: ["Agua", "var(--sharpness-blue)"], thunder: ["Rayo", "var(--sharpness-yellow)"],
  ice: ["Hielo", "var(--sharpness-white)"], dragon: ["Dragón", "var(--sharpness-purple)"], poison: ["Veneno", "var(--sharpness-purple)"],
  paralysis: ["Parálisis", "var(--sharpness-yellow)"], sleep: ["Sueño", "var(--sharpness-blue)"], blast: ["Nitro", "var(--sharpness-orange)"],
};
const KIND_ES = { head: "Casco", chest: "Peto", arms: "Brazales", waist: "Faja", legs: "Grebas", weapon: "Arma" };
const SHARP_ORDER = ["red", "orange", "yellow", "green", "blue", "white", "purple"];
const JEWEL_COLORS = { violet: "var(--sharpness-purple)", purple: "var(--sharpness-purple)", red: "var(--sharpness-red)", orange: "var(--sharpness-orange)",
  yellow: "var(--sharpness-yellow)", green: "var(--sharpness-green)", darkgreen: "var(--sharpness-green)", emerald: "var(--sharpness-green)",
  blue: "var(--sharpness-blue)", darkblue: "var(--sharpness-blue)", lightblue: "var(--sharpness-blue)", white: "var(--sharpness-white)",
  gray: "var(--sharpness-white)", grey: "var(--sharpness-white)", pink: "var(--sharpness-red)", rose: "var(--sharpness-red)",
  lightbeige: "var(--sharpness-yellow)", beige: "var(--sharpness-yellow)", gold: "var(--sharpness-yellow)", lemon: "var(--sharpness-yellow)" };
const jewelColor = (c) => JEWEL_COLORS[String(c || "").toLowerCase().replace(/[^a-z]/g, "")] || "var(--sharpness-blue)";

function elem(e, v, hidden) {
  if (!e || !v) return "";
  const [es, col] = ELEMENTS[String(e).toLowerCase()] || [e, "var(--text)"];
  return `<span class="stat">${esc(es)} <b style="color:${col}">${hidden ? "(" : ""}${esc(v)}${hidden ? ")" : ""}</b></span>`;
}

function sharpness(s) {
  if (!s) return "";
  const parts = SHARP_ORDER.filter((k) => s[k] > 0);
  return `<div class="sharpness" title="Afilado">${parts.map((k) => `<i class="s-${k}" style="flex:${s[k]}"></i>`).join("")}</div>`;
}

// Huecos: rombos vacíos o engarzados (con el color del adorno).
function slots(sizes, decos = []) {
  if (!sizes?.length) return "";
  const pool = [...decos];
  return `<span class="slots">${sizes.map((lv) => {
    const i = pool.findIndex((d) => d.size === lv);
    const d = i >= 0 ? pool.splice(i, 1)[0] : null;
    const filled = d && d.id;
    const title = filled ? `${d.name_es || d.name} (${(d.skills || []).map((s) => `${s.name_es || s.name} +${s.level}`).join(", ")})` : `Hueco nivel ${lv} libre`;
    return `<i class="slot lv${lv} ${filled ? "filled" : ""}" data-lv="${lv}" title="${esc(title)}" ${filled ? `style="--jewel:${jewelColor(d.color)}"` : ""}></i>`;
  }).join("")}</span>`;
}

function fallbackIcon(type, kind) {
  return type ? img(classIcon(type), "class-icon") : kind === "charm" ? CHARM_ICON : ARMOR_ICONS[kind] || JEWEL_ICON;
}

function iconFrame({ image, rarity, type, kind, size = "" }) {
  const main = img(image);
  const fb = `data-fb-type="${esc(type || "")}" data-fb-kind="${esc(kind || "")}"`;
  return `<div class="icon-frame ${size} ${rc(rarity)}" ${fb}>${main || fallbackIcon(type, kind)}</div>`;
}

// Si una imagen falla al cargar, se sustituye por el icono de clase o la silueta de la pieza.
document.addEventListener("error", (e) => {
  const el = e.target;
  if (!(el instanceof HTMLImageElement)) return;
  const frame = el.closest(".icon-frame");
  if (frame && !el.classList.contains("class-icon")) {
    frame.innerHTML = fallbackIcon(frame.dataset.fbType, frame.dataset.fbKind);
  } else if (el.closest(".poster-monster")) {
    el.replaceWith(Object.assign(document.createElement("span"), { innerHTML: UNKNOWN_MONSTER }));
  } else {
    el.style.visibility = "hidden";
  }
}, true);

const unlockTag = (o) => (o?.unlock_note ? `<span class="unlock-tag" title="${esc(o.unlock_note)}">${esc((o.unlock_note.match(/MR \d+/) || ["MR"])[0])}</span>` : "");
const rarTag = (r) => `<span class="rar-tag ${rc(r)}">Rareza ${esc(r ?? "?")}</span>`;
const loader = () => `<div class="loader"><i></i></div>`;
const rule = () => `<div class="rule"><i></i></div>`;

function crumbs(items) {
  return `<nav class="crumbs">${items.map(([t, h], i) => (h ? `<a href="${h}">${esc(t)}</a>` : `<span>${esc(t)}</span>`) + (i < items.length - 1 ? "<span>›</span>" : "")).join("")}</nav>`;
}

const games = () => api("/api/games");
function setNav(key) { document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === key)); }
function setGameTheme(id) { if (id) document.body.dataset.game = id; else delete document.body.dataset.game; }

// ------------------------------------------------------------------ landing: tablón de misiones
const STARS = { world: 8, rise: 7, wilds: 8, outlanders: 1 };

function posterHtml(g) {
  const mon = MONSTERS[g.id];
  const weapons = g.expansions.reduce((a, e) => a + (e.counts?.weapons || 0), 0);
  const armor = g.expansions.reduce((a, e) => a + (e.counts?.armor || 0), 0);
  const ranks = g.expansions.map((e) => `${e.name} (${e.rank_label})`).join(" · ");
  const tag = g.has_data ? "a" : "div";
  return `<${tag} class="poster tex-parchment ${g.has_data ? "" : "unavailable"}" data-game="${esc(g.id)}" ${g.has_data ? `href="#/game/${esc(g.id)}"` : 'tabindex="0"'}>
    <span class="pin"></span>
    <div class="poster-kind">MISIÓN DE CAZA</div>
    <div class="poster-stars">${"★".repeat(STARS[g.id] || 1)}</div>
    <div class="poster-monster">${mon?.img ? img(mon.img, "", mon.name) : UNKNOWN_MONSTER}</div>
    <h3>${esc(g.name)}</h3>
    <div class="poster-sub">${esc(g.subtitle)}</div>
    <dl class="quest-fields">
      <dt>Objetivo</dt><dd>${mon?.img ? `Cazar a ${esc(mon.name)} y forjar tu build` : "Esperando informe del Gremio"}</dd>
      <dt>Rangos</dt><dd>${esc(ranks)}</dd>
      <dt>Arsenal</dt><dd>${g.has_data ? `${weapons.toLocaleString("es")} armas · ${armor.toLocaleString("es")} piezas` : "8 clases confirmadas"}</dd>
      <dt>Lanzado</dt><dd>${esc(g.year)} · ${esc(g.platforms)}</dd>
    </dl>
    <div class="poster-foot"><span class="accept">${g.has_data ? "ACEPTAR MISIÓN ›" : "SIN DATOS AÚN"}</span><span class="wax-seal">${g.has_data ? "✓" : "?"}</span></div>
    ${g.has_data ? "" : `<div class="stamp">PRÓXIMAMENTE</div>`}
  </${tag}>`;
}

async function viewHome() {
  setNav("home"); setGameTheme(null);
  const gs = await games();
  $app.innerHTML = `<div class="page fade-in">
    <section class="guild-hero">
      <div class="eyebrow">Gremio de Cazadores</div>
      <h1>Tablón de Misiones</h1>
      <p>Acepta el contrato de tu juego, elige tu arma y marca tu rango: te diremos qué equipo puedes forjar ahora mismo y cómo evoluciona hasta el final.</p>
    </section>
    <section class="board tex-wood">
      <div class="board-plaque tex-leather frame-bronze">MISIONES DISPONIBLES</div>
      <div class="posters">${gs.map(posterHtml).join("")}</div>
    </section>
    <h2 class="section-title">Archivos del Gremio</h2>
    <p class="section-sub">Todo el equipo registrado, aunque no forme parte de ninguna build recomendada.</p>
    <a class="hunt-banner tex-leather frame-bronze" href="#/caceria">
      <div class="hb-icons">${["world", "rise", "wilds"].map((k) => img(MONSTERS[k].img, "", MONSTERS[k].name)).join("")}</div>
      <div><div class="eyebrow">Nuevo</div><h3>Cacería: build contra un monstruo</h3>
        <p>Elige el monstruo y el rango de la misión: la build se adapta a sus debilidades, sus zonas débiles y sus ataques.</p></div>
      <span class="go">ELEGIR PRESA ›</span>
    </a>
    <div class="notes">
      <a class="note tex-leather frame-bronze" href="#/arsenal"><div class="icon-frame lg r5">${img(classIcon("long-sword"), "class-icon")}</div>
        <div><h3>Arsenal</h3><p>Árbol de forja de las 14 clases, juego a juego y expansión a expansión.</p><span class="go">ABRIR ›</span></div></a>
      <a class="note tex-leather frame-bronze" href="#/armeria"><div class="icon-frame lg r7">${ARMOR_ICONS.head}</div>
        <div><h3>Armería</h3><p>Sets de armadura con defensa, huecos, habilidades y bonificaciones.</p><span class="go">ABRIR ›</span></div></a>
      <a class="note tex-leather frame-bronze" href="#/adornos"><div class="icon-frame lg r9">${JEWEL_ICON}</div>
        <div><h3>Adornos</h3><p>Joyas por tamaño de hueco, rareza y habilidad.</p><span class="go">ABRIR ›</span></div></a>
    </div>
  </div>`;
}

// ------------------------------------------------------------------ juego: elegir expansión y arma
function rankTabs(g, current, href) {
  return `<div class="rank-tabs">${g.expansions.map((e) => `<a class="rank-tab ${e.id === current ? "active" : ""}" href="${href(e)}">
    ${esc(e.name)}<small>${e.is_dlc ? "EXPANSIÓN" : "JUEGO BASE"} · ${esc(e.rank_label)}</small></a>`).join("")}</div>`;
}

async function viewGame(gameId, expId) {
  setNav("home"); setGameTheme(gameId);
  const [gs, types] = await Promise.all([games(), api("/api/weapon-types")]);
  const g = gs.find((x) => x.id === gameId);
  if (!g) return notFound();
  const exp = g.expansions.find((e) => e.id === expId) || g.expansions[0];
  const mon = MONSTERS[exp.id] || MONSTERS[g.id];
  $app.innerHTML = `<div class="page fade-in">
    ${crumbs([["Misiones", "#/"], [g.name]])}
    <header class="plaque tex-leather frame-bronze">
      ${mon?.img ? img(mon.img, "monster", mon.name) : `<div style="width:92px">${UNKNOWN_MONSTER}</div>`}
      <div><div class="eyebrow">${esc(g.subtitle)}</div><h1>${esc(g.name)}</h1><p>${esc(g.year)} · ${esc(g.platforms)}</p></div>
      ${rankTabs(g, exp.id, (e) => `#/game/${g.id}/${e.id}`)}
    </header>
    ${g.has_data ? `
      <h2 class="section-title">Elige tu arma</h2>
      <p class="section-sub">Verás la mejor build en cada etapa de ${esc(exp.name)} según tu ${exp.rank_label === "MR" ? "Rango Maestro" : "Rango de Cazador"}.</p>
      <div class="class-grid">${g.weapon_types.map((t) => {
        const n = types.find((x) => x.id === t.id)?.counts?.[exp.id] || 0;
        return `<a class="class-card tex-leather frame-bronze ${n ? "" : "disabled"}" href="#/build/${esc(exp.id)}/${esc(t.id)}">
          <div class="icon-frame">${img(classIcon(t.id), "class-icon")}</div><div class="name">${esc(t.name)}</div><div class="count">${n} ARMAS</div></a>`;
      }).join("")}</div>`
    : `<div class="empty-state tex-parchment" style="margin-top:28px"><h3>Informe pendiente</h3><p>${esc(g.note || "")}</p>
        <p>Armas confirmadas: ${g.weapon_types.map((t) => esc(t.name)).join(" · ")}</p></div>`}
  </div>`;
}

// ------------------------------------------------------------------ builds por rango
function rankLabel(exp, t) {
  const range = t.max_rank ? (t.max_rank > t.min_rank ? `${t.min_rank}–${t.max_rank}` : `${t.min_rank}`) : `${t.min_rank}+`;
  return `${exp.rank_label} ${range}`;
}

async function viewBuilds(expId, typeId) {
  setNav("home");
  $app.innerHTML = loader();
  const res = await api(`/api/builds/${encodeURIComponent(expId)}/${encodeURIComponent(typeId)}`);
  const { game: g, expansion: exp, weapon_type: wt, tiers } = res;
  setGameTheme(g.id);
  const gfull = (await games()).find((x) => x.id === g.id);
  const key = `rank:${exp.id}`;
  let myRank = store.get(key, null);
  const rankName = exp.rank_label === "MR" ? "Rango Maestro" : "Rango de Cazador";

  $app.innerHTML = `<div class="page fade-in">
    ${crumbs([["Misiones", "#/"], [g.name, `#/game/${g.id}/${exp.id}`], [exp.name, `#/game/${g.id}/${exp.id}`], [wt.name]])}
    <header class="plaque tex-leather frame-bronze">
      <div class="icon-frame lg r8">${img(classIcon(wt.id), "class-icon")}</div>
      <div><div class="eyebrow">${esc(g.name)} · ${esc(exp.name)}</div><h1>${esc(wt.name)}</h1><p>${tiers.length} etapas con cambios de equipo</p></div>
      ${rankTabs(gfull, exp.id, (e) => `#/build/${e.id}/${wt.id}`)}
    </header>
    ${tiers.length ? `<div class="build-layout">
      <aside class="ledger tex-leather frame-bronze">
        <h4>REGISTRO DE RANGOS</h4>
        <div class="rank-field"><label for="myrank">Tu ${rankName}</label>
          <div class="box"><span>${esc(exp.rank_label)}</span><input id="myrank" type="number" min="1" max="999" inputmode="numeric" placeholder="—" value="${myRank ?? ""}"></div></div>
        <ol class="steps">${tiers.map((t, i) => `<li><a href="#tier-${i}" data-tier="${i}"><i class="gem"></i>
          <span><b>${esc(rankLabel(exp, t))}</b><small>${esc(t.title)}</small></span></a></li>`).join("")}</ol>
      </aside>
      <div>${tiers.map((t, i) => tierHtml(exp, t, i)).join("")}</div>
    </div>` : `<div class="empty-state tex-parchment" style="margin-top:28px"><h3>Sin builds</h3><p>No hay datos de esta arma en ${esc(exp.name)}.</p></div>`}
  </div>`;

  const input = document.getElementById("myrank");
  if (!input) return;
  const apply = () => {
    const v = parseInt(input.value, 10);
    myRank = Number.isFinite(v) && v > 0 ? v : null;
    store.set(key, myRank);
    let mine = -1;
    tiers.forEach((t, i) => { if (myRank && t.min_rank <= myRank) mine = i; });
    tiers.forEach((t, i) => {
      const sec = document.getElementById(`tier-${i}`);
      const link = document.querySelector(`[data-tier="${i}"]`);
      const locked = myRank != null && t.min_rank > myRank;
      sec.classList.toggle("locked", locked);
      link.classList.toggle("locked", locked);
      link.classList.toggle("open", myRank != null && !locked);
      link.classList.toggle("mine", i === mine);
      sec.querySelector(".tier-note").innerHTML = i === mine
        ? `<div class="notice mine">★ Tu build para ${esc(exp.rank_label)} ${myRank}: todo lo que ves aquí ya lo puedes forjar.</div>`
        : locked ? `<div class="notice locked">${LOCK}<span>Se desbloquea en ${esc(exp.rank_label)} ${t.min_rank}. Te la enseñamos para que sepas hacia dónde vas.</span></div>` : "";
    });
    return mine;
  };
  input.addEventListener("change", () => { const m = apply(); if (m >= 0) document.getElementById(`tier-${m}`).scrollIntoView(); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.dispatchEvent(new Event("change")); });
  apply();
  scrollSpy();
}

function tierHtml(exp, t, i) {
  const merged = t.merged_ranks.length ? ` Sin cambios hasta ${exp.rank_label} ${t.max_rank ?? "máx."}.` : "";
  return `<section class="tier" id="tier-${i}">
    <div class="tier-head tex-leather frame-bronze">
      <div class="tier-rank"><small>${exp.rank_label === "MR" ? "RANGO MAESTRO" : "RANGO DE CAZADOR"}</small><b>${esc(rankLabel(exp, t))}</b></div>
      <div><h2>${esc(t.title)}</h2><p>${esc(t.description)}${esc(merged)}</p>
        <div class="monsters">${(t.monsters || []).map((m) => `<span class="chip">${esc(m)}</span>`).join("")}</div></div>
    </div>
    <div class="tier-note"></div>
    ${buildHtml(t.build)}
  </section>`;
}

function skillChips(list, key = (s) => s.useful) {
  return (list || []).map((s) => `<span class="skill ${key(s) ? "key" : ""}">${esc(s.name_es || s.name)} ${s.level}</span>`).join("");
}

function jewelsLine(decos) {
  const used = decos.filter((d) => d.id);
  return used.length ? `<div class="row">${used.map((d) => `<span class="jewel"><i class="slot filled lv${d.size}" data-lv="${d.size}" style="--jewel:${jewelColor(d.color)}"></i>${nm(d)}</span>`).join("")}</div>` : "";
}

function buildHtml(b) {
  const w = b.weapon;
  const wDecos = (b.decorations || []).filter((d) => d.owner === "weapon");
  const aff = w.affinity ? `<span class="stat ${w.affinity > 0 ? "pos" : "neg"}">Afinidad <b>${w.affinity > 0 ? "+" : ""}${w.affinity}%</b></span>` : "";
  const weapon = `<div class="equip weapon ${rc(w.rarity)}">
    ${iconFrame({ image: w.image, rarity: w.rarity, type: w.type, size: "lg" })}
    <div>
      <div class="kind">Arma ${rarTag(w.rarity)} ${unlockTag(w)}</div>
      <div class="ename">${nm(w)} ${w.name_es && w.name_es !== w.name ? `<small>${esc(w.name)}</small>` : ""}</div>
      <div class="row"><span class="stat">Ataque <b>${esc(w.attack)}</b></span>${elem(w.element, w.element_value, w.element_hidden)}${elem(w.element2, w.element2_value)}${aff}
        ${w.defense_bonus ? `<span class="stat">Defensa <b>+${w.defense_bonus}</b></span>` : ""}${slots(w.slots, wDecos)}</div>
      ${w.sharpness ? `<div class="row">${sharpness(w.sharpness)}</div>` : ""}
      ${w.skills?.length ? `<div class="row">${skillChips(w.skills, () => true)}</div>` : ""}
      ${jewelsLine(wDecos)}
    </div></div>`;
  const pieces = b.armor.map((p) => {
    if (p.empty) return `<div class="equip">${iconFrame({ kind: p.kind })}<div><div class="kind">${KIND_ES[p.kind]}</div><div class="ename" style="color:var(--dim)">Sin pieza útil</div></div></div>`;
    const decos = (b.decorations || []).filter((d) => d.owner === p.kind);
    return `<div class="equip ${rc(p.rarity)}">
      ${iconFrame({ image: p.image, rarity: p.rarity, kind: p.kind })}
      <div>
        <div class="kind">${KIND_ES[p.kind]} ${rarTag(p.rarity)} ${unlockTag(p)} <span>DEF ${esc(p.defense)}</span> ${slots(p.slots, decos)}</div>
        <div class="ename">${nm(p)} ${p.set_name ? `<small>· ${esc(p.set_name_es || p.set_name)}</small>` : ""}</div>
        <div class="row">${skillChips(p.skills)}</div>
        ${jewelsLine(decos)}
      </div></div>`;
  }).join("");
  const charmDecos = (b.decorations || []).filter((d) => d.owner === "charm");
  const charm = b.charm ? `<div class="equip ${rc(b.charm.rarity)}">${iconFrame({ rarity: b.charm.rarity, kind: "charm" })}<div>
      <div class="kind">${b.charm.synthetic ? "Talismán" : "Amuleto"} ${rarTag(b.charm.rarity)} ${slots(b.charm.slots, charmDecos)}
        ${b.charm.synthetic ? '<span class="random-tag" title="En Rise los talismanes son aleatorios">ALEATORIO</span>' : ""}</div>
      <div class="ename">${nm(b.charm)}</div>
      <div class="row">${skillChips(b.charm.skills, () => true)}</div>
      ${jewelsLine(charmDecos)}
      ${b.charm.synthetic ? `<div class="row talisman-note">Objetivo realista para esta etapa · ${esc(b.charm.method || "Crisol de fusión")}. Busca uno igual o mejor.</div>` : ""}
    </div></div>` : "";

  const skills = b.skills.filter((s) => s.level > 0).map((s) => `<div class="skill-line" title="${esc(s.description || "")}">
      <span class="n ${s.category}">${esc(s.name_es || s.name)}</span><span class="lv">${s.level}/${s.max}</span>
      <div class="gauge ${s.category}">${Array.from({ length: Math.min(s.max, 10) }, (_, i) => `<i class="${i < s.level ? "on" : ""} ${s.level >= s.max ? "max" : ""}"></i>`).join("")}</div></div>`).join("");
  const bonuses = b.set_bonuses.filter((x) => x.ranks.some((r) => r.active)).map((x) => `<div class="skill-line"><span class="n">${esc(x.name_es || x.name)}</span><span class="lv">${x.pieces} pzs</span>
      <div style="grid-column:1/-1;font-size:12px;color:var(--ink-soft)">${x.ranks.filter((r) => r.active).map((r) => esc(r.skill_es || r.skill)).join(" · ")}</div></div>`).join("");
  const alts = (b.alternatives || []).map((a) => `<div class="alt"><span>${nm(a)} · R${esc(a.rarity)}</span>
      <span class="num">${esc(a.attack)}${a.element && a.element_value && !a.element_hidden ? ` · ${esc((ELEMENTS[a.element.toLowerCase()] || [a.element])[0])} ${esc(a.element_value)}` : ""}</span></div>`).join("");

  return `<div class="build">
    <div class="loadout tex-leather frame-bronze"><h3>EQUIPAMIENTO</h3>${weapon}${pieces}${charm}</div>
    <div class="hunter-notes">
      <div class="hn tex-parchment"><h4>Notas del cazador</h4><ul class="why">${b.explanation.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="hn tex-parchment"><h4>Habilidades <span>${b.skills.filter((s) => s.level > 0).length}</span></h4>${skills}</div>
      ${bonuses ? `<div class="hn tex-parchment"><h4>Bonificación de set</h4>${bonuses}</div>` : ""}
      ${alts ? `<div class="hn tex-parchment"><h4>Otras armas a considerar</h4>${alts}</div>` : ""}
    </div>
  </div>`;
}

let spyObserver;
function scrollSpy() {
  spyObserver?.disconnect();
  const links = [...document.querySelectorAll("[data-tier]")];
  spyObserver = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) {
        const i = en.target.id.split("-")[1];
        links.forEach((l) => l.classList.toggle("spy", l.dataset.tier === i));
      }
    });
  }, { rootMargin: "-30% 0px -60% 0px" });
  document.querySelectorAll(".tier").forEach((s) => spyObserver.observe(s));
  links.forEach((l) => l.addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById(`tier-${l.dataset.tier}`)?.scrollIntoView({ behavior: "smooth" });
  }));
}

// ------------------------------------------------------------------ catálogo
function expTabs(gs, current, base) {
  return `<div class="tabs">${gs.filter((g) => g.has_data).flatMap((g) => g.expansions.map((e) =>
    `<a class="tab ${e.id === current ? "active" : ""}" href="${base}/${esc(e.id)}">${esc(g.name.replace("Monster Hunter", "MH").replace(":", ""))}${e.is_dlc ? ` · ${esc(e.name)}` : ""}</a>`)).join("")}</div>`;
}

function searchable(listId, inputId, render) {
  render("");
  document.getElementById(inputId).addEventListener("input", (e) => render(e.target.value));
}

async function viewArsenal(typeId, expId) {
  setNav("arsenal");
  const [gs, types] = await Promise.all([games(), api("/api/weapon-types")]);
  if (!typeId) {
    setGameTheme(null);
    $app.innerHTML = `<div class="page fade-in">${crumbs([["Misiones", "#/"], ["Arsenal"]])}
      <section class="guild-hero"><div class="eyebrow">Arsenal</div><h1>Clases de arma</h1><p>Elige una clase para recorrer su árbol de forja en cada juego.</p></section>
      ${rule()}
      <div class="class-grid">${types.map((t) => {
        const total = Object.values(t.counts).reduce((a, b) => a + b, 0);
        return `<a class="class-card tex-leather frame-bronze" href="#/arsenal/${esc(t.id)}"><div class="icon-frame">${img(classIcon(t.id), "class-icon")}</div>
          <div class="name">${esc(t.name)}</div><div class="count">${total} ARMAS · ${t.games.length} JUEGOS</div></a>`;
      }).join("")}</div></div>`;
    return;
  }
  const t = types.find((x) => x.id === typeId);
  if (!t) return notFound();
  expId = expId || gs.filter((g) => g.has_data).flatMap((g) => g.expansions)[0].id;
  const exp = gs.flatMap((g) => g.expansions).find((e) => e.id === expId);
  if (!exp) return notFound();
  setGameTheme(exp.game_id);
  $app.innerHTML = `<div class="page fade-in">${crumbs([["Arsenal", "#/arsenal"], [t.name]])}
    <header class="plaque tex-leather frame-bronze"><div class="icon-frame lg r8">${img(classIcon(t.id), "class-icon")}</div>
      <div><div class="eyebrow">Árbol de forja</div><h1>${esc(t.name)}</h1><p>${esc(t.name_en)}</p></div><div></div></header>
    <div class="toolbar">${expTabs(gs, expId, `#/arsenal/${t.id}`)}<input class="search" id="q" placeholder="Buscar arma…" aria-label="Buscar arma"></div>
    <div id="list">${loader()}</div></div>`;
  const list = await api(`/api/weapons?type=${encodeURIComponent(typeId)}&expansion=${encodeURIComponent(expId)}`);
  searchable("list", "q", (q) => {
    const ql = q.toLowerCase();
    const items = list.filter((w) => !ql || (w.name + " " + (w.name_es || "")).toLowerCase().includes(ql)).slice(0, 500);
    const byRar = {};
    items.forEach((w) => (byRar[w.rarity] ||= []).push(w));
    document.getElementById("list").innerHTML = items.length ? Object.keys(byRar).sort((a, b) => a - b).map((r) => `
      <section class="forge-tier ${rc(+r)}"><h3>RAREZA ${esc(r)}</h3><div class="forge-grid">${byRar[r].map((w) => `
        <div class="forge-node tex-leather frame-bronze ${rc(w.rarity)}">
          ${iconFrame({ image: w.image, rarity: w.rarity, type: w.weapon_type_id })}
          <div>
            <div class="fname">${nm(w)}</div>
            <div class="fsub">${w.name_es && w.name_es !== w.name ? esc(w.name) : ""}${w.extra?.category ? ` · ${esc(w.extra.category)}` : ""} ${unlockTag(w)}</div>
            <div class="row"><span class="stat">ATQ <b>${esc(w.attack_display)}</b></span>${elem(w.element, w.element_value, w.element_hidden)}${elem(w.element2, w.element2_value)}
              ${w.affinity ? `<span class="stat ${w.affinity > 0 ? "pos" : "neg"}">AFI <b>${w.affinity > 0 ? "+" : ""}${w.affinity}%</b></span>` : ""}${slots(w.slots)}</div>
            ${w.sharpness ? `<div class="row">${sharpness(w.sharpness)}</div>` : ""}
            ${w.skills?.length ? `<div class="row">${skillChips(w.skills, () => true)}</div>` : ""}
          </div></div>`).join("")}</div></section>`).join("")
      : `<div class="empty-state tex-parchment"><h3>Sin resultados</h3><p>Esta clase no existe en ${esc(exp.name)} o no coincide con la búsqueda.</p></div>`;
  });
}

async function viewArmeria(expId) {
  setNav("armeria");
  const gs = await games();
  expId = expId || gs[0].expansions[0].id;
  const exp = gs.flatMap((g) => g.expansions).find((e) => e.id === expId);
  if (!exp) return notFound();
  setGameTheme(exp.game_id);
  $app.innerHTML = `<div class="page fade-in">${crumbs([["Misiones", "#/"], ["Armería"]])}
    <section class="guild-hero"><div class="eyebrow">Armería</div><h1>Sets de armadura</h1><p>Cada pieza con su rareza, defensa, huecos y habilidades.</p></section>
    <div class="toolbar">${expTabs(gs, expId, "#/armeria")}<input class="search" id="q" placeholder="Buscar set o pieza…" aria-label="Buscar armadura"></div>
    <div id="list">${loader()}</div></div>`;
  const sets = await api(`/api/armor?expansion=${encodeURIComponent(expId)}`);
  searchable("list", "q", (q) => {
    const ql = q.toLowerCase();
    const items = sets.filter((s) => !ql || [s.name, s.name_es, ...s.pieces.flatMap((p) => [p.name, p.name_es])].join(" ").toLowerCase().includes(ql));
    document.getElementById("list").innerHTML = items.length ? `<div class="catalog-grid">${items.slice(0, 300).map((s) => `
      <article class="set-card tex-leather frame-bronze"><h3>${nm(s)} ${rarTag(s.rarity)}</h3>
        ${s.bonus_name ? `<div class="bonus">◆ ${esc(s.bonus_name_es || s.bonus_name)}: ${s.bonus_ranks.map((r) => `${r.pieces} pzs → ${esc(r.skill)}`).join(" · ")}</div>` : ""}
        ${s.group_name ? `<div class="bonus">◇ ${esc(s.group_name_es || s.group_name)}: ${s.group_ranks.map((r) => `${r.pieces} pzs → ${esc(r.skill)}`).join(" · ")}</div>` : ""}
        ${s.pieces.map((p) => `<div class="piece">${iconFrame({ image: p.image, rarity: p.rarity, kind: p.kind, size: "sm" })}
          <div><div class="pn">${nm(p)} ${unlockTag(p)}</div><div class="ps">${KIND_ES[p.kind]} · DEF ${esc(p.defense_base)}${p.defense_max && p.defense_max !== p.defense_base ? `–${esc(p.defense_max)}` : ""} · ${p.skills.map((k) => `${esc(k.name_es || k.name)} ${k.level}`).join(", ") || "sin habilidades"}</div></div>
          ${slots(p.slots)}</div>`).join("")}
      </article>`).join("")}</div>` : `<div class="empty-state tex-parchment"><h3>Sin resultados</h3></div>`;
  });
}

async function viewAdornos(expId) {
  setNav("adornos");
  const gs = await games();
  expId = expId || gs[0].expansions[0].id;
  const exp = gs.flatMap((g) => g.expansions).find((e) => e.id === expId);
  if (!exp) return notFound();
  setGameTheme(exp.game_id);
  $app.innerHTML = `<div class="page fade-in">${crumbs([["Misiones", "#/"], ["Adornos"]])}
    <section class="guild-hero"><div class="eyebrow">Adornos</div><h1>Joyas y adornos</h1><p>Se engarzan en los huecos de armas y armaduras para sumar habilidades.</p></section>
    <div class="toolbar">${expTabs(gs, expId, "#/adornos")}<input class="search" id="q" placeholder="Buscar adorno o habilidad…" aria-label="Buscar adorno"></div>
    <div id="list">${loader()}</div></div>`;
  const ds = await api(`/api/decorations?expansion=${encodeURIComponent(expId)}`);
  searchable("list", "q", (q) => {
    const ql = q.toLowerCase();
    const items = ds.filter((d) => !ql || [d.name, d.name_es, ...d.skills.flatMap((s) => [s.name, s.name_es])].join(" ").toLowerCase().includes(ql));
    document.getElementById("list").innerHTML = items.length ? `<div class="catalog-grid">${items.map((d) => `
      <div class="piece tex-leather frame-bronze" style="padding:10px 12px;clip-path:var(--cut-a)">
        <div class="icon-frame sm ${rc(d.rarity || 5)}"><i class="slot filled lv${d.slot}" data-lv="${d.slot}" style="--jewel:${jewelColor(d.color)}"></i></div>
        <div><div class="pn">${nm(d)}</div><div class="ps">${d.skills.map((s) => `${esc(s.name_es || s.name)} +${s.level}`).join(" · ")}</div></div>
        <div>${d.rarity ? rarTag(d.rarity) : ""}<div class="ps" style="text-align:right">${d.kind !== "any" ? (d.kind === "weapon" ? "arma" : "armadura") : ""}</div></div>
      </div>`).join("")}</div>` : `<div class="empty-state tex-parchment"><h3>Sin resultados</h3></div>`;
  });
}

// ------------------------------------------------------------------ cacería: build contra un monstruo
const RANK_LABEL = { low: "Rango Bajo", high: "Rango Alto", master: "Rango Maestro" };
const RANK_SHORT = { low: "RB", high: "RA", master: "RM" };
const EL_KEYS = ["fire", "water", "thunder", "ice", "dragon"];
const ST_ES = { poison: "Veneno", sleep: "Sueño", paralysis: "Parálisis", blast: "Nitro", stun: "Aturdir" };
const QUEST_EXP = {
  world: { low: "world-base", high: "world-base", master: "world-iceborne" },
  rise: { low: "rise-base", high: "rise-base", master: "rise-sunbreak" },
  wilds: { low: "wilds-base", high: "wilds-base" },
};

function weakChips(weak, min = 2) {
  return EL_KEYS.filter((e) => (weak[`element:${e}`] || 0) >= min)
    .sort((a, b) => weak[`element:${b}`] - weak[`element:${a}`])
    .map((e) => `<span class="weak-chip" style="--el:${ELEMENTS[e][1]}">${ELEMENTS[e][0]} ${"★".repeat(weak[`element:${e}`])}</span>`).join("");
}

const monsterIcon = (m, cls = "") => (m.icon ? img(m.icon, cls, m.name) : `<span class="${cls}">${UNKNOWN_MONSTER}</span>`);

async function viewHunt(gameId) {
  setNav("caceria");
  const gs = (await games()).filter((g) => g.has_data);
  gameId = gs.some((g) => g.id === gameId) ? gameId : gs[0].id;
  setGameTheme(gameId);
  $app.innerHTML = `<div class="page fade-in">${crumbs([["Misiones", "#/"], ["Cacería"]])}
    <section class="guild-hero"><div class="eyebrow">Cacería</div><h1>Elige tu presa</h1>
      <p>Selecciona el monstruo y el rango de la misión: la build se calcula contra sus zonas débiles, su debilidad elemental y los ataques que usa.</p></section>
    <div class="toolbar"><div class="tabs">${gs.map((g) => `<a class="tab ${g.id === gameId ? "active" : ""}" href="#/caceria/${g.id}">${esc(g.name.replace("Monster Hunter", "MH").replace(":", ""))}</a>`).join("")}</div>
      <input class="search" id="q" placeholder="Buscar monstruo…" aria-label="Buscar monstruo"></div>
    <div id="list">${loader()}</div></div>`;
  const ms = await api(`/api/monsters?game=${encodeURIComponent(gameId)}`);
  searchable("list", "q", (q) => {
    const ql = q.toLowerCase();
    const items = ms.filter((m) => !ql || `${m.name} ${m.name_es || ""}`.toLowerCase().includes(ql));
    document.getElementById("list").innerHTML = items.length ? `<div class="monster-grid">${items.map((m) => `
      <a class="monster-card tex-leather frame-bronze" href="#/caceria/${esc(gameId)}/${m.id}">
        <div class="medallion">${monsterIcon(m)}</div>
        <div class="mname">${nm(m)}</div>
        <div class="ranks">${["low", "high", "master"].map((r) => (m.ranks.includes(r) ? `<span class="rank-pill ${r}">${RANK_SHORT[r]}</span>` : "")).join("")}</div>
        <div class="weaks">${weakChips(m.weaknesses) || '<span class="weak-chip none">Sin debilidad clara</span>'}</div>
      </a>`).join("")}</div>` : `<div class="empty-state tex-parchment"><h3>Sin resultados</h3></div>`;
  });
}

function hitzoneTable(m) {
  const cols = [["cut", "Corte"], ["impact", "Impacto"], ["shot", "Disparo"], ...EL_KEYS.map((e) => [e, ELEMENTS[e][0]])];
  const heat = (k, v) => {
    if (v == null) return "";
    const phys = ["cut", "impact", "shot"].includes(k);
    const lv = phys ? (v >= 45 ? 3 : v >= 30 ? 2 : 1) : (v >= 20 ? 3 : v >= 10 ? 2 : v > 0 ? 1 : 0);
    return `hz${lv}`;
  };
  return `<div class="hz-wrap"><table class="hz"><thead><tr><th>Parte</th>${cols.map(([, l]) => `<th>${esc(l)}</th>`).join("")}</tr></thead>
    <tbody>${m.hitzones.map((h) => `<tr><td>${esc(h.part)}</td>${cols.map(([k]) => `<td class="${heat(k, h[k])}">${h[k] == null ? "–" : Math.round(h[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

async function viewMonster(gameId, monsterId, rank, weapon) {
  setNav("caceria"); setGameTheme(gameId);
  const [m, gs] = await Promise.all([api(`/api/monsters/${monsterId}`), games()]);
  const g = gs.find((x) => x.id === m.game_id);
  rank = m.ranks.includes(rank) ? rank : m.ranks.includes("high") ? "high" : m.ranks[0];
  const base = `#/caceria/${m.game_id}/${m.id}`;
  const stars = (n) => `<span class="stars">${"★".repeat(n)}<i>${"★".repeat(Math.max(0, 3 - n))}</i></span>`;
  const rankKey = `rank:${QUEST_EXP[m.game_id]?.[rank] || m.game_id}`;
  const rankLbl = rank === "master" ? "MR" : "HR";
  const rankName = rank === "master" ? "Rango Maestro" : "Rango de Cazador";
  const myRank = store.get(rankKey, null);
  $app.innerHTML = `<div class="page fade-in">
    ${crumbs([["Cacería", "#/caceria"], [g.name, `#/caceria/${m.game_id}`], [m.name_es || m.name]])}
    <header class="plaque tex-leather frame-bronze">
      <div class="medallion lg">${monsterIcon(m)}</div>
      <div><div class="eyebrow">Presa · ${esc(g.name)}</div><h1>${nm(m)}</h1>
        <p>${m.threats_es.length ? `Ataques: ${m.threats_es.map(esc).join(" · ")}` : ""}${m.threats_source === "estimado" ? " (estimado)" : ""}</p></div>
      <div class="rank-tabs">${["low", "high", "master"].filter((r) => m.ranks.includes(r)).map((r) =>
        `<a class="rank-tab ${r === rank ? "active" : ""}" href="${base}/${r}${weapon ? `/${weapon}` : ""}">${RANK_LABEL[r]}<small>MISIÓN</small></a>`).join("")}</div>
    </header>
    <div class="hunt-controls">
      ${m.forms.length ? `<div class="forms"><span class="ctl-label">Forma</span><div class="tabs">${m.forms.map((f) =>
        `<a class="tab ${f.id === m.id ? "active" : ""}" href="#/caceria/${m.game_id}/${f.id}/${rank}${weapon ? `/${weapon}` : ""}">${esc(f.label)}</a>`).join("")}</div></div>` : ""}
      <div class="rank-field inline"><label for="myrank">Tu ${rankName}</label>
        <div class="box"><span>${esc(rankLbl)}</span><input id="myrank" type="number" min="1" max="999" inputmode="numeric" placeholder="—" value="${myRank ?? ""}"></div>
        <small>Vacío = mejor equipo del rango</small></div>
    </div>
    ${m.notes?.length ? `<div class="notice mine variant-note">★ ${m.notes.map(esc).join(" ")}</div>` : ""}
    <div class="dossier">
      <div class="hn tex-parchment"><h4>Debilidades</h4>
        ${EL_KEYS.map((e) => `<div class="weak-line"><span class="ink-${e}">${ELEMENTS[e][0]}</span>${stars(m.weaknesses[`element:${e}`] || 0)}</div>`).join("")}
        <div class="weak-sep"></div>
        ${Object.entries(ST_ES).map(([k, l]) => `<div class="weak-line"><span>${l}</span>${stars(m.weaknesses[`status:${k}`] || 0)}</div>`).join("")}
      </div>
      <div class="hn tex-parchment"><h4>Zonas de golpe <span>% de daño recibido</span></h4>${hitzoneTable(m)}</div>
    </div>
    <h2 class="section-title">Elige tu arma</h2>
    <p class="section-sub">Build para cazar a ${nm(m)} en ${RANK_LABEL[rank]}, con el mejor equipo disponible en ese rango.</p>
    <div class="class-grid">${g.weapon_types.map((t) => `<a class="class-card tex-leather frame-bronze ${t.id === weapon ? "selected" : ""}" href="${base}/${rank}/${t.id}">
      <div class="icon-frame">${img(classIcon(t.id), "class-icon")}</div><div class="name">${esc(t.name)}</div></a>`).join("")}</div>
    <div id="hunt-build">${weapon ? loader() : ""}</div>
  </div>`;
  document.getElementById("myrank").addEventListener("change", (e) => {
    const v = parseInt(e.target.value, 10);
    store.set(rankKey, Number.isFinite(v) && v > 0 ? v : null);
    viewMonster(gameId, monsterId, rank, weapon);
  });
  document.getElementById("myrank").addEventListener("keydown", (e) => { if (e.key === "Enter") e.target.dispatchEvent(new Event("change")); });
  if (!weapon) return;
  try {
    const b = await api(`/api/hunt/${m.id}?rank=${encodeURIComponent(rank)}&weapon=${encodeURIComponent(weapon)}${myRank ? `&hr=${myRank}` : ""}`);
    const t = b.tier || {};
    const tierTxt = myRank
      ? (t.too_low ? `Tu ${rankLbl} ${myRank} no llega a ${RANK_LABEL[rank]} (mínimo ${rankLbl} ${t.min_rank_for_quest}): se muestra el equipo de esa etapa.`
        : `Con ${rankLbl} ${myRank}: equipo hasta rareza ${t.max_rarity} · ${t.tier_title}.`)
      : `Mejor equipo disponible en ${RANK_LABEL[rank]} (rareza ${t.max_rarity ?? "máx."}). Indica tu ${rankLbl} para ajustarla.`;
    const wt = g.weapon_types.find((t) => t.id === weapon);
    document.getElementById("hunt-build").innerHTML = `<section class="tier" id="hunt-result">
      <div class="tier-head tex-leather frame-bronze">
        <div class="tier-rank"><small>${esc(RANK_LABEL[rank].toUpperCase())}</small><b>${esc(RANK_SHORT[rank])}</b></div>
        <div><h2>${esc(wt?.name || weapon)} contra ${nm(m)}</h2><p>${esc(tierTxt)}</p></div>
      </div>${buildHtml(b)}</section>`;
    document.getElementById("hunt-result").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    document.getElementById("hunt-build").innerHTML = `<div class="empty-state tex-parchment"><h3>Sin build</h3><p>${esc(err.message)}</p></div>`;
  }
}

function notFound() {
  $app.innerHTML = `<div class="page"><div class="empty-state tex-parchment"><h3>Rastro perdido</h3><p>Esta página no existe.</p><p><a class="chip key" href="#/">Volver al tablón</a></p></div></div>`;
}

// ------------------------------------------------------------------ router
async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  window.scrollTo({ top: 0, behavior: "instant" });
  try {
    switch (parts[0]) {
      case undefined: return await viewHome();
      case "game": return await viewGame(parts[1], parts[2]);
      case "build": return await viewBuilds(parts[1], parts[2]);
      case "arsenal": return await viewArsenal(parts[1], parts[2]);
      case "armeria": return await viewArmeria(parts[1]);
      case "adornos": return await viewAdornos(parts[1]);
      case "caceria": return parts[2] ? await viewMonster(parts[1], +parts[2], parts[3], parts[4]) : await viewHunt(parts[1]);
      default: return notFound();
    }
  } catch (err) {
    $app.innerHTML = `<div class="page"><div class="empty-state tex-parchment"><h3>No se pudo cargar</h3><p>${esc(err.message)}</p></div></div>`;
  }
}
window.addEventListener("hashchange", route);
route();

// ------------------------------------------------------------------ brasas de la forja
(function embers() {
  const c = document.getElementById("embers");
  if (!c || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const ctx = c.getContext("2d");
  let w, h;
  const ps = [];
  const resize = () => { w = c.width = innerWidth; h = c.height = innerHeight; };
  resize(); addEventListener("resize", resize);
  for (let i = 0; i < 34; i++) ps.push({ x: Math.random() * innerWidth, y: Math.random() * innerHeight, r: Math.random() * 1.6 + 0.4, v: Math.random() * 0.45 + 0.15, d: Math.random() * Math.PI * 2 });
  (function tick() {
    ctx.clearRect(0, 0, w, h);
    for (const p of ps) {
      p.y -= p.v; p.d += 0.01; p.x += Math.sin(p.d) * 0.3;
      if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
      ctx.beginPath(); ctx.fillStyle = `rgba(244,162,97,${0.3 + 0.3 * Math.sin(p.d * 3)})`;
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
    }
    requestAnimationFrame(tick);
  })();
})();
