import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import i18n from "../../i18n/i18n";
import ShareSheet from "./ShareSheet";

describe("ShareSheet", () => {
  it("opens a share dialog with Kakao, copy, X, and an image card", async () => {
    await i18n.changeLanguage("en");
    render(
      <ShareSheet
        title="Kyoto walks"
        description="A local Kyoto guide."
        pathname="/guide/kyoto_guide.md"
        image="https://images.example/kyoto.jpg"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Share" }));
    const dialog = screen.getByRole("dialog", { name: "Share this page" });
    expect(dialog).toBeTruthy();
    expect(screen.getByRole("button", { name: "KakaoTalk" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Copy link" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "X" }).getAttribute("href")).toContain("twitter.com/intent/tweet");
    expect(screen.getByRole("button", { name: "Instagram card" })).toBeTruthy();
    expect(screen.getByText("Kyoto walks")).toBeTruthy();
  });
});
