import { Trans, useTranslation } from "react-i18next";
import PolicyNav from "../components/PolicyNav";

const CONTACT_EMAIL = "bluelog.official@gmail.com";
const MAIL = { mail: <a href={`mailto:${CONTACT_EMAIL}`} /> };

export default function TermsOfService({ onNavigate }) {
  const { t } = useTranslation();

  return (
    <article className="policy-page">
      <p className="policy-kicker">{t("terms.kicker")}</p>
      <h1>{t("terms.title")}</h1>
      <p className="policy-updated">{t("terms.updated")}</p>
      <PolicyNav onNavigate={onNavigate} current="/terms" variant="page" />

      <section>
        <h2>{t("terms.useTitle")}</h2>
        <p>{t("terms.use1")}</p>
        <p>{t("terms.use2")}</p>
      </section>

      <section>
        <h2>{t("terms.postsTitle")}</h2>
        <p>{t("terms.postsBody")}</p>
      </section>

      <section>
        <h2>{t("terms.contentTitle")}</h2>
        <p>{t("terms.contentBody")}</p>
      </section>

      <section>
        <h2>{t("terms.adsTitle")}</h2>
        <p>{t("terms.adsBody")}</p>
      </section>

      <section>
        <h2>{t("terms.liabilityTitle")}</h2>
        <p>{t("terms.liabilityBody")}</p>
      </section>

      <section>
        <h2>{t("terms.contactTitle")}</h2>
        <p>
          <Trans i18nKey="terms.contactBody" values={{ email: CONTACT_EMAIL }} components={MAIL} />
        </p>
      </section>
    </article>
  );
}
