import { API_BASE_URL } from "./guideCards";
import { isEnglishLanguage } from "./localeCopy";

export const GLOBE_PERIODS = ["1w", "2w", "1m", "1y", "all"];

const PERIOD_BASE = {
  "1w": 1,
  "2w": 0.9,
  "1m": 0.76,
  "1y": 0.62,
  all: 0.5,
};

export function destinationSlug(destination) {
  const text = String(destination || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  if (text === "da nang" || text === "danang") return "danang";
  return text.replace(/ +/g, "_");
}

export function cityHeading(slug, cards = []) {
  const match = cards.find((card) => destinationSlug(card?.destination) === slug);
  if (match?.destination) return match.destination;
  return String(slug || "")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function globeCityLabel(city, language) {
  if (!city) return "";
  if (!isEnglishLanguage(language) && city.city_ko) return city.city_ko;
  return city.city || city.slug || "";
}

export function pinScale(period, recency, isTop, cityCount) {
  const base = PERIOD_BASE[period] ?? PERIOD_BASE.all;
  const density = cityCount > 18 ? 0.78 : cityCount > 12 ? 0.88 : 1;
  const recent = 0.8 + 0.3 * (Number(recency) || 0);
  const topBoost = isTop ? 1.16 : 1;
  return Math.round(base * density * recent * topBoost * 100) / 100;
}

export function trendValue(city) {
  if (!city || city.trending_new || city.trending_percent == null) return "";
  const value = Number(city.trending_percent);
  if (!Number.isFinite(value)) return "";
  return `${value > 0 ? "+" : ""}${value}%`;
}

export function normalizeGlobeCity(raw) {
  if (!raw || typeof raw !== "object") return null;
  const lat = Number(raw.lat);
  const lng = Number(raw.lng);
  const published = Number(raw.published_count);
  const slug = String(raw.slug || "").trim().toLowerCase();
  if (!slug || !Number.isFinite(lat) || !Number.isFinite(lng) || !Number.isFinite(published)) return null;
  const trending = raw.trending_percent == null ? null : Number(raw.trending_percent);
  return {
    city: String(raw.city || slug),
    city_ko: String(raw.city_ko || ""),
    slug,
    lat,
    lng,
    published_count: published,
    rank: Number(raw.rank) || 0,
    is_top: Boolean(raw.is_top),
    quality_score: Number(raw.quality_score) || 0,
    trending_percent: Number.isFinite(trending) ? trending : null,
    trending_new: Boolean(raw.trending_new),
    keywords: Array.isArray(raw.keywords) ? raw.keywords.map((item) => String(item || "").trim()).filter(Boolean) : [],
    latest_at: String(raw.latest_at || ""),
    recency: Number.isFinite(Number(raw.recency)) ? Number(raw.recency) : 1,
  };
}

export async function fetchGlobeCities(period = "all") {
  const key = GLOBE_PERIODS.includes(period) ? period : "all";
  const res = await fetch(`${API_BASE_URL}/globe/cities?period=${encodeURIComponent(key)}`);
  if (!res.ok) throw new Error("globe cities failed");
  const data = await res.json();
  const cities = Array.isArray(data?.cities) ? data.cities.map(normalizeGlobeCity).filter(Boolean) : [];
  return { period: String(data?.period || key), cities };
}
