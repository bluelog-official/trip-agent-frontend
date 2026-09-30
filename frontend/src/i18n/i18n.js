import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import ko from "./locales/ko.json";
import ja from "./locales/ja.json";
import zhCN from "./locales/zh-CN.json";
import zhTW from "./locales/zh-TW.json";
import vi from "./locales/vi.json";
import th from "./locales/th.json";
import es from "./locales/es.json";
import fr from "./locales/fr.json";

export const APP_LANG_KEY = "app_lang";

export const APP_LANGUAGES = [
  { code: "en", native: "English" },
  { code: "ko", native: "한국어" },
  { code: "ja", native: "日本語" },
  { code: "zh-CN", native: "简体中文" },
  { code: "zh-TW", native: "繁體中文" },
  { code: "vi", native: "Tiếng Việt" },
  { code: "th", native: "ไทย" },
  { code: "es", native: "Español" },
  { code: "fr", native: "Français" },
];

const SUPPORTED = APP_LANGUAGES.map((item) => item.code);

export function normalizeAppLanguage(language) {
  const value = String(language || "").trim().toLowerCase();
  if (value === "zh-cn" || value === "zh-hans" || value === "zh") return "zh-CN";
  if (value === "zh-tw" || value === "zh-hant") return "zh-TW";
  if (value === "ko" || value.startsWith("ko")) return "ko";
  if (value === "ja" || value.startsWith("ja")) return "ja";
  if (value === "vi" || value.startsWith("vi")) return "vi";
  if (value === "th" || value.startsWith("th")) return "th";
  if (value === "es" || value.startsWith("es")) return "es";
  if (value === "fr" || value.startsWith("fr")) return "fr";
  if (value === "en" || value.startsWith("en")) return "en";
  return "en";
}

export function readAppLanguage(storage = globalThis.localStorage) {
  try {
    return normalizeAppLanguage(storage?.getItem(APP_LANG_KEY));
  } catch {
    return "en";
  }
}

export function writeAppLanguage(language, storage = globalThis.localStorage) {
  const next = normalizeAppLanguage(language);
  try {
    storage?.setItem(APP_LANG_KEY, next);
  } catch {
    /* private mode or a blocked storage API */
  }
  return next;
}

if (!i18n.isInitialized) {
  const initial = readAppLanguage();
  i18n.use(initReactI18next).init({
    resources: {
      en: { translation: en },
      ko: { translation: ko },
      ja: { translation: ja },
      "zh-CN": { translation: zhCN },
      "zh-TW": { translation: zhTW },
      vi: { translation: vi },
      th: { translation: th },
      es: { translation: es },
      fr: { translation: fr },
    },
    lng: initial,
    fallbackLng: "en",
    supportedLngs: SUPPORTED,
    interpolation: { escapeValue: false },
    returnNull: false,
    react: { useSuspense: false },
  });
}

i18n.on("languageChanged", (language) => {
  const next = writeAppLanguage(language);
  if (typeof document !== "undefined") {
    document.documentElement.lang = next;
  }
});

if (typeof document !== "undefined") {
  document.documentElement.lang = normalizeAppLanguage(i18n.language);
}

export function appLanguage() {
  return normalizeAppLanguage(i18n.resolvedLanguage || i18n.language);
}

export default i18n;
