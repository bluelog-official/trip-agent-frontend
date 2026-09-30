import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import GlobeMap from "./GlobeMap";
import i18n from "../../i18n/i18n";

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
  vote_count: 4,
  article_id: "paris_guide.md",
  country: "France",
  flag: "🇫🇷",
  thumbnail: "https://example.com/paris.jpg",
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
  vote_count: 1,
  article_id: "",
  flag: "🇮🇹",
  thumbnail: "",
};

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe("GlobeMap", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows a flat map preview, votes, and opens the city from a pin", async () => {
    await i18n.changeLanguage("en");
    const fetchMock = vi.fn(async (url, options) => {
      const href = String(url);
      if (href.includes("/api/votes")) {
        if (options?.method === "POST") {
          return jsonResponse({
            article_id: "paris_guide.md",
            vote_count: 5,
            voted: true,
            created: true,
          }, 201);
        }
        return jsonResponse({ votes: [{ article_id: "paris_guide.md", vote_count: 4, voted: false }] });
      }
      const period = new URL(href, "http://localhost").searchParams.get("period");
      if (period === "1w") return jsonResponse({ period: "1w", cities: [ROME] });
      return jsonResponse({ period: "all", cities: [PARIS, ROME] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const onOpenCity = vi.fn();
    render(<GlobeMap onOpenCity={onOpenCity} />);

    expect(await screen.findByTestId("flat-map")).toBeTruthy();
    expect(screen.getByRole("img", { name: "Flat world map" })).toBeTruthy();
    expect(document.querySelector("[data-label='asia']")?.textContent).toBe("Asia");
    expect(document.querySelector("[data-label='pacific']")?.textContent).toBe("Pacific");
    expect(document.querySelector("[data-label='atlantic']")?.textContent).toBe("Atlantic");
    expect(document.querySelector("[data-label='indian']")?.textContent).toBe("Indian Ocean");
    expect(screen.getAllByText("4 votes").length).toBeGreaterThan(0);
    expect(screen.getByText("2 guides")).toBeTruthy();
    expect(screen.getByText("QA 85")).toBeTruthy();
    expect(screen.getByText("+15%")).toBeTruthy();
    expect(screen.getByText("#Gastronomy #Nightlife")).toBeTruthy();

    const pin = screen.getByRole("button", { name: "Paris, 2 published guides" });
    fireEvent.mouseEnter(pin.parentElement);
    const preview = screen.getByRole("tooltip", { name: "Paris" });
    expect(preview.textContent).toContain("#Gastronomy");
    expect(preview.textContent).toContain("#Nightlife");
    expect(preview.querySelector("img")?.getAttribute("src")).toBe("https://example.com/paris.jpg");
    expect(pin.parentElement.classList.contains("is-open")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Vote" }));
    expect(onOpenCity).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByRole("button", { name: "Voted" })).toBeTruthy());

    fireEvent.click(pin);
    expect(onOpenCity).toHaveBeenCalledWith(expect.objectContaining({ slug: "paris" }));

    fireEvent.click(screen.getByRole("radio", { name: "1 Week" }));
    await waitFor(() => expect(screen.queryByText("2 guides")).toBeNull());
    expect(await screen.findByText("1 guides")).toBeTruthy();
    expect(screen.getByText("New")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Rome, 1 published guides" }));
    expect(onOpenCity).toHaveBeenCalledWith(expect.objectContaining({ slug: "rome" }));
  });
});
