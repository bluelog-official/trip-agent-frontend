import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import VoteButton from "./VoteButton";
import i18n from "../../i18n/i18n";

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe("VoteButton", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("raises the count before the server answers, then keeps the saved vote", async () => {
    await i18n.changeLanguage("en");
    let release = () => {};
    const pending = new Promise((resolve) => {
      release = () => resolve(jsonResponse({
        article_id: "paris_guide.md",
        vote_count: 3,
        voted: true,
        created: true,
      }, 201));
    });
    const fetchMock = vi.fn((url, options) => {
      if (options?.method === "POST") return pending;
      return Promise.resolve(jsonResponse({
        votes: [{ article_id: "paris_guide.md", vote_count: 2, voted: false }],
      }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<VoteButton articleId="paris_guide.md" />);

    expect(await screen.findByText("2")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Vote" }));
    expect(screen.getByRole("button", { name: "Voted" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("3")).toBeTruthy();

    release();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Voted" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("tells the reader when this IP already voted", async () => {
    await i18n.changeLanguage("en");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<VoteButton articleId="paris_guide.md" count={2} voted managed />);

    fireEvent.click(screen.getByRole("button", { name: "Voted" }));
    expect((await screen.findByRole("status")).textContent).toContain("You already voted on this guide.");
    expect(screen.getByText("2")).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rolls the optimistic count back when the server rejects a duplicate", async () => {
    await i18n.changeLanguage("en");
    let release = () => {};
    const pending = new Promise((resolve) => {
      release = () => resolve(jsonResponse({
        article_id: "paris_guide.md",
        vote_count: 4,
        voted: true,
        created: false,
        detail: "Already voted from this IP",
      }, 409));
    });
    vi.stubGlobal("fetch", vi.fn(() => pending));
    render(<VoteButton articleId="paris_guide.md" count={4} voted={false} managed />);

    fireEvent.click(screen.getByRole("button", { name: "Vote" }));
    expect(screen.getByText("5")).toBeTruthy();
    release();
    expect((await screen.findByRole("status")).textContent).toContain("You already voted on this guide.");
    await waitFor(() => expect(screen.getByText("4")).toBeTruthy());
    expect(screen.getByRole("button", { name: "Voted" }).getAttribute("aria-pressed")).toBe("true");
  });
});
