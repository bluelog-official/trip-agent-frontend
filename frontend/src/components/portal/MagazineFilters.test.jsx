import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import i18n from "../../i18n/i18n";
import MagazineFilters from "./MagazineFilters";

describe("MagazineFilters", () => {
  it("switches duration and daily budget chips", async () => {
    await i18n.changeLanguage("en");
    const onDuration = vi.fn();
    const onBudget = vi.fn();
    render(
      <MagazineFilters duration="all" budget="all" onDuration={onDuration} onBudget={onBudget} />,
    );

    fireEvent.click(screen.getByRole("radio", { name: "3 Days" }));
    expect(onDuration).toHaveBeenCalledWith("3_days");

    fireEvent.click(screen.getByRole("radio", { name: "Under $50/day" }));
    expect(onBudget).toHaveBeenCalledWith("under_50");

    fireEvent.click(screen.getByRole("radio", { name: "Luxury" }));
    expect(onBudget).toHaveBeenCalledWith("luxury");
  });
});