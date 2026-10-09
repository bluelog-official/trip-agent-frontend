import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";

export default function HeroSearch({ query, onQueryChange, onSearch, onPromote }) {
  const { t } = useTranslation();
  return (
    <section className="hero">
      <p className="hero-kicker">{t("hero.kicker")}</p>
      <h1 className="hero-title">{t("hero.title")}</h1>
      <p className="hero-copy">{t("hero.copy")}</p>
      <p className="hero-copy">{t("hero.about")}</p>
      <form className="hero-search" onSubmit={onSearch}>
        <Search size={18} aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={t("hero.placeholder")}
          aria-label={t("hero.title")}
        />
        <button type="submit">{t("hero.search")}</button>
      </form>
      <button type="button" className="hero-promote" onClick={onPromote}>
        {t("hero.promote")}
      </button>
    </section>
  );
}

const INTRO_KEYS = {
  all: "categories.all",
  asia: "categories.asia",
  europe: "categories.europe",
  americas: "categories.americas",
  food: "categories.food",
};

export function CategoryIntro({ category }) {
  const { t } = useTranslation();
  const prefix = INTRO_KEYS[category];
  if (!prefix) return null;
  return (
    <section className="category-intro">
      <p className="hero-kicker">{t(`${prefix}.kicker`)}</p>
      <h1 className="category-title">{t(`${prefix}.title`)}</h1>
      <p className="category-copy">{t(`${prefix}.text`)}</p>
    </section>
  );
}

export function CityIntro({ city }) {
  const { t } = useTranslation();
  if (!city) return null;
  return (
    <section className="category-intro">
      <p className="hero-kicker">{t("globe.cityKicker")}</p>
      <h1 className="category-title">{city}</h1>
      <p className="category-copy">{t("globe.cityText", { city })}</p>
    </section>
  );
}
