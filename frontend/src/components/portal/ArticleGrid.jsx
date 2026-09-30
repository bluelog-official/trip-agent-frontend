import { useEffect, useState } from "react";
import { BadgeCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { fetchVoteStatuses } from "../../lib/votes";
import VoteButton from "./VoteButton";

function CardThumb({ src, title }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return <div className="thumb-fallback" aria-hidden="true">{title.slice(0, 1)}</div>;
  }
  return <img src={src} alt="" onError={() => setFailed(true)} />;
}

function StoryCard({ card, vote, onOpen }) {
  const { t } = useTranslation();
  return (
    <article className="story-card">
      <button type="button" className="story-open" onClick={() => onOpen(card)}>
        <div className="thumb-wrap">
          <CardThumb src={card.image} title={card.title} />
          {card.approved ? (
            <span className="qa-badge approved">
              <BadgeCheck size={14} aria-hidden="true" />
              {t("catalog.verified")}
            </span>
          ) : (
            <span className="qa-badge pending">{t("catalog.checked")}</span>
          )}
        </div>
        <div className="story-body">
          <h2>{card.title}</h2>
          <p>{card.summary}</p>
          <ul className="tag-row">
            {card.tags.map((tag) => (
              <li key={tag}>{tag}</li>
            ))}
          </ul>
        </div>
      </button>
      <div className="story-vote">
        <VoteButton
          articleId={card.id}
          count={vote?.vote_count || 0}
          voted={Boolean(vote?.voted)}
          managed
        />
      </div>
    </article>
  );
}

export default function ArticleGrid({ cards, loading, error, onOpen, loadVotes = true }) {
  const { t } = useTranslation();
  const [votes, setVotes] = useState({});
  const voteKey = cards.map((card) => card.id).filter(Boolean).join("|");

  useEffect(() => {
    if (!loadVotes || !voteKey) return undefined;
    let cancelled = false;
    fetchVoteStatuses(voteKey.split("|"))
      .then((rows) => {
        if (cancelled) return;
        const next = {};
        rows.forEach((row) => {
          next[row.article_id] = row;
        });
        setVotes(next);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [loadVotes, voteKey]);

  if (loading) {
    return (
      <div className="card-grid" aria-busy="true" aria-label={t("catalog.loading")}>
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="story-skeleton" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="grid-empty">{error}</p>;
  }

  if (cards.length === 0) {
    return <p className="grid-empty">{t("catalog.empty")}</p>;
  }

  return (
    <div className="card-grid">
      {cards.map((card) => (
        <StoryCard key={card.id} card={card} vote={votes[card.id]} onOpen={onOpen} />
      ))}
    </div>
  );
}
