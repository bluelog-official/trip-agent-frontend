import DOMPurify from "dompurify";

const SCHEME = /(?:javascript|vbscript)\s*:/gi;
const MARKDOWN_BAD_URL = /(\]\()\s*(?:javascript|vbscript|data)\s*:[^)]*/gi;
const EVENT_ATTR = /\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi;

function purifier() {
  if (typeof DOMPurify.sanitize === "function") return DOMPurify;
  if (typeof window !== "undefined" && typeof DOMPurify === "function") {
    return DOMPurify(window);
  }
  return null;
}

export function allowedUrl(value) {
  const raw = String(value || "").replace(/[\u0000-\u001F\u007F]/g, "").trim();
  if (!raw) return "";
  const compact = raw.replace(/\s+/g, "").toLowerCase();
  if (
    compact.startsWith("javascript:")
    || compact.startsWith("vbscript:")
    || compact.startsWith("data:")
  ) {
    return "";
  }
  return raw;
}

export function sanitizeMarkdown(source) {
  const input = String(source ?? "");
  const engine = purifier();
  const purified = engine
    ? engine.sanitize(input, {
      FORBID_TAGS: ["script", "iframe", "object", "embed", "form", "style", "link", "meta", "base"],
      FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "onfocus", "onmouseenter", "style"],
      ALLOW_DATA_ATTR: false,
    })
    : input;
  return String(purified)
    .replace(EVENT_ATTR, "")
    .replace(MARKDOWN_BAD_URL, "$1")
    .replace(SCHEME, "");
}
