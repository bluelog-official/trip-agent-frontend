import { describe, expect, it, vi, afterEach } from "vitest";
import { presentGuideCard } from "./localeCopy";
import { fetchGuideCards, fetchGuideDetail, toGuideCard } from "./guideCards";

const ARTICLE = `---
title: "A Perfect Weekend in Vienna"
hashtags: "#Culture #Architecture"
---
# A Perfect Weekend in Vienna

Vienna is a compact city with palaces, cafes, and museums enough for a short stay.

## Where to Eat in Vienna

| Category | Recommended Location | Estimated Cost | Rating |
| --- | --- | --- | --- |
| Cafe | Cafe Sperl | EUR 8 | 4.5/5 |
`;

describe("guide card tags", () => {
  it("uses the article hashtags instead of a fixed Local Food tag", () => {
    const card = toGuideCard("vienna_guide.md", { content: ARTICLE });
    expect(card.tags).toContain("Culture");
    expect(card.tags).toContain("Architecture");
    expect(card.tags).not.toContain("Local Food");
    expect(card.hasFood).toBe(true);

    const english = presentGuideCard(card, "en");
    expect(english.tags).not.toContain("Local Food");

    const korean = presentGuideCard(card, "ko");
    expect(korean.tags).toContain("문화");
    expect(korean.tags).not.toContain("현지 음식");
  });

  it("keeps the city when the filename also carries duration and budget", () => {
    const card = toGuideCard("tokyo_1_days_50usd_guide.md", {
      content: `---
title: "Tokyo: 1 Day on Under $50/day"
city: "Tokyo"
duration_key: "1_days"
budget_key: "50usd"
---
# Tokyo: 1 Day on Under $50/day

A one-day Tokyo walk that stays inside a small daily budget and eats at market counters.

## Where to Eat in Tokyo

| Category | Recommended Location | Estimated Cost | Rating |
| --- | --- | --- | --- |
| Stall | Ameya-Yokocho | $8 | 4/5 |
`,
    });
    expect(card.destination).toBe("Tokyo");
    expect(card.durationKey).toBe("1_days");
    expect(card.budgetKey).toBe("50usd");
    expect(card.budgetFilter).toBe("under_50");
    expect(card.tags).toContain("1 Day");
    expect(card.tags).toContain("Under $50/day");
  });
});

describe("static guide fallback", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads published routes when the guide API is down", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("offline");
    }));
    const cards = await fetchGuideCards();
    expect(cards.length).toBeGreaterThanOrEqual(10);
    expect(cards.some((card) => card.publicSlug === "korea-seoul-food-route")).toBe(true);

    const detail = await fetchGuideDetail("japan-tokyo-night-bus");
    expect(String(detail.article_markdown || detail.content).length).toBeGreaterThanOrEqual(1500);
    expect(detail.qa_result.is_approved).toBe(true);
  });

  it("keeps the static article when the API responds without a body", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ id: "japan_tokyo_night_bus_guide.md", content: "" }),
    })));
    const detail = await fetchGuideDetail("japan-tokyo-night-bus");
    expect(String(detail.article_markdown || detail.content)).toContain("Highway night buses");
  });

  it("ignores an API not-found essay and keeps the static route", async () => {
    const stub = `${"데이터를 찾을 수 없습니다. ".repeat(40)}\n\nThe desk could not open this file.`;
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ id: "korea_seoul_food_route_guide.md", content: stub }),
    })));
    const detail = await fetchGuideDetail("korea-seoul-food-route");
    expect(detail.content).toContain("Gwangjang Market");
  });
});
