import { canonicalHref, SITE_ORIGIN } from "./documentHead";

const KAKAO_SDK = "https://t1.kakaocdn.net/kakao_js_sdk/2.7.4/kakao.min.js";

export function absoluteShareUrl(pathname) {
  return canonicalHref(pathname || "/");
}

export function absoluteImageUrl(image) {
  const value = String(image || "").trim();
  if (!value) return "";
  if (value.startsWith("https://") || value.startsWith("http://")) return value;
  if (value.startsWith("/")) return `${SITE_ORIGIN}${value}`;
  return "";
}

export function xShareUrl({ title, url }) {
  const intent = new URL("https://twitter.com/intent/tweet");
  intent.searchParams.set("text", String(title || "BlueLog Trip"));
  intent.searchParams.set("url", String(url || SITE_ORIGIN));
  return intent.toString();
}

export function shareCaption({ title, description, url }) {
  return [title, description, url].map((part) => String(part || "").trim()).filter(Boolean).join("\n\n");
}

export function kakaoFeedObject({ title, description, imageUrl, url }) {
  const page = String(url || SITE_ORIGIN);
  const content = {
    title: String(title || "BlueLog Trip"),
    description: String(description || ""),
    link: { mobileWebUrl: page, webUrl: page },
  };
  const image = absoluteImageUrl(imageUrl);
  if (image.startsWith("https://")) content.imageUrl = image;
  return {
    objectType: "feed",
    content,
    buttons: [{ title: "BlueLog Trip", link: { mobileWebUrl: page, webUrl: page } }],
  };
}

function loadKakaoSdk() {
  if (typeof window === "undefined") return Promise.reject(new Error("kakao sdk needs a browser"));
  if (window.Kakao) return Promise.resolve(window.Kakao);
  return new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-kakao-sdk]");
    if (existing) {
      existing.addEventListener("load", () => resolve(window.Kakao), { once: true });
      existing.addEventListener("error", () => reject(new Error("kakao sdk failed")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = KAKAO_SDK;
    script.async = true;
    script.crossOrigin = "anonymous";
    script.dataset.kakaoSdk = "true";
    script.onload = () => resolve(window.Kakao);
    script.onerror = () => reject(new Error("kakao sdk failed"));
    document.head.appendChild(script);
  });
}

export async function shareToKakao({ title, description, imageUrl, url, javascriptKey }) {
  const key = String(javascriptKey || import.meta.env.VITE_KAKAO_JS_KEY || "").trim();
  const page = String(url || SITE_ORIGIN);
  if (!key) return "unconfigured";
  const Kakao = await loadKakaoSdk();
  if (!Kakao?.Share) throw new Error("kakao share missing");
  if (!Kakao.isInitialized()) Kakao.init(key);
  const image = absoluteImageUrl(imageUrl);
  if (image.startsWith("https://")) {
    Kakao.Share.sendDefault(kakaoFeedObject({ title, description, imageUrl: image, url: page }));
  } else {
    Kakao.Share.sendScrap({ requestUrl: page });
  }
  return "sdk";
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("image failed"));
    img.src = src;
  });
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight, maxLines) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  let line = "";
  let drawn = 0;
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width > maxWidth && line) {
      ctx.fillText(line, x, y);
      drawn += 1;
      y += lineHeight;
      line = word;
      if (drawn >= maxLines) return y;
    } else {
      line = next;
    }
  }
  if (line && drawn < maxLines) ctx.fillText(line, x, y);
}

export async function renderShareCard({ title, description, imageUrl, brand = "BlueLog Trip" }) {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 630;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas unavailable");
  ctx.fillStyle = "#134e4a";
  ctx.fillRect(0, 0, 1200, 630);
  ctx.fillStyle = "#f6f1e8";
  ctx.fillRect(36, 36, 1128, 558);
  let textX = 84;
  const image = absoluteImageUrl(imageUrl);
  if (image.startsWith("https://") || image.startsWith("http://")) {
    try {
      const picture = await loadImage(image);
      ctx.drawImage(picture, 72, 78, 460, 460);
      textX = 572;
    } catch {
      textX = 84;
    }
  }
  ctx.fillStyle = "#134e4a";
  ctx.font = "700 48px Georgia, serif";
  wrapText(ctx, title || brand, textX, 180, 1120 - textX, 58, 3);
  ctx.fillStyle = "#44403c";
  ctx.font = "28px Georgia, serif";
  wrapText(ctx, description || "", textX, 380, 1120 - textX, 38, 3);
  ctx.fillStyle = "#134e4a";
  ctx.font = "700 24px Georgia, serif";
  ctx.fillText(brand, 84, 548);
  return canvas.toDataURL("image/png");
}

export function downloadDataUrl(dataUrl, filename) {
  const link = document.createElement("a");
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}
