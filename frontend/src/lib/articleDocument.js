const IMAGE_LINE = /!\[[^\]]*\]\((https?:[^)\s]+)\)/;
const PHOTO_LINE = /^\*Photo by (?:\[([^\]]+)\]\(([^)]+)\)|([^*\n]+))\*$/;
const PHOTO_CREDIT_LINE = /^\s*(?:[*_]{1,2})?\s*photo by\b.*$/i;
const HEADING_LINE = /^(#{2,3})\s+(.+)$/;
const MISSING_GUIDE = /데이터를 찾을 수 없습니다/;
const HANGUL = /[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3]/;

const TABLE_HEADER_CELLS = [
  [/^카테고리$/u, "Category"],
  [/^추천\s*장소$/u, "Recommended Location"],
  [/^예상\s*비용$/u, "Estimated Cost"],
  [/^별점(?:\s*\([^)]*\))?$/u, "Rating"],
];

const ENGLISH_HEADINGS = [
  [/1주|일주일|7일/u, "A One-Week Itinerary"],
  [/주말|2박/u, "A Weekend Itinerary"],
  [/5일|4박/u, "A 5-Day Itinerary"],
  [/3박\s*4일/u, "A 4-Day Itinerary"],
  [/3일/u, "A 3-Day Itinerary"],
  [/4일/u, "A 4-Day Itinerary"],
  [/일정/u, "Itinerary"],
  [/추천\s*맛집|맛집/u, "Recommended Restaurants"],
  [/지하철|교통|패스|에키나카/u, "Getting Around"],
  [/로컬\s*팁/u, "Local Tip"],
  [/관광|명소|여행지/u, "Places to Visit"],
  [/가성비/u, "A Practical City Route"],
];

export function slugifyHeading(text) {
  const slug = String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug || "section";
}

