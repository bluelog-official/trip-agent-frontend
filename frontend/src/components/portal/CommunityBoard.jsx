import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatPostDate } from "../../lib/communityStore";
import i18n, { appLanguage } from "../../i18n/i18n";

const EMPTY_DRAFT = {
  author: "",
  platform: "reddit",
  title: "",
  metric: "",
  body: "",
};

const TABS = ["all", "reddit", "quora", "pinterest", "tip"];

function localizedPost(post, t) {
  const titleKey = `community.seeds.${post.id}.title`;
  if (!i18n.exists(titleKey)) return post;
  return {
    ...post,
    title: t(titleKey),
    metric: t(`community.seeds.${post.id}.metric`, { defaultValue: post.metric }),
    body: t(`community.seeds.${post.id}.body`, { defaultValue: post.body }),
    author: t("community.desk"),
  };
}

export default function CommunityBoard({ posts, query, onCreate }) {
  const { t } = useTranslation();
  const language = appLanguage();
  const [tab, setTab] = useState("all");
  const [openId, setOpenId] = useState("");
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.replace(/^#/, ""));
    if (!id) return;
    setOpenId(id);
    setTab("all");
    window.requestAnimationFrame(() => {
      document.getElementById(`post-${id}`)?.scrollIntoView({ block: "center" });
    });
  }, []);

  const needle = query.trim().toLowerCase();
  const visible = posts.filter((post) => {
    const shown = localizedPost(post, t);
    if (tab !== "all" && post.platform !== tab) return false;
    if (!needle) return true;
    return `${shown.title} ${shown.body} ${shown.author} ${shown.metric}`.toLowerCase().includes(needle);
  });

  const updateDraft = (field) => (event) => {
    setDraft((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!draft.title.trim() || !draft.body.trim()) {
      setFormError(t("community.required"));
      return;
    }
    const post = onCreate({
      author: draft.author.trim() || t("community.traveler"),
      platform: draft.platform,
      title: draft.title.trim(),
      metric: draft.metric.trim(),
      body: draft.body.trim(),
    });
    setDraft(EMPTY_DRAFT);
    setFormError("");
    setTab(post.platform);
    setOpenId(post.id);
  };

  return (
    <section className="board">
      <header className="board-header">
        <p className="hero-kicker">{t("community.kicker")}</p>
        <h1>{t("community.title")}</h1>
        <p className="board-lead">{t("community.lead")}</p>
        <p className="board-lead">{t("community.purpose")}</p>
      </header>

      <div className="board-tabs" role="tablist" aria-label={t("community.tabsLabel")}>
        {TABS.map((id) => {
          const count = id === "all"
            ? posts.length
            : posts.filter((post) => post.platform === id).length;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              className={tab === id ? "board-tab active" : "board-tab"}
              onClick={() => setTab(id)}
            >
              {t(`community.tabs.${id}`)}
              <span>{count}</span>
            </button>
          );
        })}
      </div>

      <div className="board-layout">
        <form className="composer" onSubmit={handleSubmit}>
          <h2>{t("community.write")}</h2>
          <label>
            {t("community.name")}
            <input
              value={draft.author}
              onChange={updateDraft("author")}
              placeholder={t("community.namePlaceholder")}
            />
          </label>
          <label>
            {t("community.channel")}
            <select value={draft.platform} onChange={updateDraft("platform")}>
              <option value="reddit">{t("community.channels.reddit")}</option>
              <option value="quora">{t("community.channels.quora")}</option>
              <option value="pinterest">{t("community.channels.pinterest")}</option>
              <option value="tip">{t("community.channels.tip")}</option>
            </select>
          </label>
          <label>
            {t("community.titleField")}
            <input
              value={draft.title}
              onChange={updateDraft("title")}
              placeholder={t("community.titlePlaceholder")}
            />
          </label>
          <label>
            {t("community.result")}
            <input
              value={draft.metric}
              onChange={updateDraft("metric")}
              placeholder={t("community.resultPlaceholder")}
            />
          </label>
          <label>
            {t("community.note")}
            <textarea
              value={draft.body}
              onChange={updateDraft("body")}
              rows={5}
              placeholder={t("community.notePlaceholder")}
            />
          </label>
          {formError ? <p className="form-error">{formError}</p> : null}
          <button type="submit" className="composer-submit">{t("community.submit")}</button>
        </form>

        <div className="post-column">
          {visible.length === 0 ? (
            <p className="grid-empty">{t("community.empty")}</p>
          ) : (
            <ul className="post-list">
              {visible.map((post) => {
                const shown = localizedPost(post, t);
                const open = openId === post.id;
                return (
                  <li key={post.id} id={`post-${post.id}`}>
                    <article className={open ? "post-card open" : "post-card"}>
                      <button
                        type="button"
                        className="post-toggle"
                        aria-expanded={open}
                        onClick={() => setOpenId(open ? "" : post.id)}
                      >
                        <span className={`platform-pill ${post.platform}`}>
                          {t(`community.labels.${post.platform}`, { defaultValue: post.platform })}
                        </span>
                        <h3>{shown.title}</h3>
                        <small>
                          {shown.author}
                          {shown.metric ? ` · ${shown.metric}` : ""}
                          {` · ${formatPostDate(post.createdAt, language)}`}
                        </small>
                      </button>
                      {open ? <p className="post-body">{shown.body}</p> : null}
                    </article>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
