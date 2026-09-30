import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import ShareSheet from "../components/portal/ShareSheet";
import { API_BASE_URL } from "../lib/guideCards";

export default function PartnerPage({ partnerId, onNavigate, onClaim, onLoaded }) {
  const { t } = useTranslation();
  const [partner, setPartner] = useState(null);
  const [missing, setMissing] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let cancelled = false;
    setPartner(null);
    setMissing(false);
    fetch(`${API_BASE_URL}/rewards/overview`)
      .then(async (res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled) return;
        const found = (data?.partners || []).find((item) => String(item.id) === String(partnerId)) || null;
        setPartner(found);
        setMissing(!found);
        onLoaded?.(found);
      })
      .catch(() => {
        if (!cancelled) setMissing(true);
      });
    return () => {
      cancelled = true;
    };
  }, [partnerId, onLoaded]);

  const claim = async () => {
    if (!partner) return;
    setNotice("");
    const result = await onClaim?.(partner);
    setNotice(result?.ok ? t("events.claimDone") : t("events.claimFailed"));
  };

  if (missing) {
    return (
      <article className="policy-page">
        <h1>{t("events.partnersTitle")}</h1>
        <p>{t("events.partnersEmpty")}</p>
        <button type="button" className="text-link" onClick={() => onNavigate?.("/events")}>
          {t("events.title")}
        </button>
      </article>
    );
  }

  if (!partner) {
    return <p className="grid-empty">{t("guide.loading")}</p>;
  }

  return (
    <article className="policy-page partner-page">
      <p className="policy-kicker">{t("events.partnersTitle")}</p>
      <h1>{partner.name}</h1>
      <p>
        {[partner.city, partner.category, partner.offered_benefit].filter(Boolean).join(" · ")}
      </p>
      {partner.store_description ? <p>{partner.store_description}</p> : null}
      {partner.address ? <p>{partner.address}</p> : null}
      {partner.image_url ? <img className="guide-hero" src={partner.image_url} alt={partner.name} /> : null}
      <ShareSheet
        title={partner.name}
        description={partner.store_description || partner.offered_benefit || partner.city}
        pathname={`/partners/${partner.id}`}
        image={partner.image_url}
      />
      <div className="events-actions">
        <button type="button" className="dashboard-btn" onClick={claim}>
          {t("events.claim")}
          {partner.voucher_points ? ` · ${t("events.pointsCost", { points: partner.voucher_points })}` : ""}
        </button>
      </div>
      {notice ? <p role="status">{notice}</p> : null}
    </article>
  );
}
