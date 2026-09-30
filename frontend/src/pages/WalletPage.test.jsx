import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n/i18n";
import WalletPage from "./WalletPage";

describe("WalletPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the point balance, a report state, and the ledger link", async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          email: "hana@example.com",
          name: "Hana",
          auth_provider: "google",
          points_balance: 150,
          logs: [{ id: 1, amount: 100, reason: "MAGAZINE_PUBLISHED", article_id: "a.md", created_at: "" }],
          reports: [{
            id: 7,
            place: "Ikseon-dong",
            city: "Seoul",
            guest_email: "hana@example.com",
            publish_state: "VERIFIED",
            xrpl_url: "https://livenet.xrpl.org/transactions/ABCDEF",
          }],
          saved_guides: [],
        }),
      })),
    );
    render(<WalletPage session={{ token: "abc.def", email: "hana@example.com" }} onNavigate={() => {}} />);
    expect(await screen.findByText("150")).toBeTruthy();
    expect(screen.getByText("Magazine published")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "My reports" }));
    expect(screen.getByText("Verified")).toBeTruthy();
    expect(screen.getByRole("link", { name: "View ledger transaction" }).getAttribute("href")).toBe(
      "https://livenet.xrpl.org/transactions/ABCDEF",
    );
  });
});