import { stripFrontmatter } from "./articleDocument";
import {
  budgetFilterFor,
  budgetKeyFor,
  budgetLabelFor,
  durationKeyFor,
  durationLabelFor,
  parseGuideFilename,
} from "./magazineMatrix";

const DEFAULT_API_ORIGIN = "https://bluelog-trip-backend.onrender.com";

function resolveApiBaseUrl() {
  const configured = String(import.meta.env.VITE_API_BASE_URL || DEFAULT_API_ORIGIN).replace(/\/$/, "");
  if (configured.endsWith("/api/v1")) return configured;
  return `${configured}/api/v1`;
}

const API_BASE_URL = resolveApiBaseUrl();

const REGION_CITIES = {
  asia: [
    "tokyo",
    "kyoto",
    "osaka",
    "seoul",
    "busan",
    "jeju",
    "bali",
    "bangkok",
    "singapore",
    "taipei",
    "danang",
    "da nang",
    "hong kong",
    "hanoi",
    "beijing",
    "shanghai",
    "jakarta",
  ],
  europe: [
    "paris",
    "rome",
    "london",
    "barcelona",
    "amsterdam",
    "berlin",
    "prague",
    "vienna",
    "lisbon",
    "madrid",
    "florence",
    "milan",
  ],
  americas: [
    "new york",
    "los angeles",
    "chicago",
    "miami",
    "toronto",
    "vancouver",
    "mexico",
    "rio",
    "sao paulo",
    "buenos aires",
    "san francisco",
  ],
  oceania: ["sydney"],
};

const FOOD_PATTERN = /food|cuisine|restaurant|dining|bistro|ramen|cafe|맛집|음식|미식/i;

export const REGION_LABELS = {
  asia: "Asia",
  europe: "Europe",
  americas: "Americas",
  oceania: "Oceania",
};

function titleCase(value) {
  return String(value || "")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function clip(text, max = 160) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max).replace(/\s+\S*$/, "")}…`;
}

function firstHeading(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const h1 = lines.find((line) => /^#\s+/.test(line.trim()) && !/^##/.test(line.trim()));
  if (h1) return h1.trim().replace(/^#\s+/, "");
  const h2 = lines.find((line) => /^##\s+/.test(line.trim()));
  return h2 ? h2.trim().replace(/^##\s+/, "") : "";
}

function firstImage(markdown) {
  const match = String(markdown || "").match(/!\[[^\]]*\]\((https?:[^)\s]+)\)/);
  return match ? match[1] : "";
}

function firstParagraph(markdown) {
  const blocks = String(markdown || "").split(/\n\s*\n/);
  for (const block of blocks) {
    const text = block.trim();
    if (!text || text.startsWith("#") || text.startsWith("!") || text.startsWith("|")) continue;
    if (text.startsWith("*Photo") || text.startsWith("- ") || text.startsWith("* ")) continue;
    const clean = text
      .replace(/\[(.*?)\]\(.*?\)/g, "$1")
      .replace(/[*_`]/g, "")
      .replace(/\s+/g, " ")
      .trim();
    if (clean.length > 40) return clip(clean);
  }
  return "";
}

export function classifyRegion(label) {
  const name = String(label || "").toLowerCase();
  for (const [region, cities] of Object.entries(REGION_CITIES)) {
    if (cities.some((city) => name.includes(city))) return region;
  }
  return "";
}

function frontmatterValue(markdown, key) {
  const block = /^---\r?\n([\s\S]*?)\r?\n---/.exec(String(markdown || ""));
  if (!block) return "";
  const match = new RegExp(`^${key}:\\s*"?([^"\\n]+)"?`, "m").exec(block[1]);
  return match ? match[1].trim() : "";
}

