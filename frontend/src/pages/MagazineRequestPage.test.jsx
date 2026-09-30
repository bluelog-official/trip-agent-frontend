import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n/i18n";
import MagazineRequestPage from "./MagazineRequestPage";

const REVIEW = "직접 다녀온 골목 안쪽 국수집은 줄이 짧고 국물이 진해서 아침 첫 끼로 다시 가고 싶다. 정말 좋다.";

describe("MagazineRequestPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("blocks a short review and posts a public request", async () => {
    await i18n.changeLanguage("en");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ status: "PENDING_REVIEW" }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(<MagazineRequestPage onNavigate={() => {}} />);

    fireEvent.click(screen.getByRole("radio", { name: "Nickname or name" }));
    expect(screen.getByRole("radio", { name: "Nickname or name" }).checked).toBe(true);
    fireEvent.change(screen.getByRole("textbox", { name: /^Nickname/ }), { target: { value: "Hana" } });
    fireEvent.change(screen.getByRole("textbox", { name: /^Email/ }), { target: { value: "hana@example.com" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Country" }), { target: { value: "Japan" } });
    fireEvent.change(screen.getByRole("textbox", { name: "City" }), { target: { value: "Tokyo" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Recommended place" }), { target: { value: "Yanaka" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Review" }), { target: { value: "too short" } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    expect(await screen.findByText("Write at least 50 characters.")).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();

    fireEvent.change(screen.getByRole("textbox", { name: "Review" }), { target: { value: REVIEW } });
    fireEvent.change(screen.getByRole("textbox", { name: "Photo URL" }), { target: { value: "https://example.com/a.jpg" } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/magazine-requests$/);
    expect(JSON.parse(options.body)).toMatchObject({
      author_type: "public",
      nickname: "Hana",
      email: "hana@example.com",
      country: "Japan",
      city: "Tokyo",
      place: "Yanaka",
      review: REVIEW,
      photo_url: "https://example.com/a.jpg",
    });
    expect((await screen.findByRole("status")).textContent).toMatch(/Request received/);
  });
});
