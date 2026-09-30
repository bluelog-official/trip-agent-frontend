import { Compass } from "lucide-react";
import { useTranslation } from "react-i18next";

function FooterLink({ href, onNavigate, children, external = false }) {
  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  }

  return (
    <a
      href={href}
      onClick={(event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        onNavigate(href);
        const hash = href.includes("#") ? href.slice(href.indexOf("#") + 1) : "";
        window.setTimeout(() => {
          const target = hash ? document.getElementById(hash) : null;
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
          else window.scrollTo({ top: 0, behavior: "smooth" });
        }, 0);
      }}
    >
      {children}
    </a>
  );
}

export default function Footer({ onNavigate }) {
  const { t } = useTranslation();
  const visit = (path) => {
    onNavigate(path);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const legalLinks = [
    { href: "/privacy", label: t("footer.privacy") },
    { href: "/terms", label: t("footer.terms") },
    { href: "/about", label: t("footer.about") },
    { href: "/contact", label: t("footer.contact") },
    { href: "/sitemap.xml", label: t("footer.sitemap") },
  ];

  return (
    <footer className="portal-footer">
      <div className="footer-grid">
        <section className="footer-brand" aria-label={t("footer.brand")}>
          <button type="button" className="footer-logo" onClick={() => visit("/")}>
            <Compass size={22} aria-hidden="true" />
            <span>BlueLog Trip</span>
          </button>
          <p className="footer-tagline">{t("footer.tagline")}</p>
        </section>

        <nav className="footer-col" aria-label={t("footer.navLabel")}>
          <p className="footer-heading">{t("footer.navigation")}</p>
          <ul className="footer-links">
            <li>
              <button type="button" onClick={() => visit("/")}>{t("footer.home")}</button>
            </li>
            <li>
              <button type="button" onClick={() => visit("/destinations")}>{t("footer.destinations")}</button>
              <ul className="footer-sublinks">
                <li>
                  <button type="button" onClick={() => visit("/destinations/asia")}>{t("footer.asia")}</button>
                </li>
                <li>
                  <button type="button" onClick={() => visit("/destinations/europe")}>{t("footer.europe")}</button>
                </li>
                <li>
                  <button type="button" onClick={() => visit("/destinations/americas")}>{t("footer.americas")}</button>
                </li>
              </ul>
            </li>
            <li>
              <button type="button" onClick={() => visit("/local-food")}>{t("footer.localFood")}</button>
            </li>
            <li>
              <button type="button" onClick={() => visit("/community")}>{t("footer.community")}</button>
            </li>
            <li>
              <button type="button" onClick={() => visit("/events")}>{t("footer.events")}</button>
            </li>
            <li>
              <button type="button" onClick={() => visit("/wallet")}>{t("footer.wallet")}</button>
            </li>
          </ul>
        </nav>

        <nav className="footer-col" aria-label={t("footer.legalLabel")}>
          <p className="footer-heading">{t("footer.legalHeading")}</p>
          <ul className="footer-links">
            <li>
              <FooterLink href="/privacy" onNavigate={onNavigate}>{t("footer.privacy")}</FooterLink>
            </li>
            <li>
              <FooterLink href="/terms" onNavigate={onNavigate}>{t("footer.terms")}</FooterLink>
            </li>
            <li>
              <FooterLink href="/privacy#cookies" onNavigate={onNavigate}>{t("footer.cookie")}</FooterLink>
            </li>
          </ul>
        </nav>

        <nav className="footer-col" aria-label={t("footer.supportLabel")}>
          <p className="footer-heading">{t("footer.supportHeading")}</p>
          <ul className="footer-links">
            <li>
              <FooterLink href="/about" onNavigate={onNavigate}>{t("footer.about")}</FooterLink>
            </li>
            <li>
              <FooterLink href="/about#editorial" onNavigate={onNavigate}>{t("footer.editorial")}</FooterLink>
            </li>
            <li>
              <FooterLink href="/contact" onNavigate={onNavigate}>{t("footer.contact")}</FooterLink>
            </li>
            <li>
              <FooterLink href="/sitemap.xml" external>{t("footer.sitemap")}</FooterLink>
            </li>
          </ul>
        </nav>
      </div>

      <div className="footer-bottom">
        <nav aria-label={t("footer.requiredLinks")}>
          <ul className="footer-legal">
            {legalLinks.map((link) => (
              <li key={link.href}>
                <FooterLink href={link.href} onNavigate={onNavigate} external={link.href === "/sitemap.xml"}>
                  {link.label}
                </FooterLink>
              </li>
            ))}
          </ul>
        </nav>
        <p className="footer-copy">{t("footer.copyright")}</p>
      </div>
    </footer>
  );
}
