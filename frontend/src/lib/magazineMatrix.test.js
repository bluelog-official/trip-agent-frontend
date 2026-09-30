import { describe, expect, it } from "vitest";
import {
  budgetFilterFor,
  matchesMagazineMatrix,
  parseGuideFilename,
} from "./magazineMatrix";

describe("magazine matrix filenames", () => {
  it("reads the city, duration, and budget from the guide name", () => {
    expect(parseGuideFilename("tokyo_1_days_50usd_guide.md")).toEqual({
      citySlug: "tokyo",
      durationKey: "1_days",
      budgetKey: "50usd",
    });
    expect(parseGuideFilename("tokyo_3_days_200usd_guide.md").budgetKey).toBe("200usd");
    expect(parseGuideFilename("tokyo_1_week_budget_guide.md")).toMatchObject({
      durationKey: "1_week",
      budgetKey: "budget",
    });
    expect(parseGuideFilename("new_york_1_week_luxury_guide.md").citySlug).toBe("new_york");
    expect(parseGuideFilename("tokyo_guide.md").durationKey).toBe("");
  });

  it("maps budget tokens onto the filter chips", () => {
    expect(budgetFilterFor("50usd")).toBe("under_50");
    expect(budgetFilterFor("budget")).toBe("under_50");
    expect(budgetFilterFor("100usd")).toBe("per_100");
    expect(budgetFilterFor("200usd")).toBe("per_200");
    expect(budgetFilterFor("luxury")).toBe("luxury");
  });

  it("filters magazines on the client", () => {
    const day = { durationKey: "1_days", budgetFilter: "under_50" };
    const week = { durationKey: "1_week", budgetFilter: "under_50" };
    const legacy = { durationKey: "", budgetFilter: "" };

    expect(matchesMagazineMatrix(day, "all", "all")).toBe(true);
    expect(matchesMagazineMatrix(day, "1_days", "under_50")).toBe(true);
    expect(matchesMagazineMatrix(day, "3_days", "all")).toBe(false);
    expect(matchesMagazineMatrix(week, "1_week", "under_50")).toBe(true);
    expect(matchesMagazineMatrix(week, "1_week", "luxury")).toBe(false);
    expect(matchesMagazineMatrix(legacy, "all", "all")).toBe(true);
    expect(matchesMagazineMatrix(legacy, "1_days", "all")).toBe(false);
    expect(matchesMagazineMatrix(legacy, "all", "under_50")).toBe(false);
  });
});
