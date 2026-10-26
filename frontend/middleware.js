import { canonicalPath, SITE_ORIGIN } from "./src/lib/canonicalPath.js";

const SOCIAL_BOT = /facebookexternalhit|Facebot|Twitterbot|Kakao|kakaotalk|Instagram|Slackbot|TelegramBot|WhatsApp|LinkedInBot|Pinterest|Discordbot/i;

export const config = {
  matcher: [
    "/((?!assets/|favicon\\.svg|robots\\.txt|ads\\.txt|sitemap\\.xml|.*\\.(?:js|css|png|jpg|jpeg|gif|svg|webp|ico|woff2?|map|txt|xml|webmanifest)$).*)",
  ],
};

function redirectTarget(request) {
  const current = new URL(request.url);
  const nextPath = canonicalPath(current.pathname);
  const host = current.hostname.toLowerCase();
  const apex = host === "bluelogtrip.com";
  if (nextPath === current.pathname && !apex) return null;
  const dest = new URL(current.href);
  dest.pathname = nextPath;
  if (apex) {
    dest.protocol = "https:";
    dest.hostname = "www.bluelogtrip.com";
    dest.port = "";
  }
  return dest;
}

export default async function middleware(request) {
  if (request.method === "GET" || request.method === "HEAD") {
    const dest = redirectTarget(request);
    if (dest && dest.href !== new URL(request.url).href) {
      return Response.redirect(dest, 301);
    }
  }
  const agent = request.headers.get("user-agent") || "";
  if (!SOCIAL_BOT.test(agent)) return undefined;
  const current = new URL(request.url);
  const api = process.env.OG_API_ORIGIN || "https://bluelog-trip-backend.onrender.com";
  const og = new URL("/api/v1/opengraph", api);
  og.searchParams.set("path", canonicalPath(current.pathname));
  og.searchParams.set("site", SITE_ORIGIN);
  try {
    const response = await fetch(og, { headers: { accept: "text/html" } });
    if (!response.ok) return undefined;
    const html = await response.text();
    return new Response(html, {
      status: 200,
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "public, max-age=300",
      },
    });
  } catch {
    return undefined;
  }
}
