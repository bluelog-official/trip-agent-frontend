import { useTranslation } from "react-i18next";

const LINKS = [
  { href: "/about", labelKey: "footer.about" },
  { href: "/terms", labelKey: "footer.terms" },
  { href: "/privacy", labelKey: "footer.privacy" },
];

export default function PolicyNav({ onNavigate, current = "", variant = "hero" }) {
  const { t } = useTranslation();

  return (
    <nav
      className={variant === "page" ? "policy-nav policy-nav-page" : "policy-nav"}
      aria-label={t("footer.requiredLinks")}
    >
      {LINKS.map((link) => (
        <a
          key={link.href}
          href={link.href}
          aria-current={current === link.href ? "page" : undefined}
          onClick={(event) => {
            if (!onNavigate) return;
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
            event.preventDefault();
            onNavigate(link.href);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        >
          {t(link.labelKey)}
        </a>
      ))}
    </nav>
  );
}
