import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { absoluteCanonical, canonicalPath, publicOrigin, SITE_ORIGIN } from "./canonicalPath.js";
import { readKCulture } from "./kculture.js";

const LIB_DIR = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(LIB_DIR, "../../..");
export { SITE_ORIGIN };
const GUIDE_NAME = /^[a-z0-9_]+_guide\.md$/;
const ENGLISH_COPY = path.resolve(LIB_DIR, "../i18n/locales/en.json");

export const SERVICE_SITEMAP_PATHS = [
  "/about",
  "/contact",
  "/privacy",
  "/terms",
  "/events",
  "/wallet",
  "/promote-store",
  "/community",
];

export const K_CULTURE_SITEMAP_PATHS = [
  "/k-culture",
  "/k-culture/k-food",
  "/k-culture/k-beauty",
  "/k-culture/k-pop",
  "/k-culture/k-trend",
];

export const CATEGORY_SITEMAP_PATHS = [
  "/destinations",
  "/destinations/asia",
  "/destinations/europe",
  "/destinations/americas",
  "/local-food",
];

const REGION_CITIES = {
  asia: [
    "tokyo", "kyoto", "osaka", "seoul", "korea", "busan", "jeju", "bali", "bangkok",
    "singapore", "taipei", "danang", "da nang", "hong kong", "hanoi", "beijing",
    "shanghai", "jakarta", "chiang mai",
  ],
  europe: [
    "paris", "rome", "london", "barcelona", "amsterdam", "berlin", "prague", "vienna",
    "lisbon", "madrid", "florence", "milan", "athens", "dubrovnik", "istanbul",
  ],
  americas: [
    "new york", "los angeles", "chicago", "miami", "toronto", "vancouver", "mexico",
    "rio", "sao paulo", "buenos aires", "san francisco",
  ],
};

export function readEnglishCopy() {
  return JSON.parse(fs.readFileSync(ENGLISH_COPY, "utf8"));
}

export function listPublishedGuides(rootDir = REPO_ROOT) {
  const guidesDir = path.join(rootDir, "guides");
  const outputDir = path.join(rootDir, "output");
  const found = new Map();
  if (fs.existsSync(guidesDir)) {
    for (const name of fs.readdirSync(guidesDir)) {
      const filePath = path.join(guidesDir, name);
      if (GUIDE_NAME.test(name) && fs.statSync(filePath).isFile()) found.set(name, filePath);
    }
  }
  let approved = [];
  const approvals = path.join(outputDir, "approved_guides.json");
  if (fs.existsSync(approvals)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(approvals, "utf8"));
      if (Array.isArray(parsed)) approved = parsed.filter((item) => typeof item === "string");
    } catch {
      approved = [];
    }
  }
  const approvedSet = new Set(approved);
  if (fs.existsSync(outputDir)) {
    for (const name of fs.readdirSync(outputDir)) {
      const filePath = path.join(outputDir, name);
      if (!GUIDE_NAME.test(name) || !approvedSet.has(name) || found.has(name)) continue;
      if (fs.statSync(filePath).isFile()) found.set(name, filePath);
    }
  }
  return [...found.keys()].sort().map((name) => {
    const filePath = found.get(name);
    const markdown = fs.readFileSync(filePath, "utf8");
    return {
      name,
      filePath,
      markdown,
      slug: frontmatterValue(markdown, "slug") || name,
      lastmod: fs.statSync(filePath).mtime.toISOString().slice(0, 10),
    };
  });
}

function classifyRegion(label) {
  const name = String(label || "").toLowerCase();
  for (const [region, cities] of Object.entries(REGION_CITIES)) {
    if (cities.some((city) => name.includes(city))) return region;
  }
  return "";
}

export function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function stripFrontmatter(markdown) {
  return String(markdown || "").replace(/^---[\s\S]*?---\s*/, "");
}

function frontmatterValue(markdown, key) {
  const match = String(markdown || "").match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return "";
  const line = match[1].match(new RegExp(`^${key}:\\s*"?([^"\\n]+)"?\\s*$`, "m"));
  return line ? line[1].trim() : "";
}

