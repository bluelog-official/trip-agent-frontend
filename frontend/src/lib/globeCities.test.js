import { describe, expect, it } from "vitest";
import { cityHeading, destinationSlug, normalizeGlobeCity, pinScale, trendValue } from "./globeCities";
import { parseRoute } from "./usePortalRoute";
import { createCityPin } from "./globePins";

describe("globe city helpers", () => {
  it("matches backend city slugs", () => {
    expect(destinationSlug("New York")).toBe("new_york");
    expect(destinationSlug("Da Nang")).toBe("danang");
    expect(cityHeading("paris", [{ destination: "Paris" }])).toBe("Paris");
    expect(parseRoute("/city/new_york")).toMatchObject({ name: "city", city: "new_york" });
    expect(parseRoute("/magazine-request")).toMatchObject({ name: "magazineRequest" });
    expect(parseRoute("/city/")).toMatchObject({ name: "notFound" });
  });

  it("shrinks pins as the period and the map get busier", () => {
    expect(pinScale("all", 1, false, 22)).toBeLessThan(pinScale("1w", 1, false, 22));
    expect(pinScale("1y", 1, false, 8)).toBeLessThan(pinScale("1m", 1, false, 8));
    expect(pinScale("1w", 1, true, 4)).toBeGreaterThan(pinScale("1w", 0, false, 4));
  });

  it("formats a signed trend and keeps new cities blank", () => {
    expect(trendValue({ trending_percent: 15, trending_new: false })).toBe("+15%");
    expect(trendValue({ trending_percent: -4, trending_new: false })).toBe("-4%");
    expect(trendValue({ trending_percent: null, trending_new: true })).toBe("");
  });

  it("drops a city pin that has no coordinates", () => {
    expect(normalizeGlobeCity({ slug: "paris", lat: 48.8, lng: 2.3, published_count: 2, keywords: ["Food"] }).slug).toBe("paris");
    expect(normalizeGlobeCity({ slug: "", lat: 1, lng: 2, published_count: 1 })).toBeNull();
  });
});

describe("globe pins", () => {
  it("sizes the count badge from the period scale", () => {
    const handlers = { current: { open: () => {}, hover: () => {} } };
    const week = createCityPin({ slug: "paris", city: "Paris", published_count: 2, is_top: true, period: "1w", pinScale: 1.2, label: "Paris, 2" }, handlers);
    const allTime = createCityPin({ slug: "rome", city: "Rome", published_count: 1, is_top: false, period: "all", pinScale: 0.5, label: "Rome, 1" }, handlers);
    expect(week.classList.contains("is-top")).toBe(true);
    expect(week.dataset.period).toBe("1w");
    expect(Number.parseInt(week.style.width, 10)).toBeGreaterThan(Number.parseInt(allTime.style.width, 10));
    expect(week.querySelector(".globe-pin-count").textContent).toBe("2");
  });
});
