const SOCIAL_BOT = /facebookexternalhit|Facebot|Twitterbot|Kakao|kakaotalk|Instagram|Slackbot|TelegramBot|WhatsApp|LinkedInBot|Pinterest|Discordbot/i;

export const config = {
  matcher: ["/guide/:path*", "/guides/:path*", "/k-culture", "/k-culture/:path*", "/partners/:path*", "/events"],
};

export default async function middleware(request) {
  const agent = request.headers.get("user-agent") || "";
  if (!SOCIAL_BOT.test(agent)) return undefined;
  const current = new URL(request.url);
  const api = process.env.OG_API_ORIGIN || "https://bluelog-trip-backend.onrender.com";
  const og = new URL("/api/v1/opengraph", api);
  og.searchParams.set("path", current.pathname);
  og.searchParams.set("site", "https://bluelogtrip.com");
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