function headingHtml(block, titleCore) {
  const match = /^(#{1,6})\s+(.+)$/.exec(block.split("\n")[0].trim());
  if (!match) return "";
  const text = match[2].trim();
  if (match[1].length === 1 && text.toLowerCase() === String(titleCore || "").trim().toLowerCase()) return "";
  const tag = match[1].length >= 3 ? "h3" : "h2";
  return `<${tag}>${escapeHtml(text)}</${tag}>`;
}

function firstImageUrl(markdown) {
  const match = String(markdown || "").match(/!\[[^\]]*\]\((https?:[^)\s]+)\)/);
  return match ? match[1] : frontmatterValue(markdown, "image_url");
}

export function renderGuideArticle(markdown, slug) {
  const body = stripFrontmatter(markdown);
  const heading = body.match(/^#\s+(.+)$/m);
  const titleCore = frontmatterValue(markdown, "title") || (heading ? heading[1].trim() : slug);
  const blocks = [];
  let description = "";
  for (const raw of body.split(/\n\s*\n/)) {
    const block = raw.trim();
    if (!block || block.startsWith("!") || /^\*?\s*photo by\b/i.test(block)) continue;
    if (block.startsWith("|")) {
      const rows = block
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line && !/^\|?\s*:?-{3,}/.test(line));
      if (!rows.length) continue;
      const text = rows
        .map((line) => line.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()).join(" · "))
        .join(". ");
      if (!description) description = text.slice(0, 180);
      blocks.push(`<p>${escapeHtml(text)}</p>`);
      continue;
    }
    if (block.startsWith("#")) {
      const html = headingHtml(block, titleCore);
      if (html) blocks.push(html);
      continue;
    }
    const text = block.replace(/\s+/g, " ");
    if (!description) description = text.slice(0, 180);
    blocks.push(`<p>${escapeHtml(text)}</p>`);
  }
  const title = titleCore.includes("BlueLog Trip") ? titleCore : `${titleCore} · BlueLog Trip`;
  const article = `<article><h1>${escapeHtml(titleCore)}</h1>${blocks.join("")}<p><a href="/">BlueLog Trip city guides</a></p></article>`;
  return {
    title,
    description: description || titleCore,
    body: article,
    path: `/guides/${slug}`,
    placeName: frontmatterValue(markdown, "city") || titleCore,
    image: firstImageUrl(markdown),
  };
}

function article(title, paragraphs) {
  const body = paragraphs.filter(Boolean).map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
  return `<article><h1>${escapeHtml(title)}</h1>${body}</article>`;
}

export function publisherPages(copy = readEnglishCopy(), guides = []) {
  const homeLinks = guides
    .map((guide) => {
      const markdown = guide.markdown || fs.readFileSync(guide.filePath, "utf8");
      const slug = guide.slug || guide.name;
      const rendered = renderGuideArticle(markdown, slug);
      const label = rendered.title.replace(/ · BlueLog Trip$/, "");
      return `<li><a href="/guides/${escapeHtml(slug)}">${escapeHtml(label)}</a></li>`;
    })
    .join("");
  const homeBody = `${article(copy.hero.title, [copy.hero.copy, copy.hero.about])}<section><h2>Published guides</h2><ul>${homeLinks}</ul></section>`;
  const pages = [
    {
      id: "home",
      path: "/",
      file: "index.html",
      title: copy.meta.homeTitle,
      description: copy.hero.about.slice(0, 180),
      body: homeBody,
    },
    {
      id: "events",
      path: "/events",
      file: "events.html",
      title: copy.meta.eventsTitle,
      description: copy.meta.eventsDescription,
      body: article(copy.events.title, [copy.events.lead, copy.events.purpose]),
    },
    {
      id: "wallet",
      path: "/wallet",
      file: "wallet.html",
      title: copy.meta.walletTitle,
      description: copy.meta.walletDescription,
      body: article(copy.wallet.title, [copy.wallet.purpose]),
    },
    {
      id: "promote",
      path: "/promote-store",
      file: "promote-store.html",
      title: copy.meta.promoteTitle,
      description: copy.meta.promoteDescription,
      body: article(copy.promote.pageTitle, [copy.promote.pageLead, copy.promote.purpose]),
    },
    {
      id: "community",
      path: "/community",
      file: "community.html",
      title: copy.meta.communityTitle,
      description: copy.meta.communityDescription,
      body: article(copy.community.title, [copy.community.lead, copy.community.purpose]),
    },
    legalPage(copy, "about", "/about", "about.html"),
    legalPage(copy, "privacy", "/privacy", "privacy.html"),
    legalPage(copy, "terms", "/terms", "terms.html"),
    legalPage(copy, "contact", "/contact", "contact.html"),
  ];
  return pages;
}

