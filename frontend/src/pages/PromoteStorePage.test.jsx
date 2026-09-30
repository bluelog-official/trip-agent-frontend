import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n/i18n";
import PromoteStorePage from "./PromoteStorePage";

describe("PromoteStorePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts a partner application", async () => {
    await i18n.changeLanguage("en");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ status: "PENDING_APPROVAL" }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(<PromoteStorePage onNavigate={() => {}} />);

    fireEvent.change(screen.getByRole("textbox", { name: "Store name" }), { target: { value: "Hanok Noodle" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Category" }), { target: { value: "Stay" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Address" }), { target: { value: "Seoul, Ikseon-dong" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Contact email" }), { target: { value: "shop@example.com" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Phone" }), { target: { value: "010-0000-0000" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Store description" }), {
      target: { value: "A small noodle counter with a morning queue." },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Photo URLs/ }), {
      target: { value: "https://example.com/shop.jpg" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Guest benefit" }), { target: { value: "10% off a bowl" } });
    fireEvent.click(screen.getByRole("button", { name: "Send application" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/partners$/);
    expect(JSON.parse(options.body)).toMatchObject({
      store_name: "Hanok Noodle",
      category: "Stay",
      address: "Seoul, Ikseon-dong",
      contact_email: "shop@example.com",
      offered_benefit: "10% off a bowl",
    });
    expect((await screen.findByRole("status")).textContent).toMatch(/Application received/);
  });
});