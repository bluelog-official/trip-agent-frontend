import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Footer from "./components/Footer";
import VisitorBadge from "./components/VisitorBadge";
import About from "./pages/About";
import Contact from "./pages/Contact";
import Dashboard from "./pages/Dashboard";
import MagazineRequestPage from "./pages/MagazineRequestPage";
import PromoteStorePage from "./pages/PromoteStorePage";
import EventsPage from "./pages/EventsPage";
import PartnerPage from "./pages/PartnerPage";
import WalletPage from "./pages/WalletPage";
import NotFound from "./pages/NotFound";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import TermsOfService from "./pages/TermsOfService";
import AdSenseUnit from "./components/AdSenseUnit";
import AdminDrawer from "./components/portal/AdminDrawer";
import AdminLogin from "./components/portal/AdminLogin";
import ArticleGrid from "./components/portal/ArticleGrid";
import MagazineFilters from "./components/portal/MagazineFilters";
import ArticleReader from "./components/portal/ArticleReader";
import CommunityBoard from "./components/portal/CommunityBoard";
import GlobalNav from "./components/portal/GlobalNav";
import HeroSearch, { CategoryIntro, CityIntro } from "./components/portal/HeroSearch";
import GlobeMap from "./components/portal/GlobeMap";
import KCultureBar from "./components/portal/KCultureBar";
import ShareSheet from "./components/portal/ShareSheet";
import MagazineRequestCta from "./components/portal/MagazineRequestCta";
import SocialLoginModal from "./components/portal/SocialLoginModal";
import PortalSidebar from "./components/portal/PortalSidebar";
import {
  API_BASE_URL,
  apiOrigin,
  fetchGuideCards,
  fetchGuideDetail,
  matchesGuideQuery,
} from "./lib/guideCards";
import {
  adminAuthHeaders,
  clearAdminToken,
  consumeAdminReturn,
  readAdminToken,
  rememberAdminReturn,
  storeAdminToken,
} from "./lib/adminSession";
import { loadCommunityPosts, saveCommunityPosts } from "./lib/communityStore";
import { setMetaDescription } from "./lib/articleDocument";
import { applyPageHead } from "./lib/documentHead";
import { appLanguage } from "./i18n/i18n";
import { presentGuideCard } from "./lib/localeCopy";
import { cityHeading, destinationSlug } from "./lib/globeCities";
import { matchesKCulture } from "./lib/kculture";
import { matchesMagazineMatrix } from "./lib/magazineMatrix";
import {
  captureSessionFromUrl,
  clearUserSession,
  consumeAuthReturn,
  readUserSession,
  startSocialSignIn,
  authHeaders,
} from "./lib/session";
import { usePortalRoute } from "./lib/usePortalRoute";
import "./App.css";

function navActive(route) {
  if (route.name === "home") return "home";
  if (route.name === "destinations") return "destinations";
  if (route.name === "food") return "food";
  if (route.name === "community") return "community";
  if (route.name === "events") return "events";
  return "";
}

