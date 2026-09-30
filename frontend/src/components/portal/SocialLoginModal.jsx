import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchAuthProviders } from "../../lib/session";

const PROVIDERS = [
  { id: "google", labelKey: "auth.google" },
  { id: "apple", labelKey: "auth.apple" },
  { id: "kakao", labelKey: "auth.kakao" },
];

const TITLES = {
  report: "auth.reportTitle",
  points: "auth.pointsTitle",
  voucher: "auth.voucherTitle",
  save: "auth.saveTitle",
};

export default function SocialLoginModal({
  reason = "sign-in",
  onClose,
  onSelect,
  onGuest,
}) {
  const { t } = useTranslation();
  const [providers, setProviders] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchAuthProviders()
      .then((rows) => {
        if (!cancelled) setProviders(rows);
      })
      .catch(() => {
        if (!cancelled) setProviders([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const configured = (id) => providers.find((item) => item.id === id)?.configured === true;

  return (
    <div className="auth-modal" role="presentation" onClick={onClose}>
      <div
        className="auth-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="auth-title">{t(TITLES[reason] || "auth.title")}</h2>
        <div className="auth-providers">
          {PROVIDERS.map((provider) => {
            const ready = configured(provider.id);
            return (
              <button
                key={provider.id}
                type="button"
                className="auth-provider"
                disabled={!ready}
                onClick={() => {
                  setError("");
                  Promise.resolve(onSelect?.(provider.id)).catch(() => setError(t("auth.failed")));
                }}
              >
                {t(provider.labelKey)}
                {providers.length && !ready ? <small>{t("auth.unconfigured")}</small> : null}
              </button>
            );
          })}
        </div>
        {error ? <p className="auth-error">{error}</p> : null}
        {reason === "report" ? (
          <button type="button" className="text-link" onClick={onGuest}>
            {t("auth.guest")}
          </button>
        ) : null}
        <button type="button" className="text-link" onClick={onClose}>
          {t("auth.close")}
        </button>
      </div>
    </div>
  );
}
