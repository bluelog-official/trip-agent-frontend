import { canonicalHref, SITE_ORIGIN } from "./canonicalPath.js";

export { canonicalHref, SITE_ORIGIN };

function absoluteImage(image) {
  const value = String(image || "").trim();
  if (!value) return "";
  if (value.startsWith("https://") || value.startsWith("http://")) return value;
  if (value.startsWith("/")) return `${SITE_ORIGIN}${value}`;
  return value;
}

function upsertMeta(attribute, key, content) {
  if (typeof document === "undefined") return;
  const value = String(content || "").trim();
  let meta = document.head.querySelector(`meta[${attribute}="${key}"]`);
  if (!value) {
    meta?.remove();
    return;
  }
  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute(attribute, key);
    document.head.appendChild(meta);
  }
  meta.setAttribute("content", value);
}

export function applyPageHead({
  title,
  description,
  pathname,
  type = "website",
  locale = "en_US",
  image = "",
}) {
  if (typeof document === "undefined") return;
  const url = canonicalHref(pathname);
  const shareImage = absoluteImage(image);
  let link = document.head.querySelector('link[rel="canonical"]');
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", "canonical");
    document.head.appendChild(link);
  }
  link.setAttribute("href", url);

  upsertMeta("property", "og:title", title);
  upsertMeta("property", "og:description", description);
  upsertMeta("property", "og:url", url);
  upsertMeta("property", "og:type", type === "article" ? "article" : "website");
  upsertMeta("property", "og:site_name", "BlueLog Trip");
  upsertMeta("property", "og:locale", locale === "ko_KR" ? "ko_KR" : "en_US");
  upsertMeta("property", "og:image", shareImage);
  upsertMeta("name", "twitter:card", shareImage ? "summary_large_image" : "summary");
  upsertMeta("name", "twitter:title", title);
  upsertMeta("name", "twitter:description", description);
  upsertMeta("name", "twitter:image", shareImage);
}
