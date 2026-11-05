// Iconografía: iconos oficiales de clase de arma (Kiranico), monstruos emblemáticos y
// siluetas propias solo para piezas de armadura sin imagen (como los menús del juego).
const KIRANICO_ICON = "https://cdn.kiranico.net/file/kiranico/mhworld-web/mhw/icon";

const CLASS_ORDER = ["great-sword", "sword-and-shield", "dual-blades", "long-sword", "hammer", "hunting-horn",
  "lance", "gunlance", "switch-axe", "charge-blade", "insect-glaive", "bow", "heavy-bowgun", "light-bowgun"];

export const classIcon = (type) => `${KIRANICO_ICON}/weapon_type_${CLASS_ORDER.indexOf(type)}.png`;

// Monstruo emblemático de cada juego / expansión (portada, misiones y cabeceras).
export const MONSTERS = {
  "world": { name: "Nergigante", img: `${KIRANICO_ICON}/em103_ID.png` },
  "world-base": { name: "Nergigante", img: `${KIRANICO_ICON}/em103_ID.png` },
  "world-iceborne": { name: "Velkhana", img: `${KIRANICO_ICON}/em124_ID.png` },
  "rise": { name: "Magnamalo", img: "https://cdn.kiranico.net/file/kiranico/mhrise-web/images/icons/em089_00.png" },
  "rise-base": { name: "Magnamalo", img: "https://cdn.kiranico.net/file/kiranico/mhrise-web/images/icons/em089_00.png" },
  "rise-sunbreak": { name: "Malzeno", img: "https://cdn.kiranico.net/file/kiranico/mhrise-web/images/icons/em132_00.png" },
  "wilds": { name: "Arkveld", img: "https://mhwilds.kiranico.net/em_icon/EM0160_00_0.webp" },
  "wilds-base": { name: "Arkveld", img: "https://mhwilds.kiranico.net/em_icon/EM0160_00_0.webp" },
  "outlanders": { name: "Ruger Aidal", img: null },
  "outlanders-base": { name: "Ruger Aidal", img: null },
};

const S = (body, vb = "0 0 64 64") => `<svg viewBox="${vb}" aria-hidden="true" fill="currentColor">${body}</svg>`;

// Siluetas de pieza (casco, peto, brazales, faja, grebas) teñidas por rareza vía currentColor.
export const ARMOR_ICONS = {
  head: S(`<path d="M12 38c0-15 9-26 20-26s20 11 20 26v6H41v-7c0-4-4-7-9-7s-9 3-9 7v7H12z"/><path d="M29 5h6l-1 9h-4z" opacity=".75"/><path d="M22 40h20v3H22z" opacity=".5"/>`),
  chest: S(`<path d="M18 9l8 5h12l8-5 11 9-6 13-5-3v27H18V28l-5 3-6-13z"/><path d="M31 15h2v38h-2zM22 28h20v2H22z" fill="#0005"/>`),
  arms: S(`<path d="M14 12h22l7 13v21l-9 9H22l-8-9z"/><path d="M43 25h8v15h-8z" opacity=".7"/><path d="M16 32h26v3H16z" fill="#0005"/>`),
  waist: S(`<rect x="8" y="16" width="48" height="11" rx="2"/><path d="M13 27h15l-2 23-13-7zM36 27h15v16l-13 7z" opacity=".75"/><rect x="28" y="14" width="8" height="15" fill="#0005"/>`),
  legs: S(`<path d="M17 6h13v31l4 9v12H13V46l4-9z"/><path d="M35 6h12v29l6 11v12H35z" opacity=".78"/><path d="M15 46h17v3H15z" fill="#0005"/>`),
};

export const CHARM_ICON = S(`<path d="M32 4l20 13v30L32 60 12 47V17z"/><path d="M32 15l11 7v20l-11 7-11-7V22z" fill="#0006"/><circle cx="32" cy="32" r="5" opacity=".9"/>`);
export const JEWEL_ICON = S(`<path d="M32 4l24 22-24 34L8 26z"/><path d="M32 4l24 22H8z" fill="#fff" opacity=".3"/><path d="M20 26h24L32 52z" fill="#0003"/>`);
export const UNKNOWN_MONSTER = S(`<path d="M50 14c-14 0-24 9-24 20 0 6 3 10 6 13l-4 12 11-7c3 1 7 2 11 2 14 0 24-9 24-20S64 14 50 14z" fill="#3b2a16"/><text x="50" y="45" text-anchor="middle" font-family="Cinzel,serif" font-weight="900" font-size="26" fill="#ecdcb6">?</text>`, "0 0 100 80");
export const LOCK = S(`<rect x="14" y="28" width="36" height="28" rx="3"/><path d="M22 28v-8a10 10 0 0120 0v8" stroke="currentColor" stroke-width="6" fill="none"/>`);
