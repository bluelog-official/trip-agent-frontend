import { Trans, useTranslation } from "react-i18next";
import PolicyNav from "../components/PolicyNav";

const CONTACT_EMAIL = "bluelog.official@gmail.com";
const MAIL = { mail: <a href={`mailto:${CONTACT_EMAIL}`} /> };

export default function About({ onNavigate }) {
  const { t } = useTranslation();

  return (
    <article className="policy-page">
      <p className="policy-kicker">{t("about.kicker")}</p>
      <h1>{t("about.title")}</h1>
      <p className="policy-updated">{t("about.updated")}</p>
      <PolicyNav onNavigate={onNavigate} current="/about" variant="page" />

      <section>
        <h2>{t("about.missionTitle")}</h2>
        <p>{t("about.mission1")}</p>
        <p>{t("about.mission2")}</p>
      </section>

      <section id="editorial">
        <h2>{t("about.trustTitle")}</h2>
        <p>{t("about.trust1")}</p>
        <p>
          <Trans i18nKey="about.trust2" values={{ email: CONTACT_EMAIL }} components={MAIL} />
        </p>
        <p>{t("about.trust3")}</p>
      </section>

      <section>
        <h2>{t("about.contactTitle")}</h2>
        <p>
          <Trans i18nKey="about.contactBody" values={{ email: CONTACT_EMAIL }} components={MAIL} />
        </p>
      </section>
    </article>
  );
}
