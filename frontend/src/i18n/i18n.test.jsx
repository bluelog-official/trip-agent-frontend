import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import About from "../pages/About";
import Contact from "../pages/Contact";
import PrivacyPolicy from "../pages/PrivacyPolicy";
import TermsOfService from "../pages/TermsOfService";
import Footer from "../components/Footer";
import VisitorBadge from "../components/VisitorBadge";
import ArticleGrid from "../components/portal/ArticleGrid";
import GlobalNav from "../components/portal/GlobalNav";
import HeroSearch from "../components/portal/HeroSearch";
import NotFound from "../pages/NotFound";
import en from "./locales/en.json";
import ko from "./locales/ko.json";
import i18n, { APP_LANG_KEY, normalizeAppLanguage, readAppLanguage, writeAppLanguage } from "./i18n";

const HANGUL = /[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3]/;
const BRANDS = [
  "BlueLog Trip",
  "BlueLog Desk",
  "BlueLog Editorial",
  "BlueLog",
  "Google AdSense",
  "Google",
  "AdSense",
  "DART",
  "Reddit",
  "Quora",
  "Pinterest",
  "bluelog.official@gmail.com",
];

function flatten(value, prefix = "", out = {}) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    for (const [key, child] of Object.entries(value)) {
      flatten(child, prefix ? `${prefix}.${key}` : key, out);
    }
    return out;
  }
  out[prefix] = value;
  return out;
}

function visibleCopy(text) {
  return String(text || "")
    .replace(/\{\{[^}]+\}\}/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/[\w.+-]+@[\w.-]+/g, " ")
    .replace(new RegExp(BRANDS.map((brand) => brand.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g"), " ");
}

describe("app language storage", () => {
  it("normalizes only en and ko", () => {
    expect(normalizeAppLanguage("ko")).toBe("ko");
    expect(normalizeAppLanguage("ko-KR")).toBe("ko");
    expect(normalizeAppLanguage("en")).toBe("en");
    expect(normalizeAppLanguage("english")).toBe("en");
    expect(normalizeAppLanguage("")).toBe("en");
  });

  it("persists the selected language as app_lang", () => {
    const storage = new Map();
    const memory = {
      getItem: (key) => (storage.has(key) ? storage.get(key) : null),
      setItem: (key, value) => storage.set(key, value),
    };
    expect(readAppLanguage(memory)).toBe("en");
    expect(writeAppLanguage("ko", memory)).toBe("ko");
    expect(memory.getItem(APP_LANG_KEY)).toBe("ko");
    expect(readAppLanguage(memory)).toBe("ko");
  });
});

describe("translation catalogs", () => {
  const english = flatten(en);
  const korean = flatten(ko);

  it("uses the same keys in English and Korean", () => {
    expect(Object.keys(korean).sort()).toEqual(Object.keys(english).sort());
  });

  it("keeps English copy free of Hangul", () => {
    for (const [key, value] of Object.entries(english)) {
      expect(HANGUL.test(String(value)), key).toBe(false);
    }
  });

  it("keeps Korean copy free of English sentences", () => {
    const leftovers = [];
    for (const [key, value] of Object.entries(korean)) {
      const words = visibleCopy(value).match(/[A-Za-z]{3,}/g) || [];
      if (words.length) leftovers.push(`${key}: ${words.join(", ")}`);
    }
    expect(leftovers).toEqual([]);
  });
});

describe("language switcher", () => {
  it("switches the whole chrome between English and Korean", async () => {
    await i18n.changeLanguage("en");
    const view = render(
      <div>
        <GlobalNav
          active="home"
          region=""
          query=""
          onQueryChange={() => {}}
          onSearch={(event) => event.preventDefault()}
          onNavigate={() => {}}
        />
        <HeroSearch query="" onQueryChange={() => {}} onSearch={(event) => event.preventDefault()} />
        <ArticleGrid
          cards={[{
            id: "paris",
            title: "Paris Trip Guide",
            summary: "A walk through the center.",
            tags: ["Europe", "Paris"],
            image: "",
            approved: true,
          }]}
          loading={false}
          error=""
          onOpen={() => {}}
          loadVotes={false}
        />
        <About />
        <PrivacyPolicy />
        <TermsOfService />
        <Contact />
        <NotFound onNavigate={() => {}} />
        <Footer onNavigate={() => {}} />
        <VisitorBadge />
      </div>,
    );

    expect(screen.getByRole("option", { name: "English" }).selected).toBe(true);
    expect(screen.getByRole("heading", { name: "Privacy Policy" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Terms of Service" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "About BlueLog Trip" })).toBeTruthy();
    expect(screen.getByText("Verified Guide")).toBeTruthy();
    expect(HANGUL.test(view.container.textContent)).toBe(false);

    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ko" } });
    await i18n.changeLanguage("ko");

    expect(localStorage.getItem(APP_LANG_KEY)).toBe("ko");
    expect(document.documentElement.lang).toBe("ko");
    expect(screen.getByRole("option", { name: "한국어" }).selected).toBe(true);
    expect(screen.getByRole("heading", { name: "개인정보 처리방침" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "이용약관" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "BlueLog Trip 소개" })).toBeTruthy();
    expect(screen.getByText("검증된 가이드")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Privacy Policy" })).toBeNull();
    expect(screen.queryByText("Verified Guide")).toBeNull();
    expect(screen.queryByText("Terms of Service")).toBeNull();

    const chrome = view.container.cloneNode(true);
    chrome.querySelectorAll(".story-card").forEach((node) => node.remove());
    const leftovers = visibleCopy(chrome.textContent).match(/[A-Za-z]{4,}/g) || [];
    expect(leftovers).toEqual([]);

    fireEvent.change(screen.getByLabelText("언어"), { target: { value: "en" } });
    await i18n.changeLanguage("en");
    expect(localStorage.getItem(APP_LANG_KEY)).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByRole("heading", { name: "Privacy Policy" })).toBeTruthy();
    expect(HANGUL.test(view.container.textContent)).toBe(false);
  });
});
