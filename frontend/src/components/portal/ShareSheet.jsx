import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Image, Link2, Share2, X } from "lucide-react";
import {
  absoluteShareUrl,
  downloadDataUrl,
  renderShareCard,
  shareCaption,
  shareToKakao,
  xShareUrl,
} from "../../lib/socialShare";

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  const copied = document.execCommand("copy");
  area.remove();
  if (!copied) throw new Error("copy failed");
}

export default function ShareSheet({ title, description, pathname, image = "" }) {
  const { t } = useTranslation();
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const pageUrl = absoluteShareUrl(pathname);
  const caption = shareCaption({ title, description, url: pageUrl });

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const flash = (message) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 1800);
  };

  const copyLink = async () => {
    try {
      await copyText(pageUrl);
      flash(t("share.copied"));
    } catch {
      flash(t("share.failed"));
    }
  };

  const shareKakao = async () => {
    try {
      const result = await shareToKakao({
        title,
        description,
        imageUrl: image,
        url: pageUrl,
      });
      if (result === "unconfigured") {
        await copyText(caption);
        flash(t("share.kakaoCopied"));
        return;
      }
      flash(t("share.kakaoReady"));
    } catch {
      try {
        await copyText(caption);
        flash(t("share.kakaoCopied"));
      } catch {
        flash(t("share.failed"));
      }
    }
  };

  const saveCard = async () => {
    try {
      const dataUrl = await renderShareCard({ title, description, imageUrl: image });
      downloadDataUrl(dataUrl, "bluelog-share.png");
      await copyText(caption);
      flash(t("share.imageSaved"));
    } catch {
      flash(t("share.failed"));
    }
  };

  return (
    <div className="share-sheet">
      <button type="button" className="share-open" onClick={() => setOpen(true)}>
        <Share2 size={16} aria-hidden="true" />
        {t("share.button")}
      </button>
      {open ? (
        <div className="share-backdrop" onClick={() => setOpen(false)}>
          <div
            className="share-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onClick={(event) => event.stopPropagation()}
          >
            <header className="share-dialog-head">
              <h2 id={titleId}>{t("share.title")}</h2>
              <button type="button" className="share-close" onClick={() => setOpen(false)} aria-label={t("share.close")}>
                <X size={16} aria-hidden="true" />
              </button>
            </header>
            <p className="share-preview-title">{title}</p>
            <p className="share-preview-copy">{description}</p>
            <div className="share-actions">
              <button type="button" onClick={shareKakao}>{t("share.kakao")}</button>
              <button type="button" onClick={copyLink}>
                <Link2 size={16} aria-hidden="true" />
                {t("share.copy")}
              </button>
              <a href={xShareUrl({ title, url: pageUrl })} target="_blank" rel="noopener noreferrer">
                {t("share.x")}
              </a>
              <button type="button" onClick={saveCard}>
                <Image size={16} aria-hidden="true" />
                {t("share.instagram")}
              </button>
            </div>
            {notice ? <p role="status">{notice}</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
