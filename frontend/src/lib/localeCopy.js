const HANGUL = /[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3]/;

export function isEnglishLanguage(language) {
  const value = String(language || "").trim().toLowerCase();
  return value === "en" || value === "english";
}

export function containsHangul(text) {
  return HANGUL.test(String(text || ""));
}

export function englishField(text, fallback) {
  const source = String(text || "").replace(/\s+/g, " ").trim();
  if (!source || containsHangul(source)) return fallback;
  return source;
}

export function strictEnglishText(text, fallback, minLength = 1) {
  const clean = englishField(text, "");
  if (clean.length >= minLength) return clean;
  return fallback;
}

const REGION_LABELS = {
  en: { asia: "Asia", europe: "Europe", americas: "Americas", oceania: "Oceania" },
  ko: { asia: "아시아", europe: "유럽", americas: "아메리카", oceania: "오세아니아" },
};
const FOOD_LABELS = { en: "Local Food", ko: "현지 음식" };
const THEME_LABELS = {
  ko: {
    CityBreak: "도시 여행",
    Culture: "문화",
    Nightlife: "나이트라이프",
    Nature: "자연",
    SoloTravel: "혼자 여행",
    HiddenGems: "숨은 명소",
    LocalFood: "현지 음식",
    Foodie: "미식",
    StreetFood: "길거리 음식",
    Beach: "해변",
    Architecture: "건축",
    Museums: "박물관",
    WeekendTrip: "주말 여행",
    SlowTravel: "느린 여행",
    Photography: "사진",
  },
};
const CHROME_TAGS = new Set([
  ...Object.values(REGION_LABELS.en),
  ...Object.values(REGION_LABELS.ko),
  FOOD_LABELS.en,
  FOOD_LABELS.ko,
]);

function themeLabel(tag, language) {
  const clean = String(tag || "").replace(/^#/, "").trim();
  if (!clean) return "";
  if (isEnglishLanguage(language)) return clean;
  return THEME_LABELS.ko[clean] || clean;
}

export function presentGuideCard(card, language) {
  if (!card) return card;
  const english = isEnglishLanguage(language);
  const lang = english ? "en" : "ko";
  const destination = english ? englishField(card.destination, "Destination") : card.destination;
  const title = english ? englishField(card.title, `${destination} Trip Guide`) : card.title;
  const summary = english
    ? englishField(card.summary, `Local trip notes for ${destination}.`)
    : card.summary;
  const tags = [];
  (card.tags || []).forEach((tag) => {
    if (CHROME_TAGS.has(tag)) return;
    const next = themeLabel(tag, language);
    const label = english ? englishField(next, "") : next;
    if (label && !tags.includes(label)) tags.push(label);
  });
  const regionLabel = REGION_LABELS[lang][card.region] || "";
  if (regionLabel) tags.unshift(regionLabel);
  if (destination && !tags.includes(destination)) tags.splice(regionLabel ? 1 : 0, 0, destination);
  return { ...card, destination, title, summary, tags };
}

export function formatPublishedDate(iso, language) {
  if (!iso) return "";
  const date = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(isEnglishLanguage(language) ? "en-US" : "ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(date);
}
