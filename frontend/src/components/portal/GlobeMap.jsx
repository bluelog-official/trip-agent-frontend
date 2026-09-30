import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { appLanguage } from "../../i18n/i18n";
import {
  GLOBE_PERIODS,
  fetchGlobeCities,
  globeCityLabel,
  pinScale,
  trendValue,
} from "../../lib/globeCities";
import FlatWorldMap from "./FlatWorldMap";
import KCultureBar from "./KCultureBar";

export default function GlobeMap({ onOpenCity, hotCountry = false, kTheme = "all", onToggleHot, onTheme }) {
  const { t } = useTranslation();
  const language = appLanguage();
  const [period, setPeriod] = useState("all");
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeSlug, setActiveSlug] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchGlobeCities(period)
      .then((payload) => {
        if (cancelled) return;
        setCities(payload.cities);
        setError("");
      })
      .catch((err) => {
        console.error("지도 도시 로드 실패:", err);
        if (!cancelled) {
          setCities([]);
          setError("failed");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  useEffect(() => {
    if (activeSlug && !cities.some((city) => city.slug === activeSlug)) {
      setActiveSlug("");
    }
  }, [cities, activeSlug]);

  const markers = useMemo(
    () =>
      cities.map((city) => ({
        ...city,
        period,
        pinScale: pinScale(period, city.recency, city.is_top, cities.length),
        active: city.slug === activeSlug,
        label: t("globe.openCity", {
          city: globeCityLabel(city, language),
          count: city.published_count,
        }),
      })),
    [cities, period, activeSlug, language, t],
  );

  const topCities = markers.filter((city) => city.is_top).slice(0, 5);
  const trendCaption = period === "all" ? t("globe.trendNoteAll") : t("globe.trendNote");

  const openCity = (city) => {
    setActiveSlug(city.slug);
    onOpenCity?.(city);
  };

  return (
    <section className="globe-band" aria-labelledby="globe-title" data-period={period}>
      <KCultureBar
        active={hotCountry}
        theme={kTheme}
        onToggle={onToggleHot}
        onTheme={onTheme}
      />
      <div className="globe-layout">
        <div className="globe-copy">
          <p className="hero-kicker">{t("globe.kicker")}</p>
          <h2 id="globe-title">{t("globe.title")}</h2>
          <p className="globe-lead">{t("globe.copy")}</p>
          <div className="globe-filters" role="radiogroup" aria-label={t("globe.filterLabel")}>
            {GLOBE_PERIODS.map((id) => (
              <button
                key={id}
                type="button"
                role="radio"
                aria-checked={period === id}
                className={period === id ? "is-active" : ""}
                data-period={id}
                onClick={() => setPeriod(id)}
              >
                {t(`globe.period.${id}`)}
              </button>
            ))}
          </div>
          <p className="globe-hint" role="status">{t("globe.hint")}</p>
          <div className="globe-rank-card">
            <h3>{t("globe.rankTitle")}</h3>
            <p>{t("globe.rankHint")}</p>
            {loading && cities.length === 0 ? <p className="globe-note">{t("globe.loading")}</p> : null}
            {error ? <p className="globe-note">{t("globe.error")}</p> : null}
            {!loading && !error && topCities.length === 0 ? (
              <p className="globe-note">{t("globe.emptyPeriod")}</p>
            ) : null}
            {topCities.length > 0 ? (
              <ol className="globe-rank-list">
                {topCities.map((city) => {
                  const name = globeCityLabel(city, language);
                  const trend = city.trending_new ? t("globe.trendNew") : trendValue(city) || t("globe.trendFlat");
                  return (
                    <li key={city.slug}>
                      <button
                        type="button"
                        className={city.slug === activeSlug ? "is-active" : ""}
                        data-slug={city.slug}
                        onClick={() => openCity(city)}
                      >
                        <span className="globe-rank-badge">#{city.rank}</span>
                        <span className="globe-rank-body">
                          <span className="globe-rank-name">{name}</span>
                          {city.keywords.length ? (
                            <span className="globe-rank-tags">
                              {city.keywords.map((keyword) => `#${keyword}`).join(" ")}
                            </span>
                          ) : null}
                          <span className="globe-rank-metrics">
                            <span>{t("globe.votes", { count: city.vote_count || 0 })}</span>
                            <span>{t("globe.guides", { count: city.published_count })}</span>
                            <span>{t("globe.quality", { score: city.quality_score })}</span>
                            <span>
                              {trend}
                              <small>{trendCaption}</small>
                            </span>
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>
            ) : null}
          </div>
        </div>
        <div className="globe-stage" aria-busy={loading}>
          <FlatWorldMap cities={markers} onOpenCity={openCity} />
          {loading && cities.length === 0 ? <p className="globe-note">{t("globe.loading")}</p> : null}
          {error ? <p className="globe-note">{t("globe.error")}</p> : null}
          {!loading && !error && cities.length === 0 ? (
            <p className="globe-note">{t("globe.emptyPeriod")}</p>
          ) : null}
          <ul className="globe-legend">
            <li><span className="swatch published" />{t("globe.published")}</li>
            <li><span className="swatch top" />{t("globe.top")}</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
