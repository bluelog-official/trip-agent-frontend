import { useEffect, useRef, useState } from "react";
import { ChevronDown, Compass, Menu, Search, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import i18n, { normalizeAppLanguage } from "../../i18n/i18n";

const DESTINATION_PATHS = [
  { id: "all", labelKey: "nav.allRegions", path: "/destinations" },
  { id: "asia", labelKey: "nav.asia", path: "/destinations/asia" },
  { id: "europe", labelKey: "nav.europe", path: "/destinations/europe" },
  { id: "americas", labelKey: "nav.americas", path: "/destinations/americas" },
];

export default function GlobalNav({
  active,
  region,
  query,
  onQueryChange,
  onSearch,
  onNavigate,
  onOpenAdmin,
  onOpenDashboard,
  onLogout,
  adminMode = false,
  dashboardActive = false,
  userSession = null,
  onOpenLogin,
  onOpenWallet,
  onUserLogout,
  hotCountry = false,
  onToggleHotCountry,
}) {
  const { t } = useTranslation();
  const language = normalizeAppLanguage(i18n.language);
  const [destOpen, setDestOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const destRef = useRef(null);

  useEffect(() => {
    const onPointer = (event) => {
      if (destRef.current && !destRef.current.contains(event.target)) {
        setDestOpen(false);
      }
    };
    const onKey = (event) => {
      if (event.key === "Escape") {
        setDestOpen(false);
        setMobileOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const visit = (path) => {
    setDestOpen(false);
    setMobileOpen(false);
    onNavigate(path);
  };

  const changeLanguage = (event) => {
    const next = event.target.value === "ko" ? "ko" : "en";
    i18n.changeLanguage(next);
  };

  return (
    <header className="gnb">
      <div className="gnb-inner">
        <button type="button" className="logo" onClick={() => visit("/")}>
          <Compass size={22} aria-hidden="true" />
          <span>BlueLog Trip</span>
        </button>

        <button
          type="button"
          className="menu-toggle"
          aria-expanded={mobileOpen}
          aria-label={mobileOpen ? t("nav.closeMenu") : t("nav.openMenu")}
          onClick={() => setMobileOpen((open) => !open)}
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <nav className={mobileOpen ? "gnb-links open" : "gnb-links"} aria-label={t("nav.categories")}>
          <button
            type="button"
            className={active === "home" ? "nav-link active" : "nav-link"}
            onClick={() => visit("/")}
          >
            {t("nav.home")}
          </button>

          <div className="nav-dropdown" ref={destRef}>
            <button
              type="button"
              className={active === "destinations" ? "nav-link active" : "nav-link"}
              aria-expanded={destOpen}
              aria-haspopup="true"
              onClick={() => setDestOpen((open) => !open)}
            >
              {t("nav.destinations")}
              <ChevronDown size={16} aria-hidden="true" />
            </button>
            {destOpen ? (
              <div className="dropdown-panel" role="menu">
                {DESTINATION_PATHS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    role="menuitem"
                    className={region === item.id ? "dropdown-item active" : "dropdown-item"}
                    onClick={() => visit(item.path)}
                  >
                    {t(item.labelKey)}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <button
            type="button"
            className={active === "food" ? "nav-link active" : "nav-link"}
            onClick={() => visit("/local-food")}
          >
            {t("nav.localFood")}
          </button>
          <button
            type="button"
            className={active === "community" ? "nav-link active" : "nav-link"}
            onClick={() => visit("/community")}
          >
            {t("nav.community")}
          </button>
          <button
            type="button"
            className={active === "events" ? "nav-link active" : "nav-link"}
            onClick={() => visit("/events")}
          >
            {t("nav.events")}
          </button>
          <button
            type="button"
            className={hotCountry ? "nav-link hot-country active" : "nav-link hot-country"}
            aria-pressed={hotCountry}
            onClick={onToggleHotCountry}
          >
            {`🔥 ${t("nav.hotCountry")}`}
          </button>
        </nav>

        <div className="gnb-tools">
          <form className="gnb-search" onSubmit={onSearch}>
            <Search size={16} aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder={t("nav.searchPlaceholder")}
              aria-label={t("nav.searchGuides")}
            />
          </form>
          <select
            className="lang-select"
            value={language}
            aria-label={t("language.label")}
            onChange={changeLanguage}
          >
            <option value="en">{t("language.en")}</option>
            <option value="ko">{t("language.ko")}</option>
          </select>
          {userSession ? (
            <>
              <button type="button" className="dashboard-btn" onClick={onOpenWallet}>
                {t("nav.wallet")}
              </button>
              <button type="button" className="logout-btn" onClick={onUserLogout}>
                {t("nav.logout")}
              </button>
            </>
          ) : (
            <button type="button" className="dashboard-btn" onClick={onOpenLogin}>
              {t("nav.signIn")}
            </button>
          )}
          {adminMode ? (
            <>
              <button
                type="button"
                className={dashboardActive ? "dashboard-btn active" : "dashboard-btn"}
                onClick={onOpenDashboard}
              >
                {t("nav.dashboard")}
              </button>
              <button type="button" className="admin-btn" onClick={onOpenAdmin}>
                {t("nav.admin")}
              </button>
              <button type="button" className="logout-btn" onClick={onLogout}>
                {t("nav.logout")}
              </button>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
