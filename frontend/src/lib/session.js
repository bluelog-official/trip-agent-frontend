import { apiOrigin } from "./guideCards";

const SESSION_KEY = "bluelog_user_session";
const RETURN_KEY = "bluelog_auth_return";

export function readUserSession(storage = globalThis.localStorage) {
  try {
    const raw = storage?.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.token || !parsed?.email) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function storeUserSession(session, storage = globalThis.localStorage) {
  const next = {
    token: String(session?.token || ""),
    email: String(session?.email || ""),
    name: String(session?.name || ""),
    provider: String(session?.auth_provider || session?.provider || ""),
    userId: Number(session?.user_id || session?.userId || 0),
    pointsBalance: Number(session?.points_balance || session?.pointsBalance || 0),
  };
  if (!next.token || !next.email) return null;
  try {
    storage?.setItem(SESSION_KEY, JSON.stringify(next));
  } catch {
    /* private mode */
  }
  return next;
}

export function clearUserSession(storage = globalThis.localStorage) {
  try {
    storage?.removeItem(SESSION_KEY);
  } catch {
    /* private mode */
  }
}

export function rememberAuthReturn(path, storage = globalThis.sessionStorage) {
  try {
    storage?.setItem(RETURN_KEY, path || "/wallet");
  } catch {
    /* private mode */
  }
}

export function consumeAuthReturn(storage = globalThis.sessionStorage) {
  try {
    const value = storage?.getItem(RETURN_KEY) || "";
    storage?.removeItem(RETURN_KEY);
    return value.startsWith("/") ? value : "";
  } catch {
    return "";
  }
}

export function authHeaders(token, extra = {}) {
  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  };
}

export async function fetchAuthProviders() {
  const response = await fetch(`${apiOrigin()}/api/auth/providers`);
  if (!response.ok) return [];
  const data = await response.json();
  return Array.isArray(data?.providers) ? data.providers : [];
}

export async function startDevSignIn() {
  const response = await fetch(`${apiOrigin()}/api/auth/dev-signin`, { method: "POST" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) {
    const error = new Error(data.detail || "sign-in");
    error.status = response.status;
    throw error;
  }
  return storeUserSession({ ...data, token: data.access_token });
}

export async function startSocialSignIn(provider, returnPath) {
  if (returnPath) rememberAuthReturn(returnPath);
  const response = await fetch(`${apiOrigin()}/api/auth/signin/${encodeURIComponent(provider)}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.authorize_url) {
    const error = new Error(data.detail || "sign-in");
    error.status = response.status;
    throw error;
  }
  window.location.assign(data.authorize_url);
}

export async function captureSessionFromUrl(storage = globalThis.localStorage) {
  const url = new URL(window.location.href);
  const fromQuery = url.searchParams.get("session");
  const fromHash = new URLSearchParams(url.hash.replace(/^#/, "")).get("session");
  const token = fromHash || fromQuery;
  if (!token) return null;
  url.searchParams.delete("session");
  url.hash = "";
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  const response = await fetch(`${apiOrigin()}/api/auth/session`, {
    headers: authHeaders(token),
  });
  if (!response.ok) return null;
  const profile = await response.json();
  return storeUserSession({ ...profile, token }, storage);
}
