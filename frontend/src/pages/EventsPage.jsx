import { useTranslation } from "react-i18next";
import PartnerOffers from "../components/portal/PartnerOffers";
import ShareSheet from "../components/portal/ShareSheet";

export default function EventsPage({ onNavigate, onCheckPoints, onIssueVoucher, onClaimVoucher }) {
  const { t } = useTranslation();

  return (
    <article className="policy-page events-page">
      <p className="policy-kicker">{t("events.kicker")}</p>
      <h1>{t("events.title")}</h1>
      <p>{t("events.lead")}</p>
      <p>{t("events.purpose")}</p>
      <ShareSheet
        title={t("meta.eventsTitle")}
        description={t("meta.eventsDescription")}
        pathname="/events"
      />

      <h2>{t("events.pointsTitle")}</h2>
      <ul>
        <li>{t("events.publishPoints")}</li>
        <li>{t("events.rankPoints")}</li>
      </ul>
      <p>{t("events.pointsNote")}</p>

      <h2>{t("events.signInTitle")}</h2>
      <p>{t("events.signInBody")}</p>
      <div className="events-actions">
        <button type="button" className="dashboard-btn" onClick={onCheckPoints}>
          {t("events.checkPoints")}
        </button>
        <button type="button" className="dashboard-btn" onClick={onIssueVoucher}>
          {t("events.issueVoucher")}
        </button>
      </div>

      <PartnerOffers onClaim={onClaimVoucher || (() => onIssueVoucher?.())} />

      <button type="button" className="text-link" onClick={() => onNavigate?.("/magazine-request")}>
        {t("events.requestCta")}
      </button>
    </article>
  );
}