export function extractHeadings(markdown, seen = new Map()) {
  const headings = [];
  String(markdown || "")
    .split(/\r?\n/)
    .forEach((line, lineIndex) => {
      const match = HEADING_LINE.exec(line.trim());
      if (!match) return;
      const text = match[2].replace(/[*_`]/g, "").trim();
      const base = slugifyHeading(text);
      const count = seen.get(base) || 0;
      seen.set(base, count + 1);
      headings.push({
        level: match[1].length,
        text,
        id: count === 0 ? base : `${base}-${count}`,
        line: lineIndex + 1,
        lineIndex,
      });
    });
  return headings;
}

export function extractSources(markdown) {
  const sources = [];
  const seen = new Set();
  const add = (label, href = "") => {
    const name = String(label || "").replace(/\s+/g, " ").trim();
    const key = `${name}|${href}`;
    if (!name || seen.has(key)) return;
    seen.add(key);
    sources.push({ label: name, href });
  };

  String(markdown || "")
    .split(/\r?\n/)
    .forEach((line) => {
      const match = PHOTO_LINE.exec(line.trim());
      if (!match) return;
      add(match[1] || match[3], match[2] || "");
    });

  if (/images\.pexels\.com|pexels\.com/i.test(String(markdown || ""))) {
    add("Pexels", "https://www.pexels.com");
  }
  return sources;
}

export function stripPhotoCredits(markdown) {
  return String(markdown || "")
    .split(/\r?\n/)
    .filter((line) => !PHOTO_CREDIT_LINE.test(line.trim()))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n");
}

export function stripFrontmatter(markdown) {
  const text = String(markdown || "").replace(/^\uFEFF/, "");
  const match = /^---\r?\n[\s\S]*?\r?\n---\r?\n?/.exec(text);
  return match ? text.slice(match[0].length).replace(/^\s+/, "") : text;
}

export function stripLeadingImage(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  let image = "";
  let removed = false;
  const kept = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!removed) {
      const match = IMAGE_LINE.exec(line);
      if (match) {
        image = match[1];
        removed = true;
        const next = lines[index + 1]?.trim() || "";
        if (PHOTO_LINE.test(next)) index += 1;
        continue;
      }
    }
    kept.push(line);
  }
  return { markdown: kept.join("\n").trim(), image };
}

export function splitMarkdown(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const h2Lines = lines
    .map((line, index) => (/^##\s+/.test(line.trim()) && !/^###/.test(line.trim()) ? index : -1))
    .filter((index) => index >= 0);
  let cut = Math.ceil(lines.length / 2);
  if (h2Lines.length >= 2) {
    cut = h2Lines[Math.floor(h2Lines.length / 2)];
  }
  if (cut <= 0 || cut >= lines.length) {
    return { before: lines.join("\n").trim(), after: "", cut: lines.length };
  }
  return {
    before: lines.slice(0, cut).join("\n").trim(),
    after: lines.slice(cut).join("\n").trim(),
    cut,
  };
}

function isTableSeparator(line) {
  const cells = String(line || "")
    .trim()
    .split("|")
    .map((cell) => cell.trim())
    .filter(Boolean);
  return cells.length > 0 && cells.every((cell) => /^:?-+:?$/.test(cell));
}

function localizeTableHeader(line) {
  return line
    .split("|")
    .map((part) => {
      const trimmed = part.trim();
      if (!trimmed) return part;
      for (const [pattern, label] of TABLE_HEADER_CELLS) {
        if (pattern.test(trimmed)) {
          return part.replace(trimmed, label);
        }
      }
      return part;
    })
    .join("|");
}

function localizeHeading(line) {
  const match = /^(#{1,6})(\s+)(.+)$/.exec(line);
  if (!match || !HANGUL.test(match[3])) return line;
  for (const [pattern, label] of ENGLISH_HEADINGS) {
    if (pattern.test(match[3])) return `${match[1]}${match[2]}${label}`;
  }
  return `${match[1]}${match[2]}Trip Notes`;
}

export function localizeEnglishMarkdown(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  return lines
    .map((line, index) => {
      const heading = localizeHeading(line);
      if (heading !== line) return heading;
      if (line.includes("|") && isTableSeparator(lines[index + 1])) {
        return localizeTableHeader(line);
      }
      return line;
    })
    .join("\n");
}

export function prepareArticle(markdown, languageEnglish, destination) {
  const source = stripFrontmatter(markdown);
  const readable = languageEnglish && MISSING_GUIDE.test(source)
    ? `## ${destination || "Destination"} Trip Guide\n\nThis guide is not available yet.`
    : source;
  const localized = languageEnglish ? localizeEnglishMarkdown(readable) : readable;
  const withoutCredits = stripPhotoCredits(localized);
  const stripped = stripLeadingImage(withoutCredits);
  const split = splitMarkdown(stripped.markdown);
  const seen = new Map();
  const beforeHeadings = extractHeadings(split.before, seen);
  const afterHeadings = extractHeadings(split.after, seen);
  return {
    image: stripped.image,
    before: split.before,
    after: split.after,
    beforeHeadings,
    afterHeadings,
    headings: [...beforeHeadings, ...afterHeadings],
    sources: extractSources(localized),
  };
}

export function buildGuideJsonLd({
  title,
  description,
  image,
  publishedAt,
  url,
  destination,
  region,
  inLanguage,
}) {
  const article = {
    "@type": "Article",
    headline: title,
    description,
    inLanguage,
    author: {
      "@type": "Organization",
      name: "BlueLog Editorial",
    },
    publisher: {
      "@type": "Organization",
      name: "BlueLog Trip",
    },
    mainEntityOfPage: url,
  };
  if (publishedAt) {
    article.datePublished = publishedAt;
    article.dateModified = publishedAt;
  }
  if (image) article.image = [image];

  const attraction = {
    "@type": "TouristAttraction",
    name: destination || title,
    description,
  };
  if (image) attraction.image = image;
  if (region) {
    attraction.containedInPlace = {
      "@type": "Place",
      name: region,
    };
  }

  return {
    "@context": "https://schema.org",
    "@graph": [article, attraction],
  };
}

export function setMetaDescription(content) {
  const text = String(content || "").trim();
  if (!text || typeof document === "undefined") return;
  let meta = document.querySelector('meta[name="description"]');
  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute("name", "description");
    document.head.appendChild(meta);
  }
  meta.setAttribute("content", text);
}