export default function App() {
  const { route, go, adminGate, leaveAdminGate } = usePortalRoute();
  const { t } = useTranslation();
  const language = appLanguage();
  const [adminSession, setAdminSession] = useState(() => Boolean(readAdminToken()));
  const [loginOpen, setLoginOpen] = useState(false);
  const adminMode = adminSession;
  const [destination, setDestination] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [guidesLoading, setGuidesLoading] = useState(true);
  const [guidesError, setGuidesError] = useState("");
  const [cards, setCards] = useState([]);
  const [reloadToken, setReloadToken] = useState(0);
  const [selectedGuide, setSelectedGuide] = useState(null);
  const [detailTab, setDetailTab] = useState("article");
  const [statusMessage, setStatusMessage] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [posts, setPosts] = useState(() => loadCommunityPosts());
  const [tripDuration, setTripDuration] = useState("all");
  const [dailyBudget, setDailyBudget] = useState("all");
  const [hotKorea, setHotKorea] = useState(false);
  const [kTheme, setKTheme] = useState("all");
  const [partnerShare, setPartnerShare] = useState(null);
  const [session, setSession] = useState(() => readUserSession());
  const [authOpen, setAuthOpen] = useState(false);
  const [authReason, setAuthReason] = useState("sign-in");
  const [authDismissed, setAuthDismissed] = useState("");
  const [savedIds, setSavedIds] = useState([]);

  useEffect(() => {
    let cancelled = false;
    setGuidesLoading(true);
    fetchGuideCards()
      .then((next) => {
        if (cancelled) return;
        setCards(next);
        setGuidesError("");
      })
      .catch((err) => {
        console.error("가이드 목록 로드 실패:", err);
        if (!cancelled) {
          setGuidesError("failed");
        }
      })
      .finally(() => {
        if (!cancelled) setGuidesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  useEffect(() => {
    if (route.name !== "article" || !route.guideId) {
      setSelectedGuide(null);
      return undefined;
    }
    let cancelled = false;
    setDetailTab("article");
    fetchGuideDetail(route.guideId)
      .then((data) => {
        if (!cancelled) setSelectedGuide(data);
      })
      .catch((err) => {
        console.error("가이드 본문 로드 실패:", err);
        if (!cancelled) setSelectedGuide(null);
      });
    return () => {
      cancelled = true;
    };
  }, [route.name, route.guideId, reloadToken]);

  useEffect(() => {
    if (!adminMode) setAdminOpen(false);
  }, [adminMode]);

  useEffect(() => {
    if (route.name !== "dashboard" || adminSession) return;
    rememberAdminReturn("/dashboard");
    go("/admin");
  }, [route.name, adminSession, go]);

  useEffect(() => {
    if (!(adminSession && adminGate)) return;
    const next = consumeAdminReturn();
    leaveAdminGate("replace");
    if (next === "/dashboard") go("/dashboard");
  }, [adminSession, adminGate, leaveAdminGate, go]);

  const endAdminSession = () => {
    clearAdminToken();
    setAdminSession(false);
    setAdminOpen(false);
  };

  const handleLogout = () => {
    endAdminSession();
    setLoginOpen(false);
    if (route.name === "dashboard") {
      go("/");
      return;
    }
    if (adminGate) leaveAdminGate("replace");
  };

  const handleLoginSuccess = (token) => {
    storeAdminToken(token);
    setAdminSession(true);
    setLoginOpen(false);
  };

  const requestAuth = (reason) => {
    setAuthReason(reason);
    setAuthOpen(true);
  };

  const closeAuth = () => {
    setAuthOpen(false);
    setAuthDismissed(route.name);
  };

  const toggleHotKorea = () => {
    setHotKorea((on) => {
      if (on) setKTheme("all");
      return !on;
    });
  };

  const selectKTheme = (id) => {
    if (route.name === "kculture") {
      go(id === "all" ? "/k-culture" : `/k-culture/${id}`);
      return;
    }
    setKTheme(id);
    if (id !== "all") setHotKorea(true);
  };

  const rememberPartner = useCallback((partner) => {
    setPartnerShare(partner);
  }, []);

  const handleUserLogout = () => {
    clearUserSession();
    setSession(null);
    setSavedIds([]);
    if (route.name === "wallet") go("/");
  };

  const openWallet = () => {
    if (session) {
      go("/wallet");
      return;
    }
    setAuthDismissed("");
    requestAuth("points");
  };

  const claimVoucher = async (partner) => {
    if (!session?.token) {
      setAuthDismissed("");
      requestAuth("voucher");
      return { ok: false, reason: "auth" };
    }
    const response = await fetch(`${apiOrigin()}/api/vouchers/claim`, {
      method: "POST",
      headers: authHeaders(session.token, { "Content-Type": "application/json" }),
      body: JSON.stringify({ merchant_id: partner.id }),
    });
    if (response.status === 401) {
      requestAuth("voucher");
      return { ok: false, reason: "auth" };
    }
    if (!response.ok) return { ok: false, reason: "failed" };
    go("/wallet");
    return { ok: true };
  };

  const handleSaveGuide = async () => {
    if (!session?.token || !route.guideId) {
      requestAuth("save");
      return;
    }
    const response = await fetch(`${apiOrigin()}/api/v1/wallet/saved`, {
      method: "POST",
      headers: authHeaders(session.token, { "Content-Type": "application/json" }),
      body: JSON.stringify({ guide_id: route.guideId }),
    });
    if (!response.ok) return;
    const saved = await response.json();
    if (Array.isArray(saved)) setSavedIds(saved);
  };

  const handleCloseLogin = () => {
    setLoginOpen(false);
    consumeAdminReturn();
    if (adminGate) leaveAdminGate("push");
  };

  const handleUnauthorized = () => {
    endAdminSession();
    setLoginOpen(true);
  };

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    setTripDuration("all");
    setDailyBudget("all");
  }, [route.city]);

  useEffect(() => {
    let cancelled = false;
    captureSessionFromUrl().then((next) => {
      if (cancelled || !next) return;
      setSession(next);
      const back = consumeAuthReturn();
      if (back) go(back);
    });
    return () => {
      cancelled = true;
    };
  }, [go]);

  useEffect(() => {
    if (!session?.token) {
      setSavedIds([]);
      return undefined;
    }
    let cancelled = false;
    fetch(`${apiOrigin()}/api/v1/wallet`, { headers: authHeaders(session.token) })
      .then(async (response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!cancelled && Array.isArray(data?.saved_guides)) setSavedIds(data.saved_guides);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [session?.token]);

  useEffect(() => {
    if (session) return;
    if (route.name !== "magazineRequest" && route.name !== "wallet") return;
    if (authDismissed === route.name) return;
    setAuthReason(route.name === "wallet" ? "points" : "report");
    setAuthOpen(true);
  }, [route.name, session, authDismissed]);

  useEffect(() => {
    const card = presentGuideCard(
      cards.find((item) => item.id === route.guideId),
      language,
    );
    const locale = language === "ko" ? "ko_KR" : "en_US";
    let title = t("meta.homeTitle");
    let description = t("meta.siteDescription");
    let type = "website";
    let image = "";
    if (route.name === "article") {
      title = t("meta.articleTitle", { title: card?.title || t("guide.articleTab") });
      description = card?.summary || t("meta.siteDescription");
      type = "article";
      image = card?.image || "";
    } else if (route.name === "kculture") {
      title = t("meta.kcultureTitle");
      description = t("meta.kcultureDescription");
      const theme = route.theme || "all";
      const cover = cards
        .map((item) => presentGuideCard(item, language))
        .find((item) => matchesKCulture(item, theme, true) && item.image);
      image = cover?.image || "";
    } else if (route.name === "partner") {
      const name = partnerShare?.name || t("events.partnersTitle");
      title = t("meta.partnerTitle", { name });
      description =
        partnerShare?.store_description ||
        partnerShare?.offered_benefit ||
        t("meta.partnerDescription", { city: partnerShare?.city || "" });
      image = partnerShare?.image_url || "";
    } else {
      const titles = {
        home: t("meta.homeTitle"),
        destinations: t("meta.destinationsTitle"),
        food: t("meta.foodTitle"),
        community: t("meta.communityTitle"),
        dashboard: t("meta.dashboardTitle"),
        privacy: t("meta.privacyTitle"),
        terms: t("meta.termsTitle"),
        about: t("meta.aboutTitle"),
        contact: t("meta.contactTitle"),
        magazineRequest: t("meta.magazineTitle"),
        events: t("meta.eventsTitle"),
        wallet: t("meta.walletTitle"),
        notFound: t("meta.notFoundTitle"),
      };
      const descriptions = {
        privacy: t("meta.privacyDescription"),
        terms: t("meta.termsDescription"),
        about: t("meta.aboutDescription"),
        contact: t("meta.contactDescription"),
        magazineRequest: t("meta.magazineDescription"),
        events: t("meta.eventsDescription"),
        wallet: t("meta.walletDescription"),
        notFound: t("meta.notFoundDescription"),
      };
      title = titles[route.name] || t("meta.homeTitle");
      description = descriptions[route.name] || t("meta.siteDescription");
      if (route.name === "city") {
        const cityName = cityHeading(route.city, cards);
        title = t("meta.cityTitle", { city: cityName });
        description = t("meta.cityDescription", { city: cityName });
      }
    }
    document.title = title;
    setMetaDescription(description);
    applyPageHead({
      title,
      description,
      pathname: window.location.pathname,
      type,
      locale,
      image,
    });
  }, [route, cards, language, t, partnerShare]);

  const localizedCards = useMemo(
    () => cards.map((card) => presentGuideCard(card, language)),
    [cards, language],
  );

  const spotlightOn = route.name === "kculture" || hotKorea;
  const spotlightTheme = route.name === "kculture" ? route.theme || "all" : kTheme;

  const visibleCards = useMemo(() => {
    return localizedCards.filter((card) => {
      if (route.name === "destinations" && route.category !== "all" && card.region !== route.category) {
        return false;
      }
      if (route.name === "food" && !card.hasFood) return false;
      if (route.name === "city" && destinationSlug(card.destination) !== route.city) return false;
      if (route.name === "city" && !matchesMagazineMatrix(card, tripDuration, dailyBudget)) return false;
      if (!matchesKCulture(card, spotlightTheme, spotlightOn)) return false;
      return matchesGuideQuery(card, query);
    });
  }, [localizedCards, route, query, tripDuration, dailyBudget, spotlightOn, spotlightTheme]);

  const handleSearch = (event) => {
    event.preventDefault();
    if (route.name !== "home" && route.name !== "community") {
      go("/");
    }
  };

  const openGuide = (card) => {
    go(`/guide/${encodeURIComponent(card.id)}`);
    window.scrollTo({ top: 0 });
  };

  const openCityGuides = (point) => {
    if (!point?.slug) return;
    setQuery("");
    go(`/city/${encodeURIComponent(point.slug)}`);
    window.scrollTo({ top: 0 });
  };

  const handleCreatePost = (draft) => {
    const post = {
      ...draft,
      id: globalThis.crypto?.randomUUID?.() || `post-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    setPosts((current) => {
      const next = [post, ...current];
      saveCommunityPosts(next);
      return next;
    });
    return post;
  };

  const handleApprove = async () => {
    if (!route.guideId || publishing) return;
    setPublishing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/guides/${encodeURIComponent(route.guideId)}/approve`, {
        method: "POST",
        headers: adminAuthHeaders(),
      });
      if (res.status === 401) {
        handleUnauthorized();
        throw new Error(t("status.approveFailedShort"));
      }
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || t("status.approveFailedShort"));
      }
      const data = await res.json();
      setSelectedGuide(data);
      setStatusMessage(t("status.approved"));
      setReloadToken((token) => token + 1);
    } catch (err) {
      setStatusMessage(t("status.approveFailed", { message: err.message }));
    } finally {
      setPublishing(false);
    }
  };

  const handleGenerate = async (event) => {
    event.preventDefault();
    if (!destination.trim()) return;

    setLoading(true);
    setStatusMessage("");

    try {
      const res = await fetch(`${API_BASE_URL}/generate-guide`, {
        method: "POST",
        headers: adminAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ destination, target_language: language }),
      });

      if (res.status === 401) {
        handleUnauthorized();
        throw new Error(t("status.generateFailed"));
      }
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || t("status.generateFailed"));
      }

      const data = await res.json();
      const qualityScore = data.qa_result?.quality_score;
      setStatusMessage(
        qualityScore == null ? t("status.ready") : t("status.readyScore", { score: qualityScore }),
      );
      const newFileName = `${destination.trim().toLowerCase().replace(/\s+/g, "_")}_guide.md`;
      setDestination("");
      setAdminOpen(false);
      setReloadToken((token) => token + 1);
      go(`/guide/${encodeURIComponent(newFileName)}`);
      window.scrollTo({ top: 0 });
    } catch (err) {
      setStatusMessage(t("status.failed", { message: err.message }));
    } finally {
      setLoading(false);
    }
  };

  const showCatalog = route.name === "home" || route.name === "destinations" || route.name === "food" || route.name === "city" || route.name === "kculture";
  const showSidebar = showCatalog || route.name === "article";
  const cityLabel = route.name === "city" ? cityHeading(route.city, localizedCards) : "";
  const matrixActive = route.name === "city" && (tripDuration !== "all" || dailyBudget !== "all");

  return (
    <div className="portal">
      <GlobalNav
        active={navActive(route)}
        region={route.name === "destinations" ? route.category : ""}
        query={query}
        onQueryChange={setQuery}
        onSearch={handleSearch}
        onNavigate={go}
        onOpenAdmin={() => setAdminOpen(true)}
        onOpenDashboard={() => go("/dashboard")}
        onLogout={handleLogout}
        adminMode={adminMode}
        dashboardActive={route.name === "dashboard"}
        userSession={session}
        onOpenLogin={() => requestAuth("sign-in")}
        onOpenWallet={openWallet}
        onUserLogout={handleUserLogout}
        hotCountry={hotKorea}
        onToggleHotCountry={toggleHotKorea}
      />

      {route.name === "home" ? (
        <>
          <HeroSearch
            query={query}
            onQueryChange={setQuery}
            onSearch={handleSearch}
            onPromote={() => go("/promote-store")}
          />
          <GlobeMap
            onOpenCity={openCityGuides}
            hotCountry={hotKorea}
            kTheme={kTheme}
            onToggleHot={toggleHotKorea}
            onTheme={selectKTheme}
          />
          <MagazineRequestCta
            onRequest={() => go("/magazine-request")}
            onPromote={() => go("/promote-store")}
          />
          <div className="ad-band">
            <AdSenseUnit slotId="hero-below" format="auto" />
          </div>
        </>
      ) : null}

      <main className="portal-main">
        {route.name === "dashboard" ? (
          adminSession ? (
            <Dashboard onUnauthorized={handleUnauthorized} />
          ) : (
            <p className="dash-note">{t("admin.redirecting")}</p>
          )
        ) : route.name === "community" ? (
          <CommunityBoard
            posts={posts}
            query={query}
            onCreate={handleCreatePost}
          />
        ) : route.name === "privacy" ? (
          <PrivacyPolicy />
        ) : route.name === "terms" ? (
          <TermsOfService />
        ) : route.name === "about" ? (
          <About />
        ) : route.name === "contact" ? (
          <Contact />
        ) : route.name === "magazineRequest" ? (
          <MagazineRequestPage onNavigate={go} />
        ) : route.name === "promoteStore" ? (
          <PromoteStorePage onNavigate={go} />
        ) : route.name === "partner" ? (
          <PartnerPage
            partnerId={route.partnerId}
            onNavigate={go}
            onClaim={claimVoucher}
            onLoaded={rememberPartner}
          />
        ) : route.name === "events" ? (
          <EventsPage
            onNavigate={go}
            onCheckPoints={openWallet}
            onClaimVoucher={claimVoucher}
            onIssueVoucher={() => {
              if (session) go("/wallet");
              else requestAuth("voucher");
            }}
          />
        ) : route.name === "wallet" ? (
          session ? (
            <WalletPage session={session} onNavigate={go} />
          ) : (
            <p className="dash-note">{t("wallet.signInRequired")}</p>
          )
        ) : route.name === "notFound" ? (
          <NotFound onNavigate={go} />
        ) : (
          <div className={showSidebar ? "portal-body" : "portal-body solo"}>
            <div className="portal-stream">
              {route.name === "destinations" || route.name === "food" ? (
                <CategoryIntro category={route.category} />
              ) : null}
              {route.name === "kculture" ? (
                <header className="kculture-page-head">
                  <p className="policy-kicker">{t("kculture.label")}</p>
                  <h1>{t("kculture.bannerTitle")}</h1>
                  <p>{t("kculture.bannerCopy")}</p>
                  <ShareSheet
                    title={t("meta.kcultureTitle")}
                    description={t("meta.kcultureDescription")}
                    pathname={route.theme && route.theme !== "all" ? `/k-culture/${route.theme}` : "/k-culture"}
                    image={visibleCards.find((card) => card.image)?.image || ""}
                  />
                  <KCultureBar
                    active
                    theme={route.theme || "all"}
                    onToggle={() => go("/")}
                    onTheme={selectKTheme}
                  />
                </header>
              ) : null}
              {hotKorea && route.name !== "home" && route.name !== "kculture" ? (
                <KCultureBar
                  active={hotKorea}
                  theme={kTheme}
                  onToggle={toggleHotKorea}
                  onTheme={selectKTheme}
                />
              ) : null}
              {route.name === "city" ? <CityIntro city={cityLabel} /> : null}
              {route.name === "city" ? (
                <MagazineFilters
                  duration={tripDuration}
                  budget={dailyBudget}
                  onDuration={setTripDuration}
                  onBudget={setDailyBudget}
                />
              ) : null}
              {route.name === "article" ? (
                <ArticleReader
                  guide={selectedGuide}
                  fileName={route.guideId}
                  tab={detailTab}
                  onTabChange={setDetailTab}
                  publishing={publishing}
                  onApprove={handleApprove}
                  onBack={() => go("/")}
                  onOpenCommunity={() => go("/community")}
                  onNavigate={go}
                  adminMode={adminMode}
                  saved={savedIds.includes(route.guideId)}
                  onSave={handleSaveGuide}
                  onClaimVoucher={claimVoucher}
                />
              ) : (
                <ArticleGrid
                  cards={visibleCards}
                  loading={guidesLoading}
                  error={guidesError ? t("catalog.loadError") : ""}
                  emptyLabel={matrixActive ? t("matrix.empty") : ""}
                  onOpen={openGuide}
                />
              )}
            </div>
            {showSidebar ? (
              <PortalSidebar
                cards={localizedCards}
                posts={posts}
                onPickDestination={(name) => {
                  setQuery(name);
                  go("/");
                }}
                onOpenLog={(post) => {
                  go("/community");
                  window.location.hash = post.id;
                }}
              />
            ) : null}
          </div>
        )}
      </main>

      <VisitorBadge />
      <Footer onNavigate={go} />

      {adminMode ? (
        <AdminDrawer
          open={adminOpen}
          onClose={() => setAdminOpen(false)}
          destination={destination}
          onDestinationChange={setDestination}
          loading={loading}
          statusMessage={statusMessage}
          onSubmit={handleGenerate}
        />
      ) : null}
      {!adminSession && (adminGate || loginOpen) ? (
        <AdminLogin onClose={handleCloseLogin} onSuccess={handleLoginSuccess} />
      ) : null}
      {authOpen ? (
        <SocialLoginModal
          reason={authReason}
          onClose={closeAuth}
          onGuest={closeAuth}
          onSelect={(provider) => startSocialSignIn(
            provider,
            authReason === "report" ? "/magazine-request" : "/wallet",
          )}
        />
      ) : null}
    </div>
  );
}
