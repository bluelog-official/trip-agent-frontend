import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard, { applyGuideApproval } from "./Dashboard";
import i18n from "../i18n/i18n";

const STATS = {
  total_guides_count: 3,
  approved_count: 1,
  pending_count: 2,
  daily_batch_status: { last_run: "2026-09-26 09:00", status: "SUCCESS", target_city: "Tokyo" },
  agent_health: {
    research_agent: "OK",
    writer_agent: "OK",
    qa_agent: "OK",
    syndication_agent: "OK",
  },
  recent_guides: [
    {
      filename: "busan_guide.md",
      city: "Busan",
      qa_score: 90,
      created_at: "2026-09-26 10:00",
      is_approved: false,
    },
  ],
  marketing_alerts: [],
};

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

function metric(name) {
  return document.querySelector(`[data-metric="${name}"]`)?.textContent;
}

describe("applyGuideApproval", () => {
  it("moves one guide from waiting into published", () => {
    const next = applyGuideApproval(STATS, "busan_guide.md");
    expect(next.approved_count).toBe(2);
    expect(next.pending_count).toBe(1);
    expect(next.total_guides_count).toBe(3);
    expect(next.recent_guides[0].is_approved).toBe(true);
  });

  it("leaves an already published guide unchanged", () => {
    const published = {
      ...STATS,
      recent_guides: [{ ...STATS.recent_guides[0], is_approved: true }],
    };
    expect(applyGuideApproval(published, "busan_guide.md")).toBe(published);
  });
});

describe("dashboard metrics", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows total, published, and waiting as separate counts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(STATS)),
    );

    render(<Dashboard onUnauthorized={() => {}} />);

    expect(await screen.findByText("Total Content")).toBeTruthy();
    expect(screen.getByText("Published")).toBeTruthy();
    expect(screen.getByText("Waiting for Review")).toBeTruthy();
    await waitFor(() => {
      expect(metric("total")).toBe("3");
      expect(metric("published")).toBe("1");
      expect(metric("waiting")).toBe("2");
    });
  });

  it("raises published and lowers waiting as soon as approve succeeds", async () => {
    let releaseApprove;
    const approveGate = new Promise((resolve) => {
      releaseApprove = resolve;
    });
    let statsCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url) => {
        const path = String(url);
        if (path.includes("/approve")) {
          await approveGate;
          return jsonResponse({ ok: true });
        }
        statsCalls += 1;
        if (statsCalls === 1) return jsonResponse(STATS);
        return jsonResponse({
          ...STATS,
          approved_count: 2,
          pending_count: 1,
          recent_guides: STATS.recent_guides.map((guide) => ({ ...guide, is_approved: true })),
        });
      }),
    );

    render(<Dashboard onUnauthorized={() => {}} />);
    const approve = await screen.findByRole("button", { name: "Approve" });
    expect(metric("published")).toBe("1");
    expect(metric("waiting")).toBe("2");

    fireEvent.click(approve);

    await waitFor(() => {
      expect(metric("published")).toBe("2");
      expect(metric("waiting")).toBe("1");
    });
    expect(metric("total")).toBe("3");
    expect(screen.getByRole("button", { name: "Approved" }).disabled).toBe(true);

    releaseApprove();
    await waitFor(() => {
      expect(statsCalls).toBeGreaterThan(1);
    });
    expect(metric("published")).toBe("2");
    expect(metric("waiting")).toBe("1");
  });

  it("restores the previous counts when approval fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url) => {
        if (String(url).includes("/approve")) {
          return jsonResponse({ detail: "nope" }, 500);
        }
        return jsonResponse(STATS);
      }),
    );

    render(<Dashboard onUnauthorized={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));

    expect(await screen.findByText("nope")).toBeTruthy();
    await waitFor(() => {
      expect(metric("published")).toBe("1");
      expect(metric("waiting")).toBe("2");
    });
    expect(screen.getByRole("button", { name: "Approve" }).disabled).toBe(false);
  });

  it("shows guest requests as one-click guide source", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url) => {
        if (String(url).includes("magazine-requests")) {
          return jsonResponse({
            requests: [
              {
                id: 7,
                author_type: "anonymous",
                nickname: "",
                country: "Japan",
                city: "Tokyo",
                place: "Yanaka",
                review: "A quiet alley noodle shop worth the walk.",
                status: "PENDING_REVIEW",
                guide_source: {
                  destination: "Tokyo, Japan",
                  keyword: "Yanaka",
                  ready_for_one_click: true,
                },
              },
            ],
          });
        }
        return jsonResponse(STATS);
      }),
    );

    render(<Dashboard onUnauthorized={() => {}} />);
    fireEvent.click(await screen.findByRole("tab", { name: "Guest Requests" }));

    expect(await screen.findByText("Tokyo, Japan")).toBeTruthy();
    expect(screen.getByText("PENDING_REVIEW")).toBeTruthy();
    expect(screen.getByText("1-click source ready")).toBeTruthy();
    expect(document.querySelector("[data-source-ready='true']")).toBeTruthy();
    expect(document.querySelector("[data-status='PENDING_REVIEW']")).toBeTruthy();
  });
});
