import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MagazineRequestCta from "./MagazineRequestCta";

describe("MagazineRequestCta", () => {
  it("shows the share slogan and opens the request form", () => {
    const onRequest = vi.fn();
    render(<MagazineRequestCta onRequest={onRequest} />);
    expect(
      screen.getByRole("heading", {
        name: "사용자 여러분의 Trip 경험을 공유해주세요! (Share Your Experience)",
      }),
    ).toBeTruthy();
    expect(
      screen.getByText(
        "직접 다녀온 숨은 맛집과 감성 여행지를 제보해 주시면, 검토 후 공식 매거진으로 발행해 드립니다.",
      ),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "매거진 발행 요청하기" }));
    expect(onRequest).toHaveBeenCalledTimes(1);
  });
});
