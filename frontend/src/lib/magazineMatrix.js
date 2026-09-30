const MATRIX_NAME =
  /^(?<city>.+)_(?<duration>1_days|3_days|1_week)_(?<budget>50usd|100usd|200usd|budget|luxury)_guide\.md$/i;

export const DURATION_FILTERS = [
  { id: "all", labelKey: "matrix.all" },
  { id: "1_days", labelKey: "matrix.duration.oneDay" },
  { id: "3_days", labelKey: "matrix.duration.threeDays" },
  { id: "1_week", labelKey: "matrix.duration.oneWeek" },
];

export const BUDGET_FILTERS = [
  { id: "all", labelKey: "matrix.all" },
  { id: "under_50", labelKey: "matrix.budget.under50" },
  { id: "per_100", labelKey: "matrix.budget.per100" },
  { id: "per_200", labelKey: "matrix.budget.per200" },
  { id: "luxury", labelKey: "matrix.budget.luxury" },
];

const DURATION_KEYS = new Set(["1_days", "3_days", "1_week"]);

const DURATION_LABELS = {
  "1_days": "1 Day",
  "3_days": "3 Days",
  "1_week": "1 Week",
};

const BUDGET_LABELS = {
  "50usd": "Under $50/day",
  budget: "Under $50/day",
  "100usd": "$100/day",
  "200usd": "$200/day",
  luxury: "Luxury",
};

const BUDGET_FILTER_IDS = {
  "50usd": "under_50",
  budget: "under_50",
  "100usd": "per_100",
  "200usd": "per_200",
  luxury: "luxury",
};

export function parseGuideFilename(guideId) {
  const name = String(guideId || "").split("/").pop();
  const match = MATRIX_NAME.exec(name);
  if (!match?.groups) {
    return {
      citySlug: name.replace(/_guide\.md$/i, ""),
      durationKey: "",
      budgetKey: "",
    };
  }
  return {
    citySlug: match.groups.city.toLowerCase(),
    durationKey: match.groups.duration.toLowerCase(),
    budgetKey: match.groups.budget.toLowerCase(),
  };
}

export function durationKeyFor(value) {
  const key = String(value || "").trim().toLowerCase();
  return DURATION_KEYS.has(key) ? key : "";
}

export function budgetKeyFor(value) {
  const key = String(value || "").trim().toLowerCase();
  return Object.prototype.hasOwnProperty.call(BUDGET_FILTER_IDS, key) ? key : "";
}

export function budgetFilterFor(budgetKey) {
  return BUDGET_FILTER_IDS[budgetKey] || "";
}

export function durationLabelFor(durationKey) {
  return DURATION_LABELS[durationKey] || "";
}

export function budgetLabelFor(budgetKey) {
  return BUDGET_LABELS[budgetKey] || "";
}

export function matchesMagazineMatrix(card, durationFilter, budgetFilter) {
  const duration = durationFilter || "all";
  const budget = budgetFilter || "all";
  if (duration === "all" && budget === "all") return true;
  if (duration !== "all" && card?.durationKey !== duration) return false;
  if (budget !== "all" && card?.budgetFilter !== budget) return false;
  return true;
}
