import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import en from "../i18n/locales/en.json";
import ko from "../i18n/locales/ko.json";
import { canonicalBootScript } from "./canonicalPath";
import { GUIDE_FILE_TO_SLUG } from "./guideAliases";
import {
  applySeoDocument,
  buildSitemapXml,
  categoryPages,
  guideCanonicalPath,
  listPublishedGuides,
  publisherPages,
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

  it("lists each published guide once on its canonical URL", () => {
    const guides = listPublishedGuides();
    expect(guides.length).toBeGreaterThanOrEqual(32);
    const names = guides.map((guide) => guide.name);
    expect(names).toContain("seoul_guide.md");
    expect(names).toContain("los_angeles_guide.md");
    expect(names).toContain("dubrovnik_guide.md");
    expect(names).toContain("busan_guide.md");
    expect(names).toContain("vancouver_guide.md");

    const aliased = guides.filter((guide) => guide.slug && guide.slug !== guide.name);
    expect(aliased.length).toBe(Object.keys(GUIDE_FILE_TO_SLUG).length);
    for (const guide of guides) {
      if (guide.slug && guide.slug !== guide.name) {
        expect(GUIDE_FILE_TO_SLUG[guide.name]).toBe(guide.slug);
      } else {
        expect(GUIDE_FILE_TO_SLUG[guide.name]).toBeUndefined();
      }
    }

    const xml = buildSitemapXml("https://bluelogtrip.com", guides, "2026-10-09");
    const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1]);
    expect(new Set(locs).size).toBe(locs.length);
    for (const loc of locs) {
      const path = new URL(loc).pathname;
      expect(path === "/" || !path.endsWith("/"), loc).toBe(true);
      expect(path.startsWith("/guide/"), loc).toBe(false);
      expect(loc.startsWith("https://www.bluelogtrip.com"), loc).toBe(true);
    }
    for (const guide of guides) {
      expect(xml).toContain(`https://www.bluelogtrip.com${guideCanonicalPath(guide)}`);
      if (guide.slug && guide.slug !== guide.name) {
        expect(xml).not.toContain(`https://www.bluelogtrip.com/guides/${guide.name}`);
        expect(xml).not.toContain(`https://www.bluelogtrip.com/guide/${guide.name}`);
      }
    }
    for (const publicPath of SERVICE_SITEMAP_PATHS) {
      expect(xml).toContain(`https://www.bluelogtrip.com${publicPath}`);
    }
    expect(xml).not.toContain("https://bluelogtrip.com/");
    expect(xml).not.toContain("/mypage");
    expect(xml).not.toContain("<script");
  });

  it("puts title, description, Open Graph, JSON-LD, and article text in the initial HTML", () => {
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
    expect(html).toContain("<h2>");
    expect(html).toContain("<p>");
    expect(html).toContain("application/ld+json");
    expect(html).toContain('"@type":"Article"');
    expect(html).toContain('"@type":"TouristAttraction"');
    const text = html.replace(/<script type="application\/ld\+json">[\s\S]*?<\/script>/g, " ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
    expect(text.length).toBeGreaterThan(300);
    expect(html).not.toMatch(/<script(?![^>]*type="application\/ld\+json")/i);
  });

  it("publishes long-form routes and category pages with at least five guides", () => {
    const guides = listPublishedGuides();
    const food = guides.find((guide) => guide.slug === "korea-seoul-food-route");
    const nightBus = guides.find((guide) => guide.slug === "japan-tokyo-night-bus");
    expect(food?.slug).toBe("korea-seoul-food-route");
    expect(nightBus?.slug).toBe("japan-tokyo-night-bus");
    for (const guide of [food, nightBus]) {
      const page = renderGuideArticle(guide.markdown, guide.slug);
      page.type = "article";
      const html = applySeoDocument(SHELL, page);
      expect(html).toContain(`https://www.bluelogtrip.com/guides/${guide.slug}`);
      expect(html).toContain("<h1>");
      expect(html).toContain("<h2>");
      expect(html).toContain("<h3>");
      expect(html).toContain('"@type":"Article"');
      const text = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
      expect(text.length).toBeGreaterThanOrEqual(1500);
    }
    const xml = buildSitemapXml("https://www.bluelogtrip.com", guides, "2026-10-20");
    expect(xml).toContain("https://www.bluelogtrip.com/guides/korea-seoul-food-route");
    expect(xml).toContain("https://www.bluelogtrip.com/guides/japan-tokyo-night-bus");
    expect(xml).toContain("https://www.bluelogtrip.com/privacy");
    expect(xml).toContain("https://www.bluelogtrip.com/local-food");

    const privacy = publisherPages(en, guides).find((page) => page.path === "/privacy");
    expect(privacy.body).toContain("Google AdSense");
    expect(privacy.body).toContain("DART");
    expect(privacy.body.toLowerCase()).toContain("third-party");

    for (const page of categoryPages(guides)) {
      const links = page.body.match(/<li><a /g) || [];
      expect(links.length, page.path).toBeGreaterThanOrEqual(5);
    }
  });

  it("writes static guide and service HTML, and redirects aliases to the canonical URL", () => {
    const vercel = JSON.parse(readFileSync(path.join(FRONTEND_DIR, "vercel.json"), "utf8"));
    expect(vercel.trailingSlash).toBe(false);
    const guidesRedirect = vercel.redirects.find((rule) => rule.source === "/guides");
    expect(guidesRedirect).toMatchObject({ destination: "/", statusCode: 301 });
    expect(vercel.redirects.find((rule) => rule.source === "/guide/:path+")).toMatchObject({
      destination: "/guides/:path+",
      statusCode: 301,
    });
    expect(vercel.redirects.some((rule) => rule.destination === "https://www.bluelogtrip.com/$1")).toBe(true);
    for (const [fileName, slug] of Object.entries(GUIDE_FILE_TO_SLUG)) {
      expect(vercel.redirects.find((rule) => rule.source === `/guides/${fileName}`)).toMatchObject({
        destination: `/guides/${slug}`,
        statusCode: 301,
      });
    }
    expect(vercel.rewrites.some((rule) => rule.source === "/guides/:path+" && rule.destination === "/seo/guide/:path+")).toBe(true);
    const indexHtml = readFileSync(path.join(FRONTEND_DIR, "index.html"), "utf8");
    expect(indexHtml).toContain(canonicalBootScript());
    expect(vercel.rewrites.some((rule) => rule.source === "/events" && rule.destination === "/events.html")).toBe(true);
    expect(vercel.rewrites.some((rule) => rule.source === "/privacy" && rule.destination === "/privacy.html")).toBe(true);
    expect(vercel.rewrites.some((rule) => rule.source === "/local-food" && rule.destination === "/local-food.html")).toBe(true);

    expect(indexHtml).toContain('name="description"');
    expect(indexHtml).toContain('property="og:title"');
    expect(indexHtml).toContain("<h1>");
    expect(indexHtml).toContain("BlueLog Trip publishes city guides");
  });
});

describe("canonical tags on rendered pages", () => {
  it("inserts a canonical tag and folds aliases onto the public URL", () => {
    const bare = SHELL.replace(/\s*<link rel="canonical"[^>]*>/, "");
    const about = applySeoDocument(bare, {
      path: "/about/",
      title: "About",
      description: "About BlueLog Trip",
      body: "<p>About</p>",
    });
    expect(about).toContain('<link rel="canonical" href="https://www.bluelogtrip.com/about" />');
    const food = applySeoDocument(SHELL, {
      path: "/guide/korea_seoul_food_route_guide.md/",
      title: "Food",
      description: "A Seoul food route",
      body: "<p>Food</p>",
    });
    expect(food).toContain(
      '<link rel="canonical" href="https://www.bluelogtrip.com/guides/korea-seoul-food-route" />',
    );
    expect(food).toContain('property="og:url" content="https://www.bluelogtrip.com/guides/korea-seoul-food-route"');
  });
});

describe("writePublisherSite", () => {
  it("is exported for the production build", () => {
    expect(typeof writePublisherSite).toBe("function");
  });
});
