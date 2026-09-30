import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n/i18n";
import SocialLoginModal from "./SocialLoginModal";

describe("SocialLoginModal", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts a configured provider and lets a report continue as guest", async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          providers: [
            { id: "google", name: "Google", configured: true },
            { id: "apple", name: "Apple", configured: false },
            { id: "kakao", name: "Kakao", configured: true },
          ],
        }),
      })),
    );
    const onSelect = vi.fn();
    const onGuest = vi.fn();
    render(
      <SocialLoginModal reason="report" onClose={() => {}} onSelect={onSelect} onGuest={onGuest} />,
    );

    const google = await screen.findByRole("button", { name: /Continue with Google/ });
    await waitFor(() => expect(google.disabled).toBe(false));
    fireEvent.click(google);
    expect(onSelect).toHaveBeenCalledWith("google");

    const apple = screen.getByRole("button", { name: /Continue with Apple/ });
    expect(apple.disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Continue as guest" }));
    expect(onGuest).toHaveBeenCalledTimes(1);
  });
});
