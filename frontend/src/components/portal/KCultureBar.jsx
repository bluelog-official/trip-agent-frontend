import { useTranslation } from "react-i18next";
import { K_THEME_FILTERS } from "../../lib/kculture";

export default function KCultureBar({ active, theme, onToggle, onTheme }) {
  const { t } = useTranslation();
  return (
    <section className={active ? "kculture-bar is-on" : "kculture-bar"} aria-label={t("kculture.label")}>
      <div className="kculture-copy">
        <button
          type="button"
          className="kculture-toggle"
          aria-pressed={active}
          onClick={onToggle}
        >
          {t("kculture.bannerTitle")}
        </button>
        <p>{t("kculture.bannerCopy")}</p>
      </div>
      <div className="kculture-chips" role="radiogroup" aria-label={t("kculture.themesLabel")}>
        {K_THEME_FILTERS.map((item) => {
          const selected = item.id === theme;
          return (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={selected}
              className={selected ? "is-active" : ""}
              onClick={() => onTheme(item.id)}
            >
              {t(item.labelKey)}
            </button>
          );
        })}
      </div>
    </section>
  );
}