function plainCopy(template, values = {}) {
  return String(template || "")
    .replace(/<[^>]+>\{\{([^}]+)\}\}<\/[^>]+>/g, (_, key) => values[key] || "")
    .replace(/\{\{([^}]+)\}\}/g, (_, key) => values[key] || "");
}

function legalPage(copy, group, publicPath, file) {
  const section = copy[group] || {};
  const values = {
    email: "bluelog.official@gmail.com",
    adsUrl: "https://policies.google.com/technologies/ads",
    settingsUrl: "https://adssettings.google.com",
    choicesUrl: "https://www.aboutads.info/choices",
    eeaUrl: "https://www.youronlinechoices.eu",
  };
  const paragraphs = Object.entries(section)
    .filter(([key]) => !["kicker", "title"].includes(key))
    .map(([, value]) => plainCopy(value, values));
  const description = paragraphs.find((paragraph) => paragraph.length > 40) || section.title || "BlueLog Trip";
  return {
    id: group,
    path: publicPath,
    file,
    title: `${section.title || group} · BlueLog Trip`,
    description: description.slice(0, 180),
    body: article(section.title || group, paragraphs),
  };
}

function guideViews(guides) {
  return guides.map((guide) => {
    const markdown = guide.markdown || fs.readFileSync(guide.filePath, "utf8");
    const slug = guide.slug || frontmatterValue(markdown, "slug") || guide.name;
    const city = frontmatterValue(markdown, "city") || guide.name;
    const culture = readKCulture(guide.name, markdown);
    const rendered = renderGuideArticle(markdown, slug);
    return {
      slug,
      title: rendered.title.replace(/ · BlueLog Trip$/, ""),
      region: classifyRegion(`${city} ${guide.name}`),
      hasFood: /food|meal|restaurant|market|cuisine|eat|맛집/i.test(`${rendered.title}\n${markdown.slice(0, 4000)}`),
      themes: culture.kThemes,
      hot: culture.hotCountry,
    };
  });
}

function categoryArticle(title, intro, views) {
  const items = views
    .map((view) => `<li><a href="/guides/${escapeHtml(view.slug)}">${escapeHtml(view.title)}</a></li>`)
    .join("");
  return `<article><h1>${escapeHtml(title)}</h1><p>${escapeHtml(intro)}</p><h2>Published guides</h2><ul>${items}</ul></article>`;
}

