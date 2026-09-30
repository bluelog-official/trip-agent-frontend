import { describe, expect, it } from "vitest";
import { matchesKCulture, readKCulture, themesFromFilename } from "./kculture";

describe("K-Culture themes", () => {
  it("reads theme tokens from the sample filenames", () => {
    expect(themesFromFilename("korea_3_days_kbeauty_kfood_guide.md")).toEqual(["k-food", "k-beauty"]);
    expect(themesFromFilename("seoul_1_day_kpop_trend_guide.md")).toEqual(["k-pop", "k-trend"]);
    expect(themesFromFilename("korea_1_week_heritage_luxury_guide.md")).toEqual(["k-trend"]);
    expect(themesFromFilename("seoul_guide.md")).toEqual([]);
  });

  it("marks only Korea spotlight guides and filters them", () => {
    const beauty = readKCulture(
      "korea_3_days_kbeauty_kfood_guide.md",
      "---\nhot_country: \"Korea\"\nk_themes: \"K-Beauty K-Food\"\n---\n",
    );
    const plain = readKCulture("seoul_guide.md", "---\ncity: \"Seoul\"\n---\n");
    expect(beauty.hotCountry).toBe(true);
    expect(beauty.themeLabels).toEqual(["K-Food", "K-Beauty"]);
    expect(plain.hotCountry).toBe(false);

    expect(matchesKCulture(beauty, "all", false)).toBe(true);
    expect(matchesKCulture(plain, "all", true)).toBe(false);
    expect(matchesKCulture(beauty, "k-food", true)).toBe(true);
    expect(matchesKCulture(beauty, "k-pop", true)).toBe(false);
  });
});
