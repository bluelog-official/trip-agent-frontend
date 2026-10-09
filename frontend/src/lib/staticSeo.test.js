import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import en from "../i18n/locales/en.json";
import ko from "../i18n/locales/ko.json";
import {
  applySeoDocument,
  buildSitemapXml,
  listPublishedGuides,
  renderGuideArticle,
  SERVICE_SITEMAP_PATHS,
  writePublisherSite,
} from "./staticSeo";

const FRONTEND_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const SHELL = `<!doctype html>
<html lang="en">
  <head>
    <title>Old</title>
    <meta name="description" content="Old description" />
    <link rel="canonical" href="https://www.bluelogtrip.com/" />
    <meta property="og:title" content="Old" />
    <meta property="og:description" content="Old description" />
    <meta property="og:url" content="https://www.bluelogtrip.com/" />
    <meta property="og:type" content="website" />
    <meta name="twitter:title" content="Old" />
    <meta name="twitter:description" content="Old description" />
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>`;

describe("publisher pages and sitemap", () => {
  it("keeps at least 300 characters of explanation on each thin page", () => {
    for (const key of ["hero.about", "events.purpose", "wallet.purpose", "promote.purpose", "community.purpose"]) {
      const [group, name] = key.split(".");
      expect(en[group][name].length, key).toBeGreaterThanOrEqual(300);
      expect(ko[group][name].length, key).toBeGreaterThanOrEqual(300);
    }
  });

  it("lists all 32 published guides under /guide and /guides", () => {
    const guides = listPublishedGuides();
    expect(guides).toHaveLength(32);
    const names = guides.map((guide) => guide.name);
    expect(names).toContain("seoul_guide.md");
    expect(names).toContain("los_angeles_guide.md");
    expect(names).toContain("dubrovnik_guide.md");

    const xml = buildSitemapXml("https://bluelogtrip.com", guides, "2026-10-09");
    for (const name of names) {
      expect(xml).toContain(`https://bluelogtrip.com/guide/${name}`);
      expect(xml).toContain(`https://bluelogtrip.com/guides/${name}`);
    }
    for (const publicPath of SERVICE_SITEMAP_PATHS) {
      expect(xml).toContain(`https://bluelogtrip.com${publicPath}`);
    }
    expect(xml).not.toContain("<script");
  });

  it("puts title, description, Open Graph, and article text in the initial HTML", () => {
    const seoul = listPublishedGuides().find((guide) => guide.name === "seoul_guide.md");
    const markdown = readFileSync(seoul.filePath, "utf8");
    const page = renderGuideArticle(markdown, seoul.name);
    page.type = "article";
    const html = applySeoDocument(SHELL, page);
    expect(html).toContain("<title>");
    expect(html).toContain('name="description"');
    expect(html).toContain('property="og:title"');
    expect(html).toContain('property="og:description"');
    expect(html).toContain('property="og:url"');
    expect(html).toContain("https://www.bluelogtrip.com/guides/seoul_guide.md");
    expect(html).toContain('property="og:type" content="article"');
    expect(html).toContain("<h1>");
    expect(html).toContain("<p>");
    const text = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
    expect(text.length).toBeGreaterThan(300);
    expect(html).not.toContain("<script");
  });

  it("writes static guide and service HTML, and redirects /guides to the home list", () => {
    const vercel = JSON.parse(readFileSync(path.join(FRONTEND_DIR, "vercel.json"), "utf8"));
    const guidesRedirect = vercel.redirects.find((rule) => rule.source === "/guides");
    expect(guidesRedirect).toMatchObject({ destination: "/", statusCode: 301 });
    expect(vercel.rewrites.some((rule) => rule.source === "/guides/:path+" && rule.destination === "/seo/guide/:path+")).toBe(true);
    expect(vercel.rewrites.some((rule) => rule.source === "/events" && rule.destination === "/events.html")).toBe(true);

    const indexHtml = readFileSync(path.join(FRONTEND_DIR, "index.html"), "utf8");
    expect(indexHtml).toContain('name="description"');
    expect(indexHtml).toContain('property="og:title"');
    expect(indexHtml).toContain("<h1>");
    expect(indexHtml).toContain("BlueLog Trip publishes city guides");
  });
});

describe("writePublisherSite", () => {
  it("is exported for the production build", () => {
    expect(typeof writePublisherSite).toBe("function");
  });
});
