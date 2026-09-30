import { describe, expect, it } from "vitest";
import { allowedUrl, sanitizeMarkdown } from "./sanitizeMarkdown";

const GUIDE = [
  "## K-Food in Seoul",
  "",
  "A morning walk and a noodle counter.",
  "",
  "| Category | Cost |",
  "| --- | --- |",
  "| Lunch | 12 |",
  "",
  "[Map](https://example.com/seoul)",
].join("\n");

describe("sanitizeMarkdown", () => {
  it("keeps magazine markdown and drops script, iframe, onload, and javascript urls", () => {
    const dirty = [
      GUIDE,
      "<script>alert(1)</script>",
      '<iframe src="https://evil.example"></iframe>',
      '<img src="https://images.example/bowl.jpg" onload="alert(1)">',
      "[steal](javascript:alert(1))",
      '<a href="javascript:alert(1)">click</a>',
    ].join("\n\n");

    const clean = sanitizeMarkdown(dirty);
    expect(clean).toContain("## K-Food in Seoul");
    expect(clean).toContain("| Lunch | 12 |");
    expect(clean).toContain("https://example.com/seoul");
    expect(clean.toLowerCase()).not.toContain("<script");
    expect(clean.toLowerCase()).not.toContain("iframe");
    expect(clean.toLowerCase()).not.toContain("onload");
    expect(clean.toLowerCase()).not.toContain("javascript:");
    expect(clean).not.toContain("alert(1)");
  });

  it("rejects javascript, vbscript, and data urls", () => {
    expect(allowedUrl("javascript:alert(1)")).toBe("");
    expect(allowedUrl("JavaScript:alert(1)")).toBe("");
    expect(allowedUrl("vbscript:msg")).toBe("");
    expect(allowedUrl("data:text/html,hi")).toBe("");
    expect(allowedUrl("https://bluelogtrip.com/guide")).toBe("https://bluelogtrip.com/guide");
  });
});
