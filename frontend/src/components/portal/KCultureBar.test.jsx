import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import i18n from "../../i18n/i18n";
import KCultureBar from "./KCultureBar";

describe("KCultureBar", () => {
  it("toggles the Korea spotlight and picks a theme", async () => {
    await i18n.changeLanguage("en");
    const onToggle = vi.fn();
    const onTheme = vi.fn();
    render(<KCultureBar active={false} theme="all" onToggle={onToggle} onTheme={onTheme} />);

    fireEvent.click(screen.getByRole("button", { name: "Hot Spot: Korea (K-Culture Guide)" }));
    expect(onToggle).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("radio", { name: "K-Food" }));
    expect(onTheme).toHaveBeenCalledWith("k-food");
    fireEvent.click(screen.getByRole("radio", { name: "K-Pop & Culture" }));
    expect(onTheme).toHaveBeenCalledWith("k-pop");
  });
});
