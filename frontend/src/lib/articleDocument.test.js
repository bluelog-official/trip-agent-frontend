import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { extractTripPlan } from "./articleDocument";

const SEOUL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../guides/seoul_guide.md");

describe("extractTripPlan", () => {
  it("pulls the stay length, each day, and the meal prices out of a guide", () => {
    const plan = extractTripPlan(readFileSync(SEOUL, "utf8"));
    expect(plan.duration).toBe("4 Days");
    expect(plan.days.map((day) => day.label)).toEqual([
      "Day 1: Gyeongbokgung, Bukchon, and Insadong",
      "Day 2: Changdeokgung, then a food market",
      "Day 3: A modern neighborhood and the river",
      "Day 4: A last soup, then Incheon",
    ]);
    expect(plan.days[0].note).toMatch(/Gyeongbokgung/);
    expect(plan.costs[0]).toEqual({
      place: "Gwangjang Market stalls",
      amount: "₩8,000–₩15,000",
    });
    expect(plan.costs.length).toBeGreaterThanOrEqual(4);
  });

  it("uses the duration key when the visible duration line is missing", () => {
    const plan = extractTripPlan(`---
duration_key: "3_days"
budget: "Under $50/day"
---
# Walk

### Day 1: Market

Eat at the first stall.
`);
    expect(plan.duration).toBe("3 Days");
    expect(plan.budget).toBe("Under $50/day");
    expect(plan.days).toEqual([{ label: "Day 1: Market", note: "Eat at the first stall." }]);
    expect(plan.costs).toEqual([]);
  });

  it("returns an empty plan when the guide has no route facts", () => {
    expect(extractTripPlan("# Notes\n\nA short paragraph.")).toEqual({
      duration: "",
      budget: "",
      days: [],
      costs: [],
    });
  });
});
