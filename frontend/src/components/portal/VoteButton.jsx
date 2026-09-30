import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { castVote, fetchVoteStatuses } from "../../lib/votes";

export default function VoteButton({
  articleId,
  count = 0,
  voted = false,
  managed = false,
  onChange,
}) {
  const { t } = useTranslation();
  const [total, setTotal] = useState(Number(count) || 0);
  const [done, setDone] = useState(Boolean(voted));
  const [pending, setPending] = useState(false);
  const [toast, setToast] = useState("");
  const doneRef = useRef(Boolean(voted));
  const totalRef = useRef(Number(count) || 0);

  useEffect(() => {
    const nextTotal = Number(count) || 0;
    const nextDone = Boolean(voted);
    setTotal(nextTotal);
    setDone(nextDone);
    totalRef.current = nextTotal;
    doneRef.current = nextDone;
  }, [articleId, count, voted]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (managed || !articleId) return undefined;
    let cancelled = false;
    fetchVoteStatuses([articleId])
      .then((rows) => {
        if (cancelled) return;
        const row = rows[0];
        if (!row) return;
        const nextTotal = Number(row.vote_count) || 0;
        const nextDone = Boolean(row.voted);
        setTotal(nextTotal);
        setDone(nextDone);
        totalRef.current = nextTotal;
        doneRef.current = nextDone;
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [articleId, managed]);

  const publish = (next) => {
    totalRef.current = next.vote_count;
    doneRef.current = next.voted;
    setTotal(next.vote_count);
    setDone(next.voted);
    onChange?.(next);
  };

  const vote = async () => {
    if (!articleId || pending) return;
    if (doneRef.current) {
      setToast(t("vote.duplicate"));
      return;
    }
    const previous = totalRef.current;
    publish({ article_id: articleId, vote_count: previous + 1, voted: true, created: true });
    setPending(true);
    try {
      const result = await castVote(articleId);
      if (!result.created) {
        publish({
          article_id: articleId,
          vote_count: managed ? previous : result.vote_count || previous,
          voted: true,
          created: false,
        });
        setToast(t("vote.duplicate"));
        return;
      }
      publish({
        article_id: articleId,
        vote_count: managed ? previous + 1 : result.vote_count || previous + 1,
        voted: true,
        created: true,
      });
    } catch {
      publish({ article_id: articleId, vote_count: previous, voted: false, created: false });
      setToast(t("vote.failed"));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className={`vote-control${done ? " is-voted" : ""}`}>
      <button
        type="button"
        className="vote-button"
        aria-pressed={done}
        disabled={!articleId || pending}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          vote();
        }}
      >
        {done ? t("vote.voted") : t("vote.action")}
      </button>
      <span className="vote-count">{t("vote.count", { count: total })}</span>
      {toast ? (
        <p className="vote-toast" role="status">
          {toast}
        </p>
      ) : null}
    </div>
  );
}
