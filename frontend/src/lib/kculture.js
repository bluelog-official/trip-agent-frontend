const THEME_ORDER = ["k-food", "k-beauty", "k-pop", "k-trend"];

const THEME_LABELS = {
  "k-food": "K-Food",
  "k-beauty": "K-Beauty",
  "k-pop": "K-Pop & Culture",
  "k-trend": "K-Trend",
};

const THEME_RULES = [
  ["k-food", /k-?food/],
  ["k-beauty", /k-?beauty/],
  ["k-pop", /k-?pop/],
  ["k-trend", /k-?trend/],
];

export const K_THEME_FILTERS = [
  { id: "all", labelKey: "kculture.themes.all" },
  { id: "k-food", labelKey: "kculture.themes.food" },
  { id: "k-beauty", labelKey: "kculture.themes.beauty" },
  { id: "k-pop", labelKey: "kculture.themes.pop" },
  { id: "k-trend", labelKey: "kculture.themes.trend" },
];

function frontmatterValue(markdown, key) {
  const block = /^---\r?\n([\s\S]*?)\r?\n---/.exec(String(markdown || ""));
  if (!block) return "";
  const match = new RegExp(`^${key}:\\s*"?([^"\\n]+)"?`, "m").exec(block[1]);
  return match ? match[1].trim() : "";
}

function uniqueThemes(ids) {
  return THEME_ORDER.filter((id) => ids.includes(id));
}

export function themesFromText(value) {
  const raw = String(value || "").toLowerCase();
  return uniqueThemes(THEME_RULES.filter(([, pattern]) => pattern.test(raw)).map(([id]) => id));
}

const FILE_TOKENS = {
  kfood: "k-food",
  "k-food": "k-food",
  kbeauty: "k-beauty",
  "k-beauty": "k-beauty",
  kpop: "k-pop",
  "k-pop": "k-pop",
  trend: "k-trend",
  ktrend: "k-trend",
  "k-trend": "k-trend",
  heritage: "k-trend",
};

export function themesFromFilename(guideId) {
  const name = String(guideId || "")
    .split("/")
    .pop()
    .toLowerCase()
    .replace(/_guide\.md$/, "");
  const found = name.split(/[_-]/).map((token) => FILE_TOKENS[token]).filter(Boolean);
  return uniqueThemes(found);
}

export function readKCulture(guideId, markdown) {
  const themes = uniqueThemes([
    ...themesFromText(frontmatterValue(markdown, "k_themes")),
    ...themesFromFilename(guideId),
  ]);
  const hot = frontmatterValue(markdown, "hot_country").toLowerCase();
  return {
    kThemes: themes,
    hotCountry: hot === "korea" || hot === "kr" || themesFromFilename(guideId).length > 0,
    themeLabels: themes.map((id) => THEME_LABELS[id]).filter(Boolean),
  };
}

export function matchesKCulture(card, theme, hotOn) {
  const selected = theme || "all";
  if (!hotOn && selected === "all") return true;
  if (hotOn && !card?.hotCountry) return false;
  if (selected !== "all" && !(card?.kThemes || []).includes(selected)) return false;
  return true;
}
