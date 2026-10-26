import { GUIDE_FILE_TO_SLUG } from "./guideAliases.js";

export const SITE_ORIGIN = "https://www.bluelogtrip.com";

const PAGE_ALIASES = {
  "/guide": "/",
  "/guides": "/",
  "/mypage": "/wallet",
  "/partner-apply": "/promote-store",
};

export function publicOrigin(origin) {
  const base = String(origin || SITE_ORIGIN).trim().replace(/\/+$/, "") || SITE_ORIGIN;
  try {
    const url = new URL(base.includes("://") ? base : `https://${base}`);
    const host = url.hostname.toLowerCase();
    if (host === "bluelogtrip.com" || host === "www.bluelogtrip.com") return SITE_ORIGIN;
  } catch {
    return base;
  }
  return base;
}

export function canonicalPath(pathname) {
  let raw = String(pathname || "/").split("?")[0].split("#")[0] || "/";
  if (!raw.startsWith("/")) raw = `/${raw}`;
  let path = raw.length > 1 ? raw.replace(/\/+$/, "") || "/" : "/";
  if (PAGE_ALIASES[path]) return PAGE_ALIASES[path];
  const match = /^\/guides?\/([^/]+)$/.exec(path);
  if (!match) return path;
  let id = match[1];
  try {
    id = decodeURIComponent(id);
  } catch {
    // keep the original segment when percent-encoding is invalid
  }
  return `/guides/${GUIDE_FILE_TO_SLUG[id] || id}`;
}

export function absoluteCanonical(origin, pathname) {
  const path = canonicalPath(pathname);
  const base = publicOrigin(origin);
  return path === "/" ? `${base}/` : `${base}${path}`;
}

export function canonicalHref(pathname) {
  return absoluteCanonical(SITE_ORIGIN, pathname);
}

/** index.html에서 모듈 로드 전에 표준 태그를 맞춘다. canonicalPath와 같은 규칙이다. */
export function canonicalBootScript() {
  return `(function () {
  var aliases = ${JSON.stringify(GUIDE_FILE_TO_SLUG)};
  var pageAliases = ${JSON.stringify(PAGE_ALIASES)};
  var origin = ${JSON.stringify(SITE_ORIGIN)};
  var raw = location.pathname || "/";
  if (raw.charAt(0) !== "/") raw = "/" + raw;
  var path = raw.length > 1 ? raw.replace(/\\/+$/, "") || "/" : "/";
  if (pageAliases[path]) path = pageAliases[path];
  else {
    var match = /^\\/guides?\\/([^/]+)$/.exec(path);
    if (match) {
      var id = match[1];
      try { id = decodeURIComponent(id); } catch (err) {}
      path = "/guides/" + (aliases[id] || id);
    }
  }
  var href = path === "/" ? origin + "/" : origin + path;
  var link = document.querySelector('link[rel="canonical"]');
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", "canonical");
    document.head.appendChild(link);
  }
  link.setAttribute("href", href);
  var og = document.querySelector('meta[property="og:url"]');
  if (og) og.setAttribute("content", href);
})();`;
}
