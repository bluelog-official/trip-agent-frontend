import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n/i18n";
import WalletPage from "./WalletPage";

describe("WalletPage", () => {
  afterEach(() => {
    cleanup();
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

  it("opens a voucher code dialog from the wallet", async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          email: "hana@example.com",
          name: "Hana",
          auth_provider: "google",
          points_balance: 50,
          logs: [],
          reports: [],
          saved_guides: [],
          vouchers: [{
            id: 3,
            merchant_name: "Hanok Noodle",
            offered_benefit: "10% off",
            voucher_code: "ABCD2345",
            qr_svg: "<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>",
            status: "ISSUED",
          }],
        }),
      })),
    );
    render(<WalletPage session={{ token: "abc.def", email: "hana@example.com" }} />);
    fireEvent.click(await screen.findByRole("tab", { name: "My vouchers" }));
    fireEvent.click(screen.getByRole("button", { name: "Show code" }));
    expect(screen.getByRole("dialog", { name: "Show this screen at the shop" })).toBeTruthy();
    expect(screen.getByText("ABCD2345")).toBeTruthy();
  });
});