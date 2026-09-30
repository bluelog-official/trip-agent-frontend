import { useTranslation } from "react-i18next";
import GuideArticle from "./GuideArticle";
import ViralExport from "../ViralExport";
import { readGuideApproved } from "../adSlotPlan";

export default function ArticleReader({
  guide,
  fileName,
  tab,
  onTabChange,
  publishing,
  onApprove,
  onBack,
  onOpenCommunity,
  onNavigate,
  adminMode = false,
  saved = false,
  onSave,
}) {
  const { t } = useTranslation();

  if (!guide) {
    return <p className="grid-empty">{t("guide.loading")}</p>;
  }

  const approved = readGuideApproved(guide);

  return (
    <div className="detail-panel">
      <button type="button" className="back-link" onClick={onBack}>
        ← {t("guide.back")}
      </button>
      {tab === "article" ? (
        <GuideArticle
          guide={guide}
          fileName={fileName}
          onNavigate={onNavigate}
        />
      ) : null}
      {adminMode ? (
        <div className="review-bar">
          <div>
            <strong>{approved ? t("guide.reviewApproved") : t("guide.reviewPending")}</strong>
            <p>{approved ? t("guide.reviewApprovedHelp") : t("guide.reviewPendingHelp")}</p>
          </div>
          <button
            type="button"
            className="approve-btn"
            onClick={onApprove}
            disabled={approved || publishing}
          >
            {publishing ? t("guide.publishing") : t("guide.approve")}
          </button>
        </div>
      ) : null}
      <div className="reader-tools">
        <div className="detail-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "article"}
            className={tab === "article" ? "detail-tab active" : "detail-tab"}
            onClick={() => onTabChange("article")}
          >
            {t("guide.articleTab")}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "viral"}
            className={tab === "viral" ? "detail-tab active" : "detail-tab"}
            onClick={() => onTabChange("viral")}
          >
            {t("guide.viralTab")}
          </button>
        </div>
        <button type="button" className="text-link" onClick={onOpenCommunity}>
          {t("guide.openCommunity")}
        </button>
        {onSave ? (
          <button type="button" className="text-link" onClick={onSave}>
            {saved ? t("guide.saved") : t("guide.save")}
          </button>
        ) : null}
      </div>
      {tab === "viral" ? (
        <ViralExport syndication={guide.syndication} />
      ) : null}
    </div>
  );
}
