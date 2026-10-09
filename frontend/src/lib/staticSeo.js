import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const LIB_DIR = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(LIB_DIR, "../../..");
export const SITE_ORIGIN = "https://www.bluelogtrip.com";
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
    return {
      name,
      filePath,
      lastmod: fs.statSync(filePath).mtime.toISOString().slice(0, 10),
    };
  });
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
      const text = block.replace(/^#+\s*/, "").split("\n")[0].trim();
      blocks.push(`<h2>${escapeHtml(text)}</h2>`);
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
  };
}

function article(title, paragraphs) {
  const body = paragraphs.filter(Boolean).map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
  return `<article><h1>${escapeHtml(title)}</h1>${body}</article>`;
}

export function publisherPages(copy = readEnglishCopy(), guides = []) {
  const homeLinks = guides
    .map((guide) => {
      const markdown = fs.readFileSync(guide.filePath, "utf8");
      const rendered = renderGuideArticle(markdown, guide.name);
      const label = rendered.title.replace(/ · BlueLog Trip$/, "");
      return `<li><a href="/guides/${escapeHtml(guide.name)}">${escapeHtml(label)}</a></li>`;
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
  ];
  return pages;
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

export function applySeoDocument(shell, page, origin = SITE_ORIGIN) {
  const canonical = page.path === "/" ? `${origin}/` : `${origin}${page.path}`;
  let html = shell;
  html = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtml(page.title)}</title>`);
  html = html.replace(
    /<link rel="canonical" href="[^"]*"\s*\/?>/i,
    `<link rel="canonical" href="${escapeHtml(canonical)}" />`,
  );
  html = replaceMeta(html, "name", "description", page.description);
  html = replaceMeta(html, "property", "og:title", page.title);
  html = replaceMeta(html, "property", "og:description", page.description);
  html = replaceMeta(html, "property", "og:url", canonical);
  html = replaceMeta(html, "property", "og:type", page.type || "website");
  html = replaceMeta(html, "name", "twitter:title", page.title);
  html = replaceMeta(html, "name", "twitter:description", page.description);
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

export function buildSitemapXml(siteUrl, guides, today = new Date().toISOString().slice(0, 10)) {
  const origin = String(siteUrl || SITE_ORIGIN).replace(/\/$/, "") || SITE_ORIGIN;
  const entries = [sitemapUrl({ loc: `${origin}/`, lastmod: today, changefreq: "daily", priority: "1.0" })];
  for (const publicPath of SERVICE_SITEMAP_PATHS) {
    entries.push(sitemapUrl({ loc: `${origin}${publicPath}`, lastmod: today, changefreq: "monthly", priority: "0.4" }));
  }
  for (const publicPath of K_CULTURE_SITEMAP_PATHS) {
    entries.push(
      sitemapUrl({
        loc: `${origin}${publicPath}`,
        lastmod: today,
        changefreq: "weekly",
        priority: publicPath === "/k-culture" ? "0.9" : "0.7",
      }),
    );
  }
  for (const guide of guides) {
    entries.push(
      sitemapUrl({
        loc: `${origin}/guide/${guide.name}`,
        lastmod: guide.lastmod || today,
        changefreq: "weekly",
        priority: "0.8",
      }),
    );
    entries.push(
      sitemapUrl({
        loc: `${origin}/guides/${guide.name}`,
        lastmod: guide.lastmod || today,
        changefreq: "weekly",
        priority: "0.8",
      }),
    );
  }
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${entries.join("\n")}\n</urlset>\n`;
}

export function writePublisherSite(distDir, shell, options = {}) {
  const origin = options.origin || SITE_ORIGIN;
  const guides = options.guides || listPublishedGuides();
  const copy = options.copy || readEnglishCopy();
  fs.mkdirSync(distDir, { recursive: true });
  for (const page of publisherPages(copy, guides)) {
    const html = applySeoDocument(shell, page, origin);
    const target = path.join(distDir, page.file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, html);
  }
  const guideDir = path.join(distDir, "seo", "guide");
  fs.mkdirSync(guideDir, { recursive: true });
  for (const guide of guides) {
    const markdown = fs.readFileSync(guide.filePath, "utf8");
    const page = renderGuideArticle(markdown, guide.name);
    page.type = "article";
    const html = applySeoDocument(shell, page, origin);
    fs.writeFileSync(path.join(guideDir, guide.name), html);
  }
  fs.writeFileSync(path.join(distDir, "sitemap.xml"), buildSitemapXml(origin, guides));
}
