import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { apiOrigin } from "../lib/guideCards";
import { authHeaders } from "../lib/session";

const TABS = ["history", "reports", "saved", "vouchers"];

function reasonLabel(reason, t) {
  if (reason === "MAGAZINE_PUBLISHED") return t("wallet.reasonPublished");
  if (reason === "UGC_TOP_RANK_BONUS") return t("wallet.reasonRank");
  if (reason === "VOUCHER_CLAIM") return t("wallet.reasonVoucher");
  if (reason === "DEV_TEST_GRANT") return t("wallet.reasonDev");
  return reason;
}

function stateLabel(state, t) {
  const keys = {
    PENDING: "wallet.statePending",
    VERIFIED: "wallet.stateVerified",
    PUBLISHED: "wallet.statePublished",
    REJECTED: "wallet.stateRejected",
  };
  return t(keys[state] || "wallet.statePending");
}

export default function WalletPage({ session, onNavigate }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState("history");
  const [wallet, setWallet] = useState(null);
  const [error, setError] = useState("");
  const [openVoucher, setOpenVoucher] = useState(null);

  const load = () => {
    if (!session?.token) return undefined;
    let cancelled = false;
    fetch(`${apiOrigin()}/api/v1/wallet`, { headers: authHeaders(session.token) })
      .then(async (response) => {
        if (!response.ok) throw new Error("wallet");
        return response.json();
      })
      .then((data) => {
        if (!cancelled) {
          setWallet(data);
          setError("");
        }
      })
      .catch(() => {
        if (!cancelled) setError(t("wallet.loadError"));
      });
    return () => {
      cancelled = true;
    };
  };

  useEffect(() => load(), [session?.token, t]);

  const removeSaved = async (guideId) => {
    const response = await fetch(`${apiOrigin()}/api/v1/wallet/saved/${encodeURIComponent(guideId)}`, {
      method: "DELETE",
      headers: authHeaders(session.token),
    });
    if (!response.ok) return;
    const saved = await response.json();
    setWallet((current) => (current ? { ...current, saved_guides: saved } : current));
  };

  const profile = wallet || {
    email: session?.email || "",
    name: session?.name || "",
    auth_provider: session?.provider || "",
    points_balance: session?.pointsBalance || 0,
    logs: [],
    reports: [],
    saved_guides: [],
    vouchers: [],
  };
  const vouchers = profile.vouchers || [];

  return (
    <article className="policy-page wallet-page">
      <p className="policy-kicker">{t("wallet.kicker")}</p>
      <h1>{t("wallet.title")}</h1>
      <p className="wallet-profile">
        <strong>{profile.name || profile.email}</strong>
        <span>{profile.email}</span>
        {profile.auth_provider ? (
          <span>{t("wallet.provider", { provider: profile.auth_provider })}</span>
        ) : null}
      </p>
      <section className="wallet-balance" aria-label={t("wallet.balanceLabel")}>
        <p>{t("wallet.balanceLabel")}</p>
        <strong>{profile.points_balance}</strong>
      </section>
      {error ? <p className="auth-error">{error}</p> : null}
      <div className="detail-tabs" role="tablist">
        {TABS.map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? "detail-tab active" : "detail-tab"}
            onClick={() => setTab(id)}
          >
            {t(`wallet.${id}`)}
          </button>
        ))}
      </div>
      {tab === "history" ? (
        profile.logs.length ? (
          <ul className="wallet-list">
            {profile.logs.map((row) => (
              <li key={row.id}>
                <span>{reasonLabel(row.reason, t)}</span>
                <strong>{row.amount > 0 ? `+${row.amount}` : row.amount}</strong>
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("wallet.emptyHistory")}</p>
        )
      ) : null}
      {tab === "reports" ? (
        profile.reports.length ? (
          <ul className="wallet-list">
            {profile.reports.map((row) => (
              <li key={row.id}>
                <span>
                  {row.city} · {row.place}
                  <small>{stateLabel(row.publish_state, t)}</small>
                </span>
                {row.xrpl_url ? (
                  <a href={row.xrpl_url} target="_blank" rel="noopener noreferrer">
                    {t("wallet.ledger")}
                  </a>
                ) : (
                  <small>{t("wallet.ledgerPending")}</small>
                )}
                {row.content_sha256 ? <small>{`${t("wallet.anchor")} ${row.content_sha256}`}</small> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("wallet.emptyReports")}</p>
        )
      ) : null}
      {tab === "saved" ? (
        profile.saved_guides.length ? (
          <ul className="wallet-list">
            {profile.saved_guides.map((guideId) => (
              <li key={guideId}>
                <button type="button" className="text-link" onClick={() => onNavigate?.(`/guide/${encodeURIComponent(guideId)}`)}>
                  {guideId}
                </button>
                <button type="button" onClick={() => removeSaved(guideId)}>
                  {t("wallet.remove")}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("wallet.emptySaved")}</p>
        )
      ) : null}
      {tab === "vouchers" ? (
        vouchers.length ? (
          <ul className="wallet-list">
            {vouchers.map((row) => (
              <li key={row.id}>
                <span>
                  {row.merchant_name || row.voucher_code}
                  <small>{row.offered_benefit}</small>
                </span>
                <button type="button" onClick={() => setOpenVoucher(row)}>
                  {t("wallet.showCode")}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("wallet.emptyVouchers")}</p>
        )
      ) : null}
      {openVoucher ? (
        <div className="voucher-modal" role="presentation" onClick={() => setOpenVoucher(null)}>
          <div
            className="voucher-card"
            role="dialog"
            aria-modal="true"
            aria-label={t("wallet.qrTitle")}
            onClick={(event) => event.stopPropagation()}
          >
            <h2>{t("wallet.qrTitle")}</h2>
            <p>{openVoucher.merchant_name}</p>
            {String(openVoucher.qr_svg || "").startsWith("<svg") ? (
              <div className="voucher-qr" dangerouslySetInnerHTML={{ __html: openVoucher.qr_svg }} />
            ) : null}
            <p>
              {t("wallet.coupon")}
              <strong>{` ${openVoucher.voucher_code}`}</strong>
            </p>
            <button type="button" className="contact-submit" onClick={() => setOpenVoucher(null)}>
              {t("wallet.qrClose")}
            </button>
          </div>
        </div>
      ) : null}
    </article>
  );
}
