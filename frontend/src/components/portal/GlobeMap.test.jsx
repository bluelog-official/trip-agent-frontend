import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import GlobeMap from "./GlobeMap";
import i18n from "../../i18n/i18n";

const flyTo = vi.fn();

vi.mock("./GlobeScene", () => ({
  default: function MockGlobeScene({ cities, onOpenCity, onReady }) {
    onReady?.({ flyTo });
    return (
      <div data-testid="globe-scene">
        {cities.map((city) => (
          <button key={city.slug} type="button" onClick={() => onOpenCity(city)}>
            pin-{city.slug}
          </button>
        ))}
      </div>
    );
  },
}));

const PARIS = {
  city: "Paris",
  city_ko: "파리",
  slug: "paris",
  lat: 48.8566,
  lng: 2.3522,
  published_count: 2,
  rank: 1,
  is_top: true,
  quality_score: 85,
  trending_percent: 15,
  trending_new: false,
  keywords: ["Gastronomy", "Nightlife"],
  latest_at: "2026-09-28",
  recency: 1,
};

const ROME = {
  ...PARIS,
  city: "Rome",
  city_ko: "로마",
  slug: "rome",
  lat: 41.9,
  lng: 12.5,
  published_count: 1,
  rank: 2,
  quality_score: 50,
  trending_percent: null,
  trending_new: true,
  keywords: ["Museums"],
  recency: 0.4,
};

function jsonResponse(body) {
  return { ok: true, status: 200, json: async () => body };
}

describe("GlobeMap", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    flyTo.mockReset();
  });

  it("filters by period, shows rank metrics, flies to a city, and opens a pin", async () => {
    await i18n.changeLanguage("en");
    const fetchMock = vi.fn(async (url) => {
      const period = new URL(url, "http://localhost").searchParams.get("period");
      if (period === "1w") return jsonResponse({ period: "1w", cities: [ROME] });
      return jsonResponse({ period: "all", cities: [PARIS, ROME] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const onOpenCity = vi.fn();
    render(<GlobeMap onOpenCity={onOpenCity} />);

    expect(await screen.findByTestId("globe-scene")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Paris/ }));
    expect(screen.getByText("2 guides")).toBeTruthy();
    expect(screen.getByText("QA 85")).toBeTruthy();
    expect(screen.getByText("+15%")).toBeTruthy();
    expect(screen.getByText("#Gastronomy #Nightlife")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Paris/ }));
    await waitFor(() => expect(flyTo).toHaveBeenCalledWith(expect.objectContaining({ slug: "paris", lat: 48.8566 })));
    expect(onOpenCity).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("radio", { name: "1 Week" }));
    await waitFor(() => expect(screen.queryByText("2 guides")).toBeNull());
    expect(await screen.findByText("1 guides")).toBeTruthy();
    expect(screen.getByText("New")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "pin-rome" }));
    expect(onOpenCity).toHaveBeenCalledWith(expect.objectContaining({ slug: "rome" }));
  });
});
