import { useCallback, useEffect, useState } from "react";

export function normalizePath(pathname) {
  const path = pathname || "/";
  if (path === "/") return "/";
  return path.replace(/\/+$/, "") || "/";
}

export function isAdminPath(pathname) {
  const path = normalizePath(pathname);
  return path === "/admin" || path.startsWith("/admin/");
}

export function isAdminRequest(pathname, _search) {
  return isAdminPath(pathname);
}

function contentPath(pathname) {
  const path = normalizePath(pathname);
  if (path === "/admin") return "/";
  if (path.startsWith("/admin/")) return path.slice("/admin".length) || "/";
  return path;
}

export function parseRoute(pathname) {
  const path = pathname || "/";
  const guideMatch = path.match(/^\/guides?\/(.+)$/);
  if (guideMatch) {
    return {
      name: "article",
      category: "",
      guideId: decodeURIComponent(guideMatch[1]),
    };
  }
  if (path === "/destinations" || path.startsWith("/destinations/")) {
    const region = path.split("/")[2] || "all";
    const known = ["asia", "europe", "americas"];
    return {
      name: "destinations",
      category: known.includes(region) ? region : "all",
      guideId: "",
    };
  }
  if (path === "/dashboard") {
    return { name: "dashboard", category: "", guideId: "" };
  }
  if (path.startsWith("/city/")) {
    let slug = "";
    try {
      slug = decodeURIComponent(path.slice("/city/".length)).split("/")[0].trim().toLowerCase();
    } catch {
      slug = "";
    }
    if (!/^[a-z0-9_]+$/.test(slug)) {
      return { name: "notFound", category: "", guideId: "" };
    }
    return { name: "city", category: "city", guideId: "", city: slug };
  }
  if (path === "/local-food") {
    return { name: "food", category: "food", guideId: "" };
  }
  if (path === "/community") {
    return { name: "community", category: "community", guideId: "" };
  }
  if (path === "/") {
    return { name: "home", category: "home", guideId: "" };
  }
  const staticPages = {
    "/privacy": "privacy",
    "/terms": "terms",
    "/about": "about",
    "/contact": "contact",
  };
  if (staticPages[path]) {
    return { name: staticPages[path], category: "", guideId: "" };
  }
  return { name: "notFound", category: "", guideId: "" };
}

function stripLegacyAdminQuery() {
  const url = new URL(window.location.href);
  if (!url.searchParams.has("admin")) return;
  url.searchParams.delete("admin");
  const next = `${url.pathname}${url.search}${url.hash}`;
  window.history.replaceState(window.history.state, "", next);
}

function readLocation() {
  const pathname = window.location.pathname;
  return {
    route: parseRoute(contentPath(pathname)),
    adminGate: isAdminPath(pathname),
  };
}

export function usePortalRoute() {
  const initial = readLocation();
  const [route, setRoute] = useState(initial.route);
  const [adminGate, setAdminGate] = useState(initial.adminGate);

  useEffect(() => {
    stripLegacyAdminQuery();
    const sync = () => {
      stripLegacyAdminQuery();
      const next = readLocation();
      setRoute(next.route);
      setAdminGate(next.adminGate);
    };
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const go = useCallback((path) => {
    const raw = path.startsWith("/") ? path : `/${path}`;
    const url = new URL(raw, window.location.origin);
    url.searchParams.delete("admin");
    const next = `${url.pathname}${url.search}${url.hash}`;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (current !== next) {
      window.history.pushState({ path: next }, "", next);
    }
    setRoute(parseRoute(contentPath(url.pathname)));
    setAdminGate(isAdminPath(url.pathname));
  }, []);

  const leaveAdminGate = useCallback((mode = "push") => {
    const url = new URL(window.location.href);
    url.pathname = contentPath(url.pathname);
    url.searchParams.delete("admin");
    const next = `${url.pathname}${url.search}${url.hash}`;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (current !== next) {
      const state = { path: next };
      if (mode === "replace") window.history.replaceState(state, "", next);
      else window.history.pushState(state, "", next);
    }
    setRoute(parseRoute(url.pathname));
    setAdminGate(false);
  }, []);

  return { route, go, adminGate, leaveAdminGate };
}