export function categoryPages(guides = []) {
  const views = guideViews(guides);
  const byRegion = (region) => views.filter((view) => view.region === region);
  const byTheme = (theme) => views.filter((view) => view.hot && (theme === "all" || view.themes.includes(theme)));
  const pages = [
    ["destinations", "/destinations", "destinations.html", "City guides by region", "Walking routes and neighborhood meals, grouped by region.", views],
    ["asia", "/destinations/asia", "destinations/asia.html", "Asia city guides", "Published Asia routes with neighborhoods, meals, and transit.", byRegion("asia")],
    ["europe", "/destinations/europe", "destinations/europe.html", "Europe city guides", "Published Europe routes with neighborhoods, meals, and transit.", byRegion("europe")],
    ["americas", "/destinations/americas", "destinations/americas.html", "Americas city guides", "Published Americas routes with neighborhoods, meals, and transit.", byRegion("americas")],
    ["food", "/local-food", "local-food.html", "Local food guides", "Guides that name the market, the counter, and what the meal costs.", views.filter((view) => view.hasFood)],
    ["kculture", "/k-culture", "k-culture.html", "K-Culture guides", "Korea routes for food, beauty counters, music nights, and neighborhood trends.", byTheme("all")],
    ["k-food", "/k-culture/k-food", "k-culture/k-food.html", "K-Food guides", "Korean meals, markets, and soup counters with prices and timing.", byTheme("k-food")],
    ["k-beauty", "/k-culture/k-beauty", "k-culture/k-beauty.html", "K-Beauty guides", "Shop counters and skincare loops that fit a real Seoul or Busan day.", byTheme("k-beauty")],
    ["k-pop", "/k-culture/k-pop", "k-culture/k-pop.html", "K-Pop guides", "Show nights, company streets, and live rooms that you can actually enter.", byTheme("k-pop")],
    ["k-trend", "/k-culture/k-trend", "k-culture/k-trend.html", "K-Trend guides", "Warehouse streets, cafe lanes, and newer neighborhoods with a walkable plan.", byTheme("k-trend")],
  ];
  return pages.map(([id, publicPath, file, title, description, matched]) => ({
    id,
    path: publicPath,
    file,
    title: `${title} · BlueLog Trip`,
    description,
    body: categoryArticle(title, description, matched),
  }));
}

function replaceMeta(html, attribute, key, content) {
  const pattern = new RegExp(`<meta ${attribute}="${key}" content="[^"]*"\\s*/?>`, "i");
  const tag = `<meta ${attribute}="${key}" content="${escapeHtml(content)}" />`;
  if (pattern.test(html)) return html.replace(pattern, tag);
  return html.replace("</head>", `    ${tag}\n  </head>`);
}

export function replaceRoot(html, body) {
  const token = '<div id="root">';
  const start = html.indexOf(token);
  if (start < 0) return html;
  let index = start + token.length;
  let depth = 1;
  while (index < html.length && depth > 0) {
    const nextOpen = html.indexOf("<div", index);
    const nextClose = html.indexOf("</div>", index);
    if (nextClose < 0) return html;
    if (nextOpen !== -1 && nextOpen < nextClose) {
      depth += 1;
      index = nextOpen + 4;
      continue;
    }
    depth -= 1;
    if (depth === 0) {
      return `${html.slice(0, start)}<div id="root">${body}</div>${html.slice(nextClose + "</div>".length)}`;
    }
    index = nextClose + "</div>".length;
  }
  return html;
}

function jsonLdScript(page, canonical, origin) {
  const graph = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Article",
        headline: page.title,
        description: page.description,
        mainEntityOfPage: canonical,
        url: canonical,
        image: page.image || undefined,
        author: { "@type": "Organization", name: "BlueLog Editorial" },
        publisher: { "@type": "Organization", name: "BlueLog Trip", url: `${origin}/` },
      },
      {
        "@type": "TouristAttraction",
        name: page.placeName || page.title,
        description: page.description,
        url: canonical,
        image: page.image || undefined,
      },
    ],
  };
  const json = JSON.stringify(graph).replace(/</g, "\\u003c");
  return `<script type="application/ld+json">${json}</script>`;
}