function themeTags(markdown) {
  const fromFrontmatter = frontmatterValue(markdown, "hashtags");
  const source = fromFrontmatter
    ? fromFrontmatter.split(/\s+/)
    : String(markdown || "")
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .reverse()
        .find((line) => /^(?:#[A-Za-z][A-Za-z0-9]*)(?:\s+#[A-Za-z][A-Za-z0-9]*)+$/.test(line))
        ?.split(/\s+/) || [];
  const labels = [];
  source.forEach((tag) => {
    const label = String(tag || "").replace(/^#/, "").trim();
    if (label && !labels.includes(label)) labels.push(label);
  });
  return labels;
}

export function toGuideCard(summary, detail) {
  const id = (typeof summary === "string" ? summary : summary?.id) || detail?.id || "";
  const rawMarkdown = detail?.content || detail?.article_markdown || "";
  const markdown = stripFrontmatter(rawMarkdown);
  const identity = parseGuideFilename(id);
  const durationKey = durationKeyFor(frontmatterValue(rawMarkdown, "duration_key") || identity.durationKey);
  const budgetKey = budgetKeyFor(frontmatterValue(rawMarkdown, "budget_key") || identity.budgetKey);
  const destination = titleCase(
    (frontmatterValue(rawMarkdown, "city") || identity.citySlug).replace(/_/g, " "),
  );
  const title = frontmatterValue(rawMarkdown, "title") || firstHeading(markdown) || `${destination} Trip Guide`;
  const summaryText = firstParagraph(markdown) || `Local trip notes for ${destination}.`;
  const region = classifyRegion(`${destination} ${id}`);
  const hasFood = FOOD_PATTERN.test(`${title}\n${markdown.slice(0, 4000)}`);
  const score = Number(detail?.qa_result?.quality_score ?? summary?.quality_score ?? 0) || 0;
  const approved = detail?.qa_result?.is_approved === true || detail?.is_approved === true;
  const tags = [];
  if (REGION_LABELS[region]) tags.push(REGION_LABELS[region]);
  if (destination) tags.push(destination);
  themeTags(rawMarkdown).forEach((tag) => {
    if (!tags.includes(tag)) tags.push(tag);
  });
  const durationLabel = durationLabelFor(durationKey);
  const budgetLabel = budgetLabelFor(budgetKey);
  if (durationLabel && !tags.includes(durationLabel)) tags.push(durationLabel);
  if (budgetLabel && !tags.includes(budgetLabel)) tags.push(budgetLabel);

  return {
    id,
    title,
    summary: summaryText,
    image: firstImage(markdown) || frontmatterValue(rawMarkdown, "image_url"),
    destination,
    region,
    hasFood,
    score,
    approved,
    tags,
    durationKey,
    durationLabel,
    budgetKey,
    budgetLabel,
    budgetFilter: budgetFilterFor(budgetKey),
  };
}

export function matchesGuideQuery(card, query) {
  const needle = String(query || "").trim().toLowerCase();
  if (!needle) return true;
  return [card.title, card.summary, card.destination, ...(card.tags || [])]
    .join(" ")
    .toLowerCase()
    .includes(needle);
}

export function popularDestinations(cards, limit = 5) {
  const seen = new Set();
  return [...cards]
    .sort((a, b) => (b.score || 0) - (a.score || 0) || a.destination.localeCompare(b.destination))
    .filter((card) => {
      const key = card.destination.toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, limit);
}

export async function fetchGuideCards() {
  const res = await fetch(`${API_BASE_URL}/guides`);
  if (!res.ok) {
    throw new Error("guide list failed");
  }
  const data = await res.json();
  const items = Array.isArray(data) ? data : data.guides || [];
  const cards = await Promise.all(
    items.map(async (item) => {
      const id = typeof item === "string" ? item : item?.id;
      if (!id) return null;
      try {
        const detailRes = await fetch(`${API_BASE_URL}/guides/${encodeURIComponent(id)}`);
        const detail = detailRes.ok ? await detailRes.json() : null;
        return toGuideCard(item, detail);
      } catch (err) {
        console.error("가이드 카드 로드 실패:", err);
        return toGuideCard(item, null);
      }
    }),
  );
  return cards.filter(Boolean);
}

export async function fetchGuideDetail(guideId) {
  const res = await fetch(`${API_BASE_URL}/guides/${encodeURIComponent(guideId)}`);
  if (!res.ok) {
    throw new Error("guide detail failed");
  }
  return res.json();
}

export { API_BASE_URL };
