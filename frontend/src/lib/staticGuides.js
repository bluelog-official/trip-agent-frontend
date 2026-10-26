const GUIDE_FILES = import.meta.glob("../../../guides/*_guide.md", {
  query: "?raw",
  import: "default",
  eager: true,
});

function frontmatterValue(markdown, key) {
  const block = /^---\r?\n([\s\S]*?)\r?\n---/.exec(String(markdown || ""));
  if (!block) return "";
  const match = new RegExp(`^${key}:\\s*"?([^"\\n]+)"?`, "m").exec(block[1]);
  return match ? match[1].trim() : "";
}

export function listStaticGuideRecords() {
  return Object.entries(GUIDE_FILES)
    .map(([filePath, markdown]) => {
      const id = String(filePath).split("/").pop();
      const source = String(markdown || "");
      return {
        id,
        slug: frontmatterValue(source, "slug"),
        markdown: source,
      };
    })
    .filter((record) => record.id)
    .sort((a, b) => a.id.localeCompare(b.id));
}

export function findStaticGuide(guideId) {
  const key = decodeURIComponent(String(guideId || "")).trim();
  if (!key) return null;
  const bare = key.replace(/\.md$/i, "");
  return (
    listStaticGuideRecords().find(
      (record) => record.id === key || record.slug === key || record.id.replace(/\.md$/i, "") === bare,
    ) || null
  );
}

export function staticGuidePayload(guideId) {
  const found = findStaticGuide(guideId);
  if (!found) return null;
  return {
    id: found.id,
    content: found.markdown,
    article_markdown: found.markdown,
    is_approved: true,
    qa_result: { is_approved: true, quality_score: 80, violations: [] },
  };
}
