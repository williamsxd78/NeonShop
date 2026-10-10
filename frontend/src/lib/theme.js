export const THEME_KEYS = [
  ["brand", "Main color", "Buttons, links, active tabs"],
  ["brandlt", "Light main color", "Prices, highlights, balance"],
  ["info", "Accent color", "Secondary highlights, card bars"],
  ["ink", "Page background", "Behind everything"],
  ["panel", "Card background", "Product and info cards"],
  ["surface", "Panel background", "Menus, nav bars, chips"],
  ["deep", "Input background", "Text boxes, dialogs"],
  ["line", "Borders", "Card and input outlines"],
];

export const PRESETS = {
  "Neon Green": { brand: "#22C55E", brandlt: "#4ADE80", info: "#22D3EE", ink: "#0A0B0B", panel: "#171A19", surface: "#121413", deep: "#0E100F", line: "#272B29" },
  "Cyber Blue": { brand: "#3B82F6", brandlt: "#60A5FA", info: "#A78BFA", ink: "#090B10", panel: "#151922", surface: "#11141B", deep: "#0D1016", line: "#252B38" },
  "Royal Purple": { brand: "#A855F7", brandlt: "#C084FC", info: "#22D3EE", ink: "#0B0910", panel: "#19151F", surface: "#14111A", deep: "#100D15", line: "#2C2636" },
  "Sunset Orange": { brand: "#F97316", brandlt: "#FB923C", info: "#FACC15", ink: "#0C0A09", panel: "#1A1715", surface: "#151210", deep: "#110F0D", line: "#2E2925" },
  "Crimson Red": { brand: "#EF4444", brandlt: "#F87171", info: "#F59E0B", ink: "#0C0909", panel: "#1A1515", surface: "#151111", deep: "#110E0E", line: "#2E2525" },
  "Royal Gold": { brand: "#EAB308", brandlt: "#FACC15", info: "#22D3EE", ink: "#0B0A08", panel: "#191713", surface: "#141210", deep: "#100F0C", line: "#2D2A22" },
  "Ocean Teal": { brand: "#14B8A6", brandlt: "#2DD4BF", info: "#38BDF8", ink: "#080B0B", panel: "#141A19", surface: "#101515", deep: "#0C1111", line: "#233030" },
};

const triplet = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
};

export function applyTheme(theme, persist = true) {
  if (!theme) return;
  const root = document.documentElement.style;
  THEME_KEYS.forEach(([k]) => { if (/^#[0-9a-f]{6}$/i.test(theme[k] || "")) root.setProperty(`--nk-${k}`, triplet(theme[k])); });
  if (persist) localStorage.setItem("nk_theme", JSON.stringify(theme));
}

export const FONTS = {
  heading: ["Outfit", "Space Grotesk", "Sora", "Syne", "Unbounded", "Chakra Petch", "Orbitron", "Rajdhani", "Exo 2", "Lexend", "Poppins", "Montserrat", "Bricolage Grotesque", "Playfair Display", "Bebas Neue"],
  body: ["Manrope", "Inter", "DM Sans", "Plus Jakarta Sans", "Nunito Sans", "Figtree", "Work Sans", "Rubik", "Karla", "IBM Plex Sans", "Source Sans 3", "Lato", "Open Sans", "Outfit", "Sora", "Rajdhani", "Exo 2"],
  mono: ["JetBrains Mono", "IBM Plex Mono", "Fira Code", "Space Mono", "Roboto Mono", "Source Code Pro", "DM Mono", "Share Tech Mono"],
};
export const DEFAULT_FONTS = { heading: "Outfit", body: "Manrope", mono: "JetBrains Mono" };

export function loadFont(name) {
  const id = `nk-font-${name.replace(/ /g, "-")}`;
  if (document.getElementById(id)) return;
  const l = document.createElement("link");
  l.id = id;
  l.rel = "stylesheet";
  l.href = `https://fonts.googleapis.com/css2?family=${name.replace(/ /g, "+")}:wght@400;500;600;700&display=swap`;
  document.head.appendChild(l);
}

export function applyFonts(fonts, persist = true) {
  if (!fonts) return;
  const root = document.documentElement.style;
  ["heading", "body", "mono"].forEach((k) => {
    if (!FONTS[k].includes(fonts[k])) return;
    loadFont(fonts[k]);
    root.setProperty(`--nk-font-${k}`, `"${fonts[k]}"`);
  });
  if (persist) localStorage.setItem("nk_fonts", JSON.stringify(fonts));
}

export function applyCachedTheme() {
  try { applyTheme(JSON.parse(localStorage.getItem("nk_theme")), false); } catch { /* no cached theme */ }
  try { applyFonts(JSON.parse(localStorage.getItem("nk_fonts")), false); } catch { /* no cached fonts */ }
}
