import { Trans, useTranslation } from "react-i18next";
import PolicyNav from "../components/PolicyNav";

const CONTACT_EMAIL = "bluelog.official@gmail.com";
const ADS_URL = "https://policies.google.com/technologies/ads";
const SETTINGS_URL = "https://adssettings.google.com";
const CHOICES_URL = "https://www.aboutads.info/choices";
const EEA_URL = "https://www.youronlinechoices.eu";
const MAIL = { mail: <a href={`mailto:${CONTACT_EMAIL}`} /> };

export default function PrivacyPolicy({ onNavigate }) {
  const { t } = useTranslation();

  return (
    <article className="policy-page">
      <p className="policy-kicker">{t("privacy.kicker")}</p>
      <h1>{t("privacy.title")}</h1>
      <p className="policy-updated">{t("privacy.updated")}</p>
      <PolicyNav onNavigate={onNavigate} current="/privacy" variant="page" />

      <section>
        <h2>{t("privacy.whoTitle")}</h2>
        <p>{t("privacy.whoBody")}</p>
      </section>

      <section>
        <h2>{t("privacy.collectTitle")}</h2>
        <p>{t("privacy.collect1")}</p>
        <p>{t("privacy.collect2")}</p>
      </section>

      <section id="cookies">
        <h2>{t("privacy.cookiesTitle")}</h2>
        <p>{t("privacy.cookies1")}</p>
        <p>{t("privacy.cookies2")}</p>
        <p>{t("privacy.cookies3")}</p>
      </section>

      <section id="adsense">
        <h2>{t("privacy.adsenseTitle")}</h2>
        <p>{t("privacy.adsense1")}</p>
        <p>
          <Trans
            i18nKey="privacy.adsense2"
            values={{ adsUrl: ADS_URL }}
            components={{ ads: <a href={ADS_URL} rel="noopener noreferrer" /> }}
          />
        </p>
        <p>
          <Trans
            i18nKey="privacy.adsense3"
            values={{ settingsUrl: SETTINGS_URL, choicesUrl: CHOICES_URL, eeaUrl: EEA_URL }}
            components={{
              settings: <a href={SETTINGS_URL} rel="noopener noreferrer" />,
              choices: <a href={CHOICES_URL} rel="noopener noreferrer" />,
              eea: <a href={EEA_URL} rel="noopener noreferrer" />,
            }}
          />
        </p>
      </section>

      <section>
        <h2>{t("privacy.othersTitle")}</h2>
        <p>{t("privacy.othersBody")}</p>
      </section>

      <section>
        <h2>{t("privacy.contactTitle")}</h2>
        <p>
          <Trans i18nKey="privacy.contactBody" values={{ email: CONTACT_EMAIL }} components={MAIL} />
        </p>
      </section>
    </article>
  );
}
