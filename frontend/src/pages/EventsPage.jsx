import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { API_BASE_URL } from "../lib/guideCards";

export default function EventsPage({ onNavigate, onCheckPoints, onIssueVoucher }) {
  const { t } = useTranslation();
  const [partners, setPartners] = useState([]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/rewards/overview`)
      .then(async (res) => {
        if (!res.ok) return null;
        return res.json();
      })
      .then((data) => {
        if (!cancelled && Array.isArray(data?.partners)) setPartners(data.partners);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <article className="policy-page events-page">
      <p className="policy-kicker">{t("events.kicker")}</p>
      <h1>{t("events.title")}</h1>
      <p>{t("events.lead")}</p>

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

      <h2>{t("events.partnersTitle")}</h2>
      <p>{t("events.partnersBody")}</p>
      {partners.length ? (
        <ul className="partner-list">
          {partners.map((partner) => (
            <li key={partner.id}>
              <strong>{partner.name}</strong>
              {` · ${partner.city} · ${partner.discount_rate}% · ${partner.status}`}
            </li>
          ))}
        </ul>
      ) : (
        <p>{t("events.partnersEmpty")}</p>
      )}

      <button type="button" className="text-link" onClick={() => onNavigate?.("/magazine-request")}>
        {t("events.requestCta")}
      </button>
    </article>
  );
}
