import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PolicyNav from "./PolicyNav";
import i18n from "../i18n/i18n";

describe("PolicyNav", () => {
  afterEach(() => {
    cleanup();
  });

  it("opens About, Terms, and Privacy from the landing navigator", async () => {
    await i18n.changeLanguage("en");
    const onNavigate = vi.fn();
    render(<PolicyNav onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole("link", { name: "About" }));
    fireEvent.click(screen.getByRole("link", { name: "Terms of Service" }));
    fireEvent.click(screen.getByRole("link", { name: "Privacy Policy" }));

    expect(onNavigate.mock.calls.map((call) => call[0])).toEqual(["/about", "/terms", "/privacy"]);
  });
});
