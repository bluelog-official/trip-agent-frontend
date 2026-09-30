import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { applyPageHead, canonicalHref, SITE_ORIGIN } from "./documentHead";

const FRONTEND_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

describe("canonical and Open Graph head", () => {
  it("builds absolute canonical URLs on the public origin", () => {
    expect(SITE_ORIGIN).toBe("https://www.bluelogtrip.com");
    expect(canonicalHref("/")).toBe("https://www.bluelogtrip.com/");
    expect(canonicalHref("/about")).toBe("https://www.bluelogtrip.com/about");
    expect(canonicalHref("/about/")).toBe("https://www.bluelogtrip.com/about");
    expect(canonicalHref("/privacy")).toBe("https://www.bluelogtrip.com/privacy");
    expect(canonicalHref("/terms")).toBe("https://www.bluelogtrip.com/terms");
    expect(canonicalHref("/contact")).toBe("https://www.bluelogtrip.com/contact");
    expect(canonicalHref("/guide/kyoto_guide.md")).toBe(
      "https://www.bluelogtrip.com/guide/kyoto_guide.md",
    );
  });

  it("writes canonical and Open Graph tags for the current path", () => {
    applyPageHead({
      title: "About · BlueLog Trip",
      description: "BlueLog Trip writes local city guides.",
      pathname: "/about",
      type: "website",
      locale: "en_US",
    });

    expect(document.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe(
      "https://www.bluelogtrip.com/about",
    );
    expect(document.querySelector('meta[property="og:title"]')?.getAttribute("content")).toBe(
      "About · BlueLog Trip",
    );
    expect(document.querySelector('meta[property="og:url"]')?.getAttribute("content")).toBe(
      "https://www.bluelogtrip.com/about",
    );
    expect(document.querySelector('meta[property="og:type"]')?.getAttribute("content")).toBe("website");
    expect(document.querySelector('meta[property="og:locale"]')?.getAttribute("content")).toBe("en_US");

    applyPageHead({
      title: "Kyoto · BlueLog Trip",
      description: "A local Kyoto guide.",
      pathname: "/guide/kyoto_guide.md",
      type: "article",
      locale: "ko_KR",
      image: "https://images.example/kyoto.jpg",
    });

    expect(document.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe(
      "https://www.bluelogtrip.com/guide/kyoto_guide.md",
    );
    expect(document.querySelector('meta[property="og:type"]')?.getAttribute("content")).toBe("article");
    expect(document.querySelector('meta[property="og:locale"]')?.getAttribute("content")).toBe("ko_KR");
    expect(document.querySelector('meta[property="og:image"]')?.getAttribute("content")).toBe(
      "https://images.example/kyoto.jpg",
    );
    expect(document.querySelector('meta[name="twitter:card"]')?.getAttribute("content")).toBe(
      "summary_large_image",
    );
    expect(document.querySelector('meta[name="twitter:title"]')?.getAttribute("content")).toBe(
      "Kyoto · BlueLog Trip",
    );
    expect(document.querySelector('meta[name="twitter:image"]')?.getAttribute("content")).toBe(
      "https://images.example/kyoto.jpg",
    );

    applyPageHead({
      title: "Home",
      description: "Guides",
      pathname: "/",
      image: "",
    });
    expect(document.querySelector('meta[property="og:image"]')).toBeNull();
    expect(document.querySelector('meta[name="twitter:image"]')).toBeNull();
    expect(document.querySelector('meta[name="twitter:card"]')?.getAttribute("content")).toBe("summary");
  });
});

describe("robots.txt", () => {
  it("allows every crawler and points at the public sitemap", () => {
    const robots = readFileSync(path.join(FRONTEND_DIR, "public/robots.txt"), "utf8");
    expect(robots).toMatch(/User-agent:\s*\*\s*Allow:\s*\//);
    expect(robots).toContain("Sitemap: https://bluelogtrip.com/sitemap.xml");
  });
});
