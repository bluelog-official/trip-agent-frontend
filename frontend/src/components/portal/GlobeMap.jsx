import { Component, lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { appLanguage } from "../../i18n/i18n";
import {
  GLOBE_PERIODS,
  fetchGlobeCities,
  globeCityLabel,
  pinScale,
  trendValue,
} from "../../lib/globeCities";

const GlobeScene = lazy(() => import("./GlobeScene"));

function mediaMatches(query) {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia(query).matches;
}

function readGlobeMode() {
  const reducedMotion = mediaMatches("(prefers-reduced-motion: reduce)");
  const narrow = mediaMatches("(max-width: 720px)");
  const cores = typeof navigator === "undefined" ? 8 : navigator.hardwareConcurrency || 8;
  const saveData = typeof navigator !== "undefined" && navigator.connection?.saveData === true;
  return {
    reducedMotion,
    lowPower: Boolean(saveData || narrow || cores <= 4),
    skipWebgl: Boolean(saveData),
  };
}

class GlobeErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) return this.props.fallback;
    return this.props.children;
  }
}

function placeTip(band, point, event) {
  if (!band || !point) return null;
  const rect = band.getBoundingClientRect();
  const target = event?.currentTarget?.getBoundingClientRect?.();
  const x = Number.isFinite(event?.clientX) && event.clientX !== 0
    ? event.clientX
    : target
      ? target.left + target.width / 2
      : rect.left + 24;
  const y = Number.isFinite(event?.clientY) && event.clientY !== 0
    ? event.clientY
    : target
      ? target.top
      : rect.top + 24;
  return { point, x: x - rect.left, y: y - rect.top };
}

export default function GlobeMap({ onOpenCity }) {
  const { t } = useTranslation();
  const language = appLanguage();
  const bandRef = useRef(null);
  const sceneRef = useRef(null);
  const pendingFly = useRef(null);
  const handleReady = useCallback((api) => {
    sceneRef.current = api;
    if (pendingFly.current && api?.flyTo) {
      api.flyTo(pendingFly.current);
      pendingFly.current = null;
    }
  }, []);
  const [period, setPeriod] = useState("all");
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [visible, setVisible] = useState(false);
  const [mode, setMode] = useState(readGlobeMode);
  const [activeSlug, setActiveSlug] = useState("");
  const [tip, setTip] = useState(null);

  useEffect(() => {
    const node = bandRef.current;
    if (!node) {
      setVisible(true);
      return undefined;
    }
    const reveal = () => {
      const rect = node.getBoundingClientRect();
      const near = rect.top < window.innerHeight + 240 && rect.bottom > -240;
      if (near) setVisible(true);
      return near;
    };
    if (reveal() || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px 0px" },
    );
    observer.observe(node);
    window.addEventListener("scroll", reveal, { passive: true });
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", reveal);
    };
  }, []);

  useEffect(() => {
    const queries = ["(prefers-reduced-motion: reduce)", "(max-width: 720px)"];
    if (typeof window.matchMedia !== "function") return undefined;
    const lists = queries.map((query) => window.matchMedia(query));
    const sync = () => setMode(readGlobeMode());
    lists.forEach((list) => list.addEventListener?.("change", sync));
    return () => lists.forEach((list) => list.removeEventListener?.("change", sync));
  }, []);

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
        console.error("지구본 도시 로드 실패:", err);
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
  const showScene = visible && !mode.skipWebgl && markers.length > 0;
  const trendCaption = period === "all" ? t("globe.trendNoteAll") : t("globe.trendNote");

  const hoverCity = (point, event) => {
    setTip(placeTip(bandRef.current, point, event));
  };

  const focusCity = (city) => {
    setActiveSlug(city.slug);
    if (mode.skipWebgl) {
      onOpenCity(city);
      return;
    }
    if (sceneRef.current?.flyTo) {
      sceneRef.current.flyTo(city);
      return;
    }
    pendingFly.current = city;
  };

  const tipLabel = tip ? globeCityLabel(tip.point, language) : "";

  return (
    <section className="globe-band" ref={bandRef} aria-labelledby="globe-title" data-period={period}>
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
          <p className="globe-hint" role="status">
            {tip
              ? t("globe.tooltip", { city: tipLabel, count: tip.point.published_count })
              : t("globe.hint")}
          </p>
          {mode.skipWebgl ? <p className="globe-lite">{t("globe.lite")}</p> : null}
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
                        onClick={() => focusCity(city)}
                        onPointerEnter={(event) => hoverCity(city, event)}
                        onPointerLeave={() => setTip(null)}
                        onFocus={(event) => hoverCity(city, event)}
                        onBlur={() => setTip(null)}
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
          {showScene ? (
            <GlobeErrorBoundary fallback={<p className="globe-note globe-stage-note">{t("globe.lite")}</p>}>
              <Suspense fallback={<p className="globe-note globe-stage-note">{t("globe.loading")}</p>}>
                <GlobeScene
                  cities={markers}
                  period={period}
                  reducedMotion={mode.reducedMotion}
                  lowPower={mode.lowPower}
                  onOpenCity={onOpenCity}
                  onHover={hoverCity}
                  onReady={handleReady}
                />
              </Suspense>
            </GlobeErrorBoundary>
          ) : (
            <p className="globe-note globe-stage-note">
              {!visible || loading
                ? t("globe.loading")
                : error
                  ? t("globe.error")
                  : t("globe.emptyPeriod")}
            </p>
          )}
          <ul className="globe-legend">
            <li><span className="swatch published" />{t("globe.published")}</li>
            <li><span className="swatch top" />{t("globe.top")}</li>
          </ul>
        </div>
      </div>
      {tip ? (
        <div className="globe-tooltip" style={{ left: tip.x, top: tip.y }} role="tooltip">
          <strong>{tipLabel}</strong>
          <span>{t("globe.tooltip", { city: tipLabel, count: tip.point.published_count })}</span>
        </div>
      ) : null}
    </section>
  );
}
