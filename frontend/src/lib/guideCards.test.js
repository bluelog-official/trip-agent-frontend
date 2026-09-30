import { describe, expect, it } from "vitest";
import { presentGuideCard } from "./localeCopy";
import { toGuideCard } from "./guideCards";

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
});
