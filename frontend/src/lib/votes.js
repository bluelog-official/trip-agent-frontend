import { API_BASE_URL } from "./guideCards";

function votesEndpoint() {
  return `${API_BASE_URL.replace(/\/api\/v1$/, "")}/api/votes`;
}

export async function fetchVoteStatuses(articleIds) {
  const ids = [...new Set((articleIds || []).map((id) => String(id || "").trim()).filter(Boolean))];
  if (!ids.length || typeof fetch !== "function") return [];
  const res = await fetch(`${votesEndpoint()}?article_ids=${encodeURIComponent(ids.join(","))}`);
  if (!res.ok) throw new Error("votes failed");
  const data = await res.json();
  return Array.isArray(data?.votes) ? data.votes : [];
}

export async function castVote(articleId) {
  const res = await fetch(votesEndpoint(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ article_id: articleId }),
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 409) {
    return {
      article_id: articleId,
      vote_count: Number(data.vote_count) || 0,
      voted: true,
      created: false,
    };
  }
  if (!res.ok) throw new Error("vote failed");
  return {
    article_id: String(data.article_id || articleId),
    vote_count: Number(data.vote_count) || 0,
    voted: data.voted !== false,
    created: data.created !== false,
  };
}
