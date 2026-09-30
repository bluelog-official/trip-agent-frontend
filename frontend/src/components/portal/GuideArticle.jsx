import { useEffect, useMemo, useState } from "react";
import { BadgeCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import ArticleView from "../ArticleView";
import ShareSheet from "./ShareSheet";
import VoteButton from "./VoteButton";
import AdSenseUnit from "../AdSenseUnit";
import { prepareArticle, buildGuideJsonLd } from "../../lib/articleDocument";
import { toGuideCard } from "../../lib/guideCards";
import { appLanguage } from "../../i18n/i18n";
import {
  containsHangul,
  englishField,
  formatPublishedDate,
  isEnglishLanguage,
  presentGuideCard,
} from "../../lib/localeCopy";

function CrumbLink({ crumb, onNavigate }) {
  if (!crumb.path) {
    return <span aria-current="page">{crumb.label}</span>;
  }
  return (
    <a
      href={crumb.path}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(crumb.path);
      }}
    >
      {crumb.label}
    </a>
  );
}

function GuideHero({ src, alt }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return null;
  return (
    <img
      className="guide-hero"
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
    />
  );
}

export default function GuideArticle({ guide, fileName, onNavigate }) {
  const { t } = useTranslation();
  const language = appLanguage();
  const english = isEnglishLanguage(language);
  const card = presentGuideCard(toGuideCard(fileName || guide?.id || "", guide), language);
  const markdown = guide?.content || guide?.article_markdown || "";
  const article = useMemo(
    () => prepareArticle(markdown, english, card.destination),
    [markdown, english, card.destination],
  );
  const publishedAt = guide?.published_at || "";
  const publishedLabel = formatPublishedDate(publishedAt, language);
  const regionLabel = card.region ? t(`nav.${card.region}`) : "";
  const crumbs = [
    { label: t("nav.home"), path: "/" },
    ...(regionLabel ? [{ label: regionLabel, path: `/destinations/${card.region}` }] : []),
    { label: card.destination || card.title, path: "" },
  ];
  const toc = [...article.beforeHeadings, ...article.afterHeadings].filter((item) => {
    if (!english) return true;
    return !containsHangul(item.text);
  });
  const sources = article.sources
    .map((item) => ({
      ...item,
      label: english ? englishField(item.label, "") : item.label,
    }))
    .filter((item) => item.label);
  if (!sources.some((item) => item.label === t("guide.author"))) {
    sources.push({ label: t("guide.author"), href: "" });
  }

  const jsonLd = useMemo(
    () =>
      buildGuideJsonLd({
        title: card.title,
        description: card.summary,
        image: card.image || article.image,
        publishedAt,
        url: typeof window === "undefined"
          ? `/guide/${encodeURIComponent(card.id || "")}`
          : `${window.location.origin}/guide/${encodeURIComponent(card.id || "")}`,
        destination: card.destination,
        region: regionLabel,
        inLanguage: english ? "en" : "ko",
      }),
    [card.title, card.summary, card.image, card.id, card.destination, article.image, publishedAt, regionLabel, english],
  );

  useEffect(() => {
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.id = "bluelog-guide-jsonld";
    script.textContent = JSON.stringify(jsonLd);
    document.getElementById("bluelog-guide-jsonld")?.remove();
    document.head.appendChild(script);
    return () => {
      script.remove();
    };
  }, [jsonLd]);

  const jumpTo = (id) => (event) => {
    event.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <article className="guide-article" data-page="guide-detail">
      <nav className="breadcrumb" aria-label={t("guide.breadcrumb")}>
        {crumbs.map((crumb, index) => (
          <span key={`${crumb.label}-${index}`} className="crumb">
            {index > 0 ? <span className="crumb-sep" aria-hidden="true">&gt;</span> : null}
            <CrumbLink crumb={crumb} onNavigate={onNavigate} />
          </span>
        ))}
      </nav>

      <header className="guide-header">
        <h1>{card.title}</h1>
        <div className="guide-meta">
          {publishedLabel ? (
            <time dateTime={publishedAt}>
              {t("guide.published")} {publishedLabel}
            </time>
          ) : null}
          <span>{t("guide.author")}</span>
          {card.approved ? (
            <span className="verified-pill">
              <BadgeCheck size={14} aria-hidden="true" />
              {t("guide.verified")}
            </span>
          ) : (
            <span className="checked-pill">{t("guide.checked")}</span>
          )}
        </div>
      </header>

      <GuideHero src={card.image || article.image} alt={card.title} />

      <div className="guide-sheet">
        {toc.length > 0 ? (
          <nav className="guide-toc" aria-label={t("guide.toc")}>
            <h2>{t("guide.toc")}</h2>
            <ol>
              {toc.map((item) => (
                <li key={item.id} className={item.level === 3 ? "toc-h3" : "toc-h2"}>
                  <a href={`#${item.id}`} onClick={jumpTo(item.id)}>
                    {item.text}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
        ) : null}

        {article.before ? (
          <ArticleView
            markdown={article.before}
            isApproved={false}
            headingIds={article.beforeHeadings}
            plain
          />
        ) : null}

        <AdSenseUnit slotId="article-mid" format="auto" />

        {article.after ? (
          <ArticleView
            markdown={article.after}
            isApproved={false}
            headingIds={article.afterHeadings}
            plain
          />
        ) : null}

        <div className="source-block">
          <h2>{t("guide.sources")}</h2>
          <ul className="tag-row">
            {sources.map((item) => (
              <li key={`${item.label}-${item.href}`}>
                {item.href ? (
                  <a href={item.href} target="_blank" rel="noopener noreferrer">
                    {item.label}
                  </a>
                ) : (
                  item.label
                )}
              </li>
            ))}
          </ul>
        </div>

        <AdSenseUnit slotId="article-bottom" format="auto" />
        <footer className="guide-vote guide-share-row">
          <VoteButton articleId={card.id} />
          <ShareSheet
            title={card.title}
            description={card.summary}
            pathname={`/guide/${encodeURIComponent(fileName || card.id)}`}
            image={card.image}
          />
        </footer>
      </div>
    </article>
  );
}
