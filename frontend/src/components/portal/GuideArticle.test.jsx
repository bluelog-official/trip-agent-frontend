import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import GuideArticle from "./GuideArticle";
import i18n from "../../i18n/i18n";

const GUIDE = {
  content: `---
title: "Tokyo: 1 Day on Under $50/day"
city: "Tokyo"
duration: "1 Day"
budget: "Under $50/day"
---
# Tokyo: 1 Day on Under $50/day

Tokyo on a 1 day stay only works if the budget decides the route.

## 1 Day in Tokyo

### Day 1: Asakusa

Be at Senso-ji before 9:00. Keep meals inside $50.

| Category | Recommended Location | Estimated Cost | Rating |
| --- | --- | --- | --- |
| Standing soba | Asakusa tachigui counter | $4–8 | 4.4/5 |
`,
};

describe("GuideArticle trip plan", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the day, the time, and the cost before the article body", async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ votes: [] }),
    })));
    render(
      <GuideArticle
        guide={GUIDE}
        fileName="tokyo_1_days_50usd_guide.md"
        onNavigate={() => {}}
      />,
    );

    const plan = screen.getByRole("heading", { name: "Route at a glance" }).closest("section");
    expect(plan.textContent).toContain("Time needed");
    expect(plan.textContent).toContain("1 Day");
    expect(plan.textContent).toContain("Daily cost");
    expect(plan.textContent).toContain("Under $50/day");
    expect(plan.textContent).toContain("Day 1: Asakusa");
    expect(plan.textContent).toContain("Be at Senso-ji before 9:00.");
    expect(plan.textContent).toContain("Asakusa tachigui counter");
    expect(plan.textContent).toContain("$4–8");
    expect(screen.getByRole("table")).toBeTruthy();
  });
});
