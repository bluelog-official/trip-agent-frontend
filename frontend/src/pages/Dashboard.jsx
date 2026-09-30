import { useEffect, useCallback, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { adminAuthHeaders } from "../lib/adminSession";
import { API_BASE_URL } from "../lib/guideCards";

const EMPTY_STATS = {
  total_guides_count: 0,
  approved_count: 0,
  pending_count: 0,
  daily_batch_status: { last_run: "", status: "SUCCESS", target_city: "" },
  agent_health: {
    research_agent: "OK",
    writer_agent: "OK",
    qa_agent: "OK",
    syndication_agent: "OK",
  },
  recent_guides: [],
  marketing_alerts: [],
};

const PIPELINE = [
  ["research_agent", "dashboard.pipeline.research"],
  ["writer_agent", "dashboard.pipeline.writer"],
  ["qa_agent", "dashboard.pipeline.qa"],
  ["syndication_agent", "dashboard.pipeline.syndication"],
];

function scoreClass(score) {
  return Number(score) >= 75 ? "score-tag pass" : "score-tag hold";
}

function GuestRequestCard({ row, onUnauthorized, onChange }) {
  const { t } = useTranslation();
  const source = row.guide_source || {};
  const author = row.author_type === "anonymous" ? t("dashboard.guestAnonymous") : row.nickname;
  const [note, setNote] = useState(row.verification_note || "");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const fact = row.fact_check_status || "PENDING";
  const urls = String(row.reference_urls || "").split("\n").map((item) => item.trim()).filter(Boolean);

  const sendFact = async (status) => {
    setBusy(status);
    setMessage("");
    try {
      const res = await fetch(`${API_BASE_URL}/admin/magazine-requests/${row.id}/fact-check`, {
        method: "PATCH",
        headers: { ...adminAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ fact_check_status: status, verification_note: note.trim() }),
      });
      if (res.status === 401) {
        onUnauthorized();
        return;
      }
      if (!res.ok) throw new Error(t("dashboard.factFailed"));
      setMessage(t("dashboard.factSaved"));
      onChange();
    } catch (err) {
      setMessage(err.message || t("dashboard.factFailed"));
    } finally {
      setBusy("");
    }
  };

  const publishDraft = async () => {
    setBusy("publish");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE_URL}/admin/magazine-requests/${row.id}/publish`, {
        method: "POST",
        headers: adminAuthHeaders(),
      });
      if (res.status === 401) {
        onUnauthorized();
        return;
      }
      if (!res.ok) throw new Error(t("dashboard.publishFailed"));
      const payload = await res.json();
      setMessage(t("dashboard.publishDone", { guide: payload.guide_id || "" }));
      onChange();
    } catch (err) {
      setMessage(err.message || t("dashboard.publishFailed"));
    } finally {
      setBusy("");
    }
  };

  return (
    <li className="guest-request-card" data-request-id={row.id}>
      <header>
        <strong>{author}</strong>
        <span data-status={row.status}>
          {row.status === "PENDING_REVIEW" ? t("dashboard.guestStatusPending") : row.status}
        </span>
        <span data-fact-status={fact}>{t(`dashboard.fact.${fact}`)}</span>
      </header>
      <p>
        <span>{t("dashboard.guestPlace")}</span>
        {` ${row.city}, ${row.country} · ${row.place}`}
      </p>
      <p>{row.review}</p>
      {row.transport_info ? (
        <p>
          <span>{t("dashboard.guestTransport")}</span>
          {` ${row.transport_info}`}
        </p>
      ) : null}
      {row.discovery_story ? (
        <p>
          <span>{t("dashboard.guestDiscovery")}</span>
          {` ${row.discovery_story}`}
        </p>
      ) : null}
      {urls.length ? (
        <ul className="guest-references">
          {urls.map((url) => (
            <li key={url}>
              <a href={url} target="_blank" rel="noopener noreferrer">{url}</a>
            </li>
          ))}
        </ul>
      ) : null}
      <div
        className="guest-source"
        data-source-ready={source.ready_for_one_click ? "true" : "false"}
      >
        <span>{t("dashboard.guestSource")}</span>
        <strong>{source.destination}</strong>
        <span>{source.keyword}</span>
        {source.ready_for_one_click ? <em>{t("dashboard.guestReady")}</em> : <em>{t("dashboard.guestHold")}</em>}
      </div>
      <label className="contact-label" htmlFor={`fact-note-${row.id}`}>
        {t("dashboard.factNote")}
      </label>
      <textarea
        id={`fact-note-${row.id}`}
        className="contact-input contact-message"
        rows={2}
        value={note}
        onChange={(event) => setNote(event.target.value)}
      />
      <div className="guest-fact-actions">
        <button type="button" disabled={Boolean(busy)} onClick={() => sendFact("VERIFIED")}>
          {t("dashboard.factVerify")}
        </button>
        <button type="button" disabled={Boolean(busy)} onClick={() => sendFact("REJECTED")}>
          {t("dashboard.factReject")}
        </button>
        {source.ready_for_one_click ? (
          <button type="button" disabled={Boolean(busy)} onClick={publishDraft}>
            {t("dashboard.publishDraft")}
          </button>
        ) : null}
      </div>
      {message ? <p className="dash-banner">{message}</p> : null}
    </li>
  );
}

function GuestRequests({ onUnauthorized }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/admin/magazine-requests`, {
      headers: adminAuthHeaders(),
    })
      .then(async (res) => {
        if (res.status === 401) {
          onUnauthorized();
          throw new Error("Unauthorized");
        }
        if (!res.ok) throw new Error(t("dashboard.guestLoadFailed"));
        return res.json();
      })
      .then((data) => {
        if (!cancelled) {
          setRows(Array.isArray(data?.requests) ? data.requests : []);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled && err.message !== "Unauthorized") setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [onUnauthorized, t]);

  return (
    <section className="guest-requests" aria-label={t("dashboard.tabGuests")}>
      <h2>{t("dashboard.tabGuests")}</h2>
      <p>{t("dashboard.guestLead")}</p>
      {error ? <p className="dash-banner error">{error}</p> : null}
      {loading ? <p>{t("dashboard.guestLoading")}</p> : null}
      {!loading && !error && rows.length === 0 ? <p>{t("dashboard.guestEmpty")}</p> : null}
      {rows.length > 0 ? (
        <ul className="guest-request-list">
          {rows.map((row) => (
            <GuestRequestCard
              key={row.id}
              row={row}
              onUnauthorized={onUnauthorized}
              onChange={() => {
                setLoading(true);
                fetch(`${API_BASE_URL}/admin/magazine-requests`, { headers: adminAuthHeaders() })
                  .then((res) => res.json())
                  .then((data) => setRows(Array.isArray(data?.requests) ? data.requests : []))
                  .catch(() => {})
                  .finally(() => setLoading(false));
              }}
            />
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function applyGuideApproval(stats, filename) {
  const guides = Array.isArray(stats?.recent_guides) ? stats.recent_guides : [];
  const target = guides.find((guide) => guide.filename === filename);
  if (!target || target.is_approved) return stats;
  return {
    ...stats,
    approved_count: Number(stats.approved_count || 0) + 1,
    pending_count: Math.max(0, Number(stats.pending_count || 0) - 1),
    recent_guides: guides.map((guide) =>
      guide.filename === filename ? { ...guide, is_approved: true } : guide,
    ),
  };
}

export default function Dashboard({ onUnauthorized }) {
  const { t } = useTranslation();
  const [stats, setStats] = useState(EMPTY_STATS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [batching, setBatching] = useState(false);
  const [approvingId, setApprovingId] = useState("");
  const [copiedId, setCopiedId] = useState(null);
  const [dismissingId, setDismissingId] = useState(null);
  const [panel, setPanel] = useState("overview");
  const onUnauthorizedRef = useRef(onUnauthorized);
  const statsRef = useRef(stats);
  onUnauthorizedRef.current = onUnauthorized;
  statsRef.current = stats;

  const loadStats = useCallback(async () => {
    const res = await fetch(`${API_BASE_URL}/admin/dashboard-stats`, {
      headers: adminAuthHeaders(),
    });
    if (res.status === 401) {
      onUnauthorizedRef.current();
      throw new Error("Unauthorized");
    }
    if (!res.ok) {
      throw new Error(t("dashboard.statsFailed"));
    }
    return res.json();
  }, [t]);

  useEffect(() => {
    let cancelled = false;
    loadStats()
      .then((data) => {
        if (!cancelled) {
          setStats(data);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled && err.message !== "Unauthorized") setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loadStats]);

  useEffect(() => {
    if (!batching) return undefined;
    const timer = window.setInterval(() => {
      loadStats()
        .then((data) => setStats(data))
        .catch(() => {});
    }, 4000);
    return () => window.clearInterval(timer);
  }, [batching, loadStats]);

  const triggerBatch = async () => {
    if (batching) return;
    setBatching(true);
    setNotice("");
    setError("");
    setStats((current) => ({
      ...current,
      daily_batch_status: {
        ...current.daily_batch_status,
        status: "RUNNING",
      },
    }));
    try {
      const res = await fetch(`${API_BASE_URL}/cron/trigger`, {
        method: "POST",
        headers: adminAuthHeaders(),
      });
      if (res.status === 401) {
        onUnauthorizedRef.current();
        return;
      }
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || t("dashboard.batchFailed"));
      }
      setNotice(t("dashboard.batchDone"));
      const data = await loadStats();
      setStats(data);
    } catch (err) {
      setError(err.message);
      loadStats().then(setStats).catch(() => {});
    } finally {
      setBatching(false);
    }
  };

  const approveGuide = async (filename) => {
    if (!filename || approvingId) return;
    const previous = statsRef.current;
    const optimistic = applyGuideApproval(previous, filename);
    if (optimistic === previous) return;
    setApprovingId(filename);
    setError("");
    setStats(optimistic);
    try {
      const res = await fetch(`${API_BASE_URL}/guides/${encodeURIComponent(filename)}/approve`, {
        method: "POST",
        headers: adminAuthHeaders(),
      });
      if (res.status === 401) {
        setStats(previous);
        onUnauthorizedRef.current();
        return;
      }
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || t("dashboard.approveFailed"));
      }
      setNotice(t("dashboard.approvedNotice", { filename }));
      try {
        const data = await loadStats();
        setStats(data);
      } catch (refreshErr) {
        if (refreshErr.message !== "Unauthorized") setError(refreshErr.message);
      }
    } catch (err) {
      setStats(previous);
      setError(err.message);
    } finally {
      setApprovingId("");
    }
  };

  const copyDraft = async (alert) => {
    const text = alert.body || "";
    setError("");
    const copyWithTextarea = () => {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.top = "0";
      area.style.left = "0";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.focus();
      area.select();
      const copied = document.execCommand("copy");
      document.body.removeChild(area);
      return copied;
    };
    try {
      if (!copyWithTextarea()) {
        if (!navigator.clipboard) throw new Error("copy failed");
        const write = navigator.clipboard.writeText(text);
        const timeout = new Promise((_, reject) => {
          window.setTimeout(() => reject(new Error("copy failed")), 800);
        });
        await Promise.race([write, timeout]);
      }
      setCopiedId(alert.id);
      window.setTimeout(() => {
        setCopiedId((current) => (current === alert.id ? null : current));
      }, 2000);
    } catch {
      setError(t("dashboard.copyFailed"));
    }
  };

  const dismissAlert = async (alertId) => {
    if (dismissingId) return;
    setDismissingId(alertId);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/admin/marketing-alerts/${alertId}`, {
        method: "DELETE",
        headers: adminAuthHeaders(),
      });
      if (res.status === 401) {
        onUnauthorizedRef.current();
        return;
      }
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || t("dashboard.dismissFailed"));
      }
      setNotice(t("dashboard.dismissed"));
      const data = await loadStats();
      setStats(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setDismissingId(null);
    }
  };

  const batch = stats.daily_batch_status || EMPTY_STATS.daily_batch_status;
  const health = stats.agent_health || EMPTY_STATS.agent_health;
  const guides = stats.recent_guides || [];
  const alerts = stats.marketing_alerts || [];
  const batchStatus = (status) => {
    const key = String(status || "SUCCESS").toUpperCase();
    if (key === "RUNNING") return t("dashboard.statusRunning");
    if (key === "FAILED" || key === "ERROR") return t("dashboard.statusFailed");
    return t("dashboard.statusSuccess");
  };

  return (
    <section className="dash">
      <header className="dash-header">
        <div>
          <h1>{t("dashboard.title")}</h1>
          <p>{t("dashboard.lead")}</p>
        </div>
        <button type="button" className="dash-trigger" onClick={triggerBatch} disabled={batching}>
          {batching ? <Loader2 className="spinner" size={16} aria-hidden="true" /> : null}
          {batching ? t("dashboard.triggerRunning") : t("dashboard.trigger")}
        </button>
      </header>

      {error ? <p className="dash-banner error">{error}</p> : null}
      {notice ? <p className="dash-banner">{notice}</p> : null}

      <div className="dash-tabs" role="tablist" aria-label={t("dashboard.tabsLabel")}>
        <button
          type="button"
          role="tab"
          aria-selected={panel === "overview"}
          className={panel === "overview" ? "is-active" : ""}
          onClick={() => setPanel("overview")}
        >
          {t("dashboard.tabOverview")}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={panel === "guests"}
          className={panel === "guests" ? "is-active" : ""}
          onClick={() => setPanel("guests")}
        >
          {t("dashboard.tabGuests")}
        </button>
      </div>

      {panel === "guests" ? (
        <GuestRequests onUnauthorized={onUnauthorized} />
      ) : (
        <>
      <div className="dash-metrics" aria-label={t("dashboard.metricsLabel")}>
        <article className="dash-card metric-total">
          <span>{t("dashboard.totalContent")}</span>
          <strong data-metric="total">{loading ? "…" : stats.total_guides_count}</strong>
          <small>{t("dashboard.totalContentHelp")}</small>
        </article>
        <article className="dash-card metric-published">
          <span>{t("dashboard.publishedCount")}</span>
          <strong data-metric="published">{loading ? "…" : stats.approved_count}</strong>
          <small>{t("dashboard.publishedCountHelp")}</small>
        </article>
        <article className="dash-card metric-waiting">
          <span>{t("dashboard.waitingReview")}</span>
          <strong data-metric="waiting">{loading ? "…" : stats.pending_count}</strong>
          <small>{t("dashboard.waitingReviewHelp")}</small>
        </article>
      </div>

      <div className="dash-cards">
        <article className={`dash-card batch ${String(batch.status || "").toLowerCase()}`}>
          <span>{t("dashboard.batchStatus")}</span>
          <strong>{batchStatus(batch.status)}</strong>
          <small>
            {batch.target_city || "—"}
            {" · "}
            {batch.last_run || t("dashboard.noRecord")}
          </small>
        </article>
      </div>

      <section className="health-panel" aria-label={t("dashboard.healthLabel")}>
        <h2>{t("dashboard.healthTitle")}</h2>
        <ol className="health-bar">
          {PIPELINE.map(([key, label], index) => {
            const state = health[key] || "OK";
            const ok = state === "OK";
            return (
              <li key={key} className={ok ? "health-step ok" : "health-step down"}>
                {index > 0 ? <span className="health-arrow" aria-hidden="true">→</span> : null}
                <span className="health-name">{t(label)}</span>
                <span className="health-state">{ok ? t("dashboard.healthOk") : t("dashboard.healthDown")}</span>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="dash-table-wrap">
        <h2>{t("dashboard.recentGuides")}</h2>
        <table className="dash-table">
          <thead>
            <tr>
              <th>{t("dashboard.city")}</th>
              <th>{t("dashboard.qaScore")}</th>
              <th>{t("dashboard.publishState")}</th>
              <th>{t("dashboard.createdAt")}</th>
              <th>{t("dashboard.action")}</th>
            </tr>
          </thead>
          <tbody>
            {guides.length === 0 ? (
              <tr>
                <td colSpan={5}>{loading ? t("dashboard.loading") : t("dashboard.noGuides")}</td>
              </tr>
            ) : (
              guides.map((guide) => (
                <tr key={guide.filename}>
                  <td>
                    <strong>{guide.city}</strong>
                    <small>{guide.filename}</small>
                  </td>
                  <td>
                    <span className={scoreClass(guide.qa_score)}>{guide.qa_score}</span>
                  </td>
                  <td>{guide.is_approved ? t("dashboard.published") : t("dashboard.held")}</td>
                  <td>{guide.created_at}</td>
                  <td>
                    <button
                      type="button"
                      className="approve-btn"
                      disabled={guide.is_approved || approvingId === guide.filename}
                      onClick={() => approveGuide(guide.filename)}
                    >
                      {guide.is_approved ? t("dashboard.approved") : t("dashboard.approve")}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      <section className="marketing-panel" aria-label={t("dashboard.marketingLabel")}>
        <h2>{t("dashboard.marketingTitle")}</h2>
        {alerts.length === 0 ? (
          <p className="marketing-empty">{loading ? t("dashboard.loading") : t("dashboard.noDrafts")}</p>
        ) : (
          <ul className="marketing-list">
            {alerts.map((alert) => (
              <li key={alert.id} className="marketing-card">
                <header>
                  <div>
                    <strong>{alert.title || alert.guide_id}</strong>
                    <small>
                      {alert.guide_id}
                      {" · "}
                      {alert.created_at}
                    </small>
                  </div>
                  <div className="marketing-actions">
                    <button type="button" className="alert-copy" onClick={() => copyDraft(alert)}>
                      {copiedId === alert.id ? t("dashboard.copied") : t("dashboard.copy")}
                    </button>
                    <button
                      type="button"
                      className="alert-dismiss"
                      disabled={dismissingId === alert.id}
                      onClick={() => dismissAlert(alert.id)}
                    >
                      {dismissingId === alert.id ? t("dashboard.dismissing") : t("dashboard.dismiss")}
                    </button>
                  </div>
                </header>
                <pre className="alert-body">{alert.body}</pre>
              </li>
            ))}
          </ul>
        )}
      </section>
        </>
      )}
    </section>
  );
}
