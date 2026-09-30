import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { API_BASE_URL } from "../../lib/guideCards";

export default function PartnerOffers({ onClaim }) {
  const { t } = useTranslation();
  const [partners, setPartners] = useState([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/rewards/overview`)
      .then(async (res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && Array.isArray(data?.partners)) setPartners(data.partners);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const claim = async (partner) => {
    setNotice("");
    setBusy(partner.id);
    try {
      const result = await onClaim?.(partner);
      if (result?.ok) setNotice(t("events.claimDone"));
      else if (result?.reason === "failed") setNotice(t("events.claimFailed"));
    } finally {
      setBusy(0);
    }
  };

  return (
    <section className="partner-offers" aria-label={t("events.partnersTitle")}>
      <h2>{t("events.partnersTitle")}</h2>
      <p>{t("events.partnersBody")}</p>
      {notice ? <p role="status">{notice}</p> : null}
      {partners.length ? (
        <ul className="partner-list">
          {partners.map((partner) => (
            <li key={partner.id}>
              <strong>{partner.name}</strong>
              <span>
                {` · ${partner.city || ""}`}
                {partner.category ? ` · ${partner.category}` : ""}
                {partner.offered_benefit ? ` · ${partner.offered_benefit}` : ""}
              </span>
              <button type="button" disabled={busy === partner.id} onClick={() => claim(partner)}>
                {t("events.claim")}
                {partner.voucher_points ? ` · ${t("events.pointsCost", { points: partner.voucher_points })}` : ""}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p>{t("events.partnersEmpty")}</p>
      )}
    </section>
  );
}
