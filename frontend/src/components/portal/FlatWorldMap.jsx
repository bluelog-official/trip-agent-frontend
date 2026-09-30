import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { appLanguage } from "../../i18n/i18n";
import { continentPaths, pinPlacement } from "../../lib/flatMap";
import { globeCityLabel, pinScale } from "../../lib/globeCities";
import { fetchVoteStatuses } from "../../lib/votes";
import VoteButton from "./VoteButton";

const PATHS = continentPaths();

function MapThumb({ src, name }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return <div className="map-thumb-fallback" aria-hidden="true">{name.slice(0, 1)}</div>;
  }
  return <img src={src} alt="" onError={() => setFailed(true)} />;
}

function MapPin({ city, language, onOpenCity }) {
  const { t } = useTranslation();
  const placement = pinPlacement(city.lat, city.lng);
  const name = globeCityLabel(city, language);
  const size = Math.max(18, Math.round(28 * (Number(city.pinScale) || 1)));
  const [open, setOpen] = useState(false);
  const [total, setTotal] = useState(Number(city.vote_count) || 0);
  const [voted, setVoted] = useState(false);

  useEffect(() => {
    setTotal(Number(city.vote_count) || 0);
  }, [city.slug, city.vote_count]);

  useEffect(() => {
    if (!city.article_id) return undefined;
    let cancelled = false;
    fetchVoteStatuses([city.article_id])
      .then((rows) => {
        if (cancelled) return;
        const row = rows.find((item) => item.article_id === city.article_id) || rows[0];
        if (row) setVoted(Boolean(row.voted));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [city.article_id]);

  return (
    <div
      className={[
        "map-pin-wrap",
        open ? "is-open" : "",
        placement.openLeft ? "open-left" : "",
        placement.openUp ? "open-up" : "",
      ].filter(Boolean).join(" ")}
      style={{ left: `${placement.left}%`, top: `${placement.top}%` }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <button
        type="button"
        className={["globe-pin", "map-pin", city.is_top ? "is-top" : "", `period-${city.period || "all"}`].filter(Boolean).join(" ")}
        style={{ width: size, height: size }}
        aria-label={city.label || name}
        data-slug={city.slug}
        onClick={() => onOpenCity?.(city)}
      >
        <span className="globe-pin-count">{city.published_count}</span>
      </button>
      <div className="map-popover" role="tooltip" aria-label={name}>
        <MapThumb src={city.thumbnail} name={name} />
        <div className="map-popover-body">
          <strong>
            {city.flag ? <span className="map-flag" aria-hidden="true">{city.flag}</span> : null}
            {name}
          </strong>
          {city.keywords?.length ? (
            <ul className="map-chips">
              {city.keywords.map((keyword) => (
                <li key={keyword}>#{keyword}</li>
              ))}
            </ul>
          ) : null}
          <p className="map-vote-line">{t("globe.votes", { count: total })}</p>
          {city.article_id ? (
            <VoteButton
              articleId={city.article_id}
              count={total}
              voted={voted}
              managed
              onChange={(next) => {
                setTotal(next.vote_count);
                setVoted(next.voted);
              }}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function FlatWorldMap({ cities, onOpenCity }) {
  const { t } = useTranslation();
  const language = appLanguage();
  const markers = (cities || []).map((city) => ({
    ...city,
    pinScale: city.pinScale || pinScale(city.period, city.recency, city.is_top, cities.length),
  }));

  return (
    <div className="flat-map" data-testid="flat-map">
      <svg className="flat-map-svg" viewBox="0 0 960 480" role="img" aria-label={t("globe.mapLabel")}>
        <rect className="flat-ocean" x="0" y="0" width="960" height="480" />
        {Array.from({ length: 5 }, (_, index) => {
          const y = 80 + index * 80;
          return <line key={`lat-${y}`} className="flat-graticule" x1="0" y1={y} x2="960" y2={y} />;
        })}
        {Array.from({ length: 7 }, (_, index) => {
          const x = 120 + index * 120;
          return <line key={`lng-${x}`} className="flat-graticule" x1={x} y1="0" x2={x} y2="480" />;
        })}
        {PATHS.map((shape) => (
          <path key={shape.id} className="flat-land" d={shape.d} />
        ))}
      </svg>
      <div className="flat-map-pins">
        {markers.map((city) => (
          <MapPin key={city.slug} city={city} language={language} onOpenCity={onOpenCity} />
        ))}
      </div>
    </div>
  );
}
