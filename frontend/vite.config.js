import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { adsTxtBody, normalizePublisherId } from "./src/lib/adsTxt.js";
import { buildSitemapXml, listPublishedGuides, SITE_ORIGIN, writePublisherSite } from "./src/lib/staticSeo.js";

const FRONTEND_DIR = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_SITE_URL = SITE_ORIGIN;

function stripScripts(xml) {
  return String(xml || "")
    .replace(/<script\b[^>]*\/>/gi, "")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");
}

function requestOrigin(req) {
  const host = String(req.headers.host || "");
  if (!host || host.endsWith(":8000")) return "";
  const proto = String(req.headers["x-forwarded-proto"] || "http")
    .split(",")[0]
    .trim();
  return `${proto}://${host}`;
}

function buildStaticSitemap(siteUrl) {
  const origin = String(siteUrl || DEFAULT_SITE_URL).replace(/\/$/, "") || DEFAULT_SITE_URL;
  return stripScripts(buildSitemapXml(origin, listPublishedGuides()));
}

function publisherHtmlPlugin(env) {
  const siteUrl = env.VITE_SITE_URL || DEFAULT_SITE_URL;
  return {
    name: "publisher-html",
    apply: "build",
    closeBundle() {
      const dist = path.resolve(FRONTEND_DIR, "dist");
      const indexPath = path.join(dist, "index.html");
      if (!fs.existsSync(indexPath)) return;
      const shell = fs.readFileSync(indexPath, "utf8");
      writePublisherSite(dist, shell, { origin: siteUrl });
    },
  };
}

function adsTxtPlugin(env) {
  const publisher = normalizePublisherId(env.VITE_ADSENSE_PUBLISHER_ID || env.ADSENSE_PUBLISHER_ID || env.VITE_ADSENSE_CLIENT_ID || "");
  const body = publisher ? adsTxtBody(publisher) : "";
  const serve = (req, res, next) => {
    const requestPath = (req.url || "").split("?")[0];
    if (!body || (requestPath !== "/ads.txt" && requestPath !== "/api/ads.txt")) {
      next();
      return;
    }
    res.statusCode = 200;
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.end(body);
  };
  return {
    name: "bluelog-ads-txt",
    configureServer(server) {
      server.middlewares.use(serve);
    },
    configurePreviewServer(server) {
      server.middlewares.use(serve);
    },
    writeBundle(options) {
      if (!body) return;
      const dir = options.dir || path.resolve(FRONTEND_DIR, "dist");
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, "ads.txt"), body);
    },
  };
}

function pureSitemapPlugin(env) {
  const apiOrigin = env.SITEMAP_API_ORIGIN || "http://127.0.0.1:8000";
  const siteUrl = env.VITE_SITE_URL || DEFAULT_SITE_URL;
  return {
    name: "pure-sitemap-xml",
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "sitemap.xml",
        source: buildStaticSitemap(siteUrl),
      });
    },
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const requestPath = (req.url || "").split("?")[0].replace(/\/+$/, "") || "/";
        if (requestPath !== "/sitemap.xml" && requestPath !== "/api/v1/sitemap.xml") {
          next();
          return;
        }
        const configured = String(env.VITE_SITE_URL || "").replace(/\/$/, "");
        const siteUrl = configured || requestOrigin(req);
        try {
          const upstream = await fetch(`${apiOrigin}/api/v1/sitemap.xml`, {
            headers: siteUrl ? { "X-Site-Url": siteUrl } : {},
          });
          const xml = stripScripts(await upstream.text());
          res.statusCode = upstream.ok ? 200 : 502;
          res.setHeader("Content-Type", "application/xml; charset=utf-8");
          res.setHeader("X-Content-Type-Options", "nosniff");
          res.setHeader("Cache-Control", "no-cache");
          res.end(xml);
        } catch {
          res.statusCode = 502;
          res.setHeader("Content-Type", "application/xml; charset=utf-8");
          res.setHeader("X-Content-Type-Options", "nosniff");
          res.end(buildStaticSitemap(siteUrl || DEFAULT_SITE_URL));
        }
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [adsTxtPlugin(env), pureSitemapPlugin(env), publisherHtmlPlugin(env), react()],
    test: {
      environment: "jsdom",
      globals: false,
    },
  };
});