export function applySeoDocument(shell, page, origin = SITE_ORIGIN) {
  const canonical = absoluteCanonical(origin, page.path);
  let html = shell;
  html = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtml(page.title)}</title>`);
  const canonicalTag = `<link rel="canonical" href="${escapeHtml(canonical)}" />`;
  if (/<link rel="canonical" href="[^"]*"\s*\/?>/i.test(html)) {
    html = html.replace(/<link rel="canonical" href="[^"]*"\s*\/?>/i, canonicalTag);
  } else {
    html = html.replace("</head>", `    ${canonicalTag}\n  </head>`);
  }
  html = replaceMeta(html, "name", "description", page.description);
  html = replaceMeta(html, "property", "og:title", page.title);
  html = replaceMeta(html, "property", "og:description", page.description);
  html = replaceMeta(html, "property", "og:url", canonical);
  html = replaceMeta(html, "property", "og:type", page.type || "website");
  html = replaceMeta(html, "name", "twitter:title", page.title);
  html = replaceMeta(html, "name", "twitter:description", page.description);
  if (page.image) html = replaceMeta(html, "property", "og:image", page.image);
  if (page.type === "article") {
    html = html.replace("</head>", `    ${jsonLdScript(page, canonical, publicOrigin(origin))}\n  </head>`);
  }
  return replaceRoot(html, page.body);
}

function sitemapUrl({ loc, lastmod, changefreq, priority }) {
  const lines = ["  <url>", `    <loc>${escapeHtml(loc)}</loc>`];
  if (lastmod) lines.push(`    <lastmod>${escapeHtml(lastmod)}</lastmod>`);
  lines.push(`    <changefreq>${escapeHtml(changefreq)}</changefreq>`);
  lines.push(`    <priority>${escapeHtml(priority)}</priority>`);
  lines.push("  </url>");
  return lines.join("\n");
}

export function guideCanonicalPath(guide) {
  const slug = String(guide?.slug || "").trim();
  const name = String(guide?.name || "").trim();
  const id = slug || name;
  return canonicalPath(`/guides/${id}`);
}

export function buildSitemapXml(siteUrl, guides, today = new Date().toISOString().slice(0, 10)) {
  const seen = new Set();
  const entries = [];
  const add = (publicPath, changefreq, priority, lastmod = today) => {
    const loc = absoluteCanonical(siteUrl || SITE_ORIGIN, publicPath);
    if (seen.has(loc)) return;
    seen.add(loc);
    entries.push(sitemapUrl({ loc, lastmod, changefreq, priority }));
  };
  add("/", "daily", "1.0");
  for (const publicPath of SERVICE_SITEMAP_PATHS) add(publicPath, "monthly", "0.4");
  for (const publicPath of K_CULTURE_SITEMAP_PATHS) {
    add(publicPath, "weekly", publicPath === "/k-culture" ? "0.9" : "0.7");
  }
  for (const publicPath of CATEGORY_SITEMAP_PATHS) add(publicPath, "weekly", "0.7");
  for (const guide of guides) {
    add(guideCanonicalPath(guide), "weekly", "0.8", guide.lastmod || today);
  }
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${entries.join("\n")}\n</urlset>\n`;
}

export function writePublisherSite(distDir, shell, options = {}) {
  const origin = options.origin || SITE_ORIGIN;
  const guides = options.guides || listPublishedGuides();
  const copy = options.copy || readEnglishCopy();
  fs.mkdirSync(distDir, { recursive: true });
  for (const page of [...publisherPages(copy, guides), ...categoryPages(guides)]) {
    const html = applySeoDocument(shell, page, origin);
    const target = path.join(distDir, page.file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, html);
  }
  const guideDir = path.join(distDir, "seo", "guide");
  fs.mkdirSync(guideDir, { recursive: true });
  for (const guide of guides) {
    const markdown = guide.markdown || fs.readFileSync(guide.filePath, "utf8");
    const targets = new Set([guide.name]);
    if (guide.slug && guide.slug !== guide.name) targets.add(guide.slug);
    const canonicalId = guide.slug || guide.name;
    for (const publicId of targets) {
      const page = renderGuideArticle(markdown, publicId);
      page.path = `/guides/${canonicalId}`;
      page.type = "article";
      const html = applySeoDocument(shell, page, origin);
      fs.writeFileSync(path.join(guideDir, publicId), html);
    }
  }
  fs.writeFileSync(path.join(distDir, "sitemap.xml"), buildSitemapXml(origin, guides));
}
