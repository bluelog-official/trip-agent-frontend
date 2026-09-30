import { useState } from "react";
import { useTranslation } from "react-i18next";
import { magazineRequestEndpoint, REVIEW_MIN } from "../lib/magazineRequests";

function readPhoto(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("photo"));
    reader.readAsDataURL(file);
  });
}

export default function MagazineRequestPage({ onNavigate }) {
  const { t } = useTranslation();
  const [authorType, setAuthorType] = useState("anonymous");
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [country, setCountry] = useState("");
  const [city, setCity] = useState("");
  const [place, setPlace] = useState("");
  const [review, setReview] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [photoFile, setPhotoFile] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [sending, setSending] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    setNotice("");
    if (authorType === "public" && !nickname.trim()) {
      setError(t("magazineRequest.nameRequired"));
      return;
    }
    if (review.trim().length < REVIEW_MIN) {
      setError(t("magazineRequest.reviewTooShort"));
      return;
    }
    setError("");
    setSending(true);
    try {
      let photoData = "";
      if (photoFile) {
        photoData = await readPhoto(photoFile);
      }
      const response = await fetch(magazineRequestEndpoint(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          author_type: authorType,
          nickname: nickname.trim(),
          email: email.trim(),
          country: country.trim(),
          city: city.trim(),
          place: place.trim(),
          review: review.trim(),
          photo_url: photoUrl.trim(),
          photo_data: photoData,
        }),
      });
      if (!response.ok) {
        throw new Error(t("magazineRequest.failed"));
      }
      setNotice(t("magazineRequest.success"));
      setNickname("");
      setEmail("");
      setCountry("");
      setCity("");
      setPlace("");
      setReview("");
      setPhotoUrl("");
      setPhotoFile(null);
    } catch (err) {
      setError(err.message || t("magazineRequest.failed"));
    } finally {
      setSending(false);
    }
  };

  return (
    <article className="policy-page magazine-request-page">
      <h1>{t("magazineRequest.pageTitle")}</h1>
      <p>{t("magazineRequest.pageLead")}</p>
      <form className="contact-form" onSubmit={onSubmit}>
        <fieldset className="author-types">
          <legend>{t("magazineRequest.authorType")}</legend>
          <label>
            <input
              type="radio"
              name="author_type"
              value="anonymous"
              checked={authorType === "anonymous"}
              onChange={() => setAuthorType("anonymous")}
            />
            {t("magazineRequest.anonymous")}
          </label>
          <label>
            <input
              type="radio"
              name="author_type"
              value="public"
              checked={authorType === "public"}
              onChange={() => setAuthorType("public")}
            />
            {t("magazineRequest.publicName")}
          </label>
        </fieldset>

        <label className="contact-label" htmlFor="magazine-nickname">
          {t("magazineRequest.nickname")}
          <span> {t("magazineRequest.nicknameHint")}</span>
        </label>
        <input
          id="magazine-nickname"
          className="contact-input"
          value={nickname}
          onChange={(event) => setNickname(event.target.value)}
        />

        <label className="contact-label" htmlFor="magazine-email">
          {t("magazineRequest.email")}
          <span> {t("magazineRequest.emailHint")}</span>
        </label>
        <input
          id="magazine-email"
          className="contact-input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label className="contact-label" htmlFor="magazine-country">
          {t("magazineRequest.country")}
        </label>
        <input
          id="magazine-country"
          className="contact-input"
          required
          value={country}
          onChange={(event) => setCountry(event.target.value)}
        />

        <label className="contact-label" htmlFor="magazine-city">
          {t("magazineRequest.city")}
        </label>
        <input
          id="magazine-city"
          className="contact-input"
          required
          value={city}
          onChange={(event) => setCity(event.target.value)}
        />

        <label className="contact-label" htmlFor="magazine-place">
          {t("magazineRequest.place")}
        </label>
        <input
          id="magazine-place"
          className="contact-input"
          required
          value={place}
          onChange={(event) => setPlace(event.target.value)}
        />

        <label className="contact-label" htmlFor="magazine-review">
          {t("magazineRequest.review")}
        </label>
        <textarea
          id="magazine-review"
          className="contact-input contact-message"
          rows={6}
          value={review}
          onChange={(event) => setReview(event.target.value)}
        />
        <p className="review-count">
          {review.trim().length}/{REVIEW_MIN}
        </p>

        <label className="contact-label" htmlFor="magazine-photo-url">
          {t("magazineRequest.photoUrl")}
        </label>
        <input
          id="magazine-photo-url"
          className="contact-input"
          type="url"
          value={photoUrl}
          onChange={(event) => setPhotoUrl(event.target.value)}
        />

        <label className="contact-label" htmlFor="magazine-photo-file">
          {t("magazineRequest.photoFile")}
        </label>
        <input
          id="magazine-photo-file"
          className="contact-input"
          type="file"
          accept="image/*"
          onChange={(event) => setPhotoFile(event.target.files?.[0] || null)}
        />

        <button type="submit" className="contact-submit" disabled={sending}>
          {sending ? t("magazineRequest.submitting") : t("magazineRequest.submit")}
        </button>
        {error ? <p className="dash-banner error">{error}</p> : null}
        {notice ? (
          <p className="contact-notice" role="status">
            {notice}
          </p>
        ) : null}
      </form>
      <button type="button" className="text-link" onClick={() => onNavigate?.("/")}>
        {t("magazineRequest.home")}
      </button>
    </article>
  );
}
