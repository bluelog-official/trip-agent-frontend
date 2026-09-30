import { useState } from "react";
import { useTranslation } from "react-i18next";
import i18n, { APP_LANGUAGES, normalizeAppLanguage } from "../i18n/i18n";
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
  const [transportInfo, setTransportInfo] = useState("");
  const [discoveryStory, setDiscoveryStory] = useState("");
  const [referenceUrls, setReferenceUrls] = useState("");
  const [submitLanguage, setSubmitLanguage] = useState(normalizeAppLanguage(i18n.language));
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
          transport_info: transportInfo.trim(),
          discovery_story: discoveryStory.trim(),
          reference_urls: referenceUrls.trim(),
          photo_url: photoUrl.trim(),
          photo_data: photoData,
          submit_language: submitLanguage,
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
      setTransportInfo("");
      setDiscoveryStory("");
      setReferenceUrls("");
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

        <label className="contact-label" htmlFor="magazine-language">
          {t("magazineRequest.writingLanguage")}
        </label>
        <select
          id="magazine-language"
          className="contact-input"
          value={submitLanguage}
          onChange={(event) => setSubmitLanguage(event.target.value)}
        >
          {APP_LANGUAGES.map((item) => (
            <option key={item.code} value={item.code}>
              {item.native}
            </option>
          ))}
        </select>
        <p className="review-count">{t("magazineRequest.writingHint")}</p>

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

        <label className="contact-label" htmlFor="magazine-transport">
          {t("magazineRequest.transport")}
          <span> {t("magazineRequest.optional")}</span>
        </label>
        <textarea
          id="magazine-transport"
          className="contact-input contact-message"
          rows={3}
          value={transportInfo}
          onChange={(event) => setTransportInfo(event.target.value)}
          placeholder={t("magazineRequest.transportHint")}
        />

        <label className="contact-label" htmlFor="magazine-discovery">
          {t("magazineRequest.discovery")}
          <span> {t("magazineRequest.optional")}</span>
        </label>
        <textarea
          id="magazine-discovery"
          className="contact-input contact-message"
          rows={3}
          value={discoveryStory}
          onChange={(event) => setDiscoveryStory(event.target.value)}
          placeholder={t("magazineRequest.discoveryHint")}
        />

        <label className="contact-label" htmlFor="magazine-references">
          {t("magazineRequest.references")}
          <span> {t("magazineRequest.optional")}</span>
        </label>
        <textarea
          id="magazine-references"
          className="contact-input contact-message"
          rows={3}
          value={referenceUrls}
          onChange={(event) => setReferenceUrls(event.target.value)}
          placeholder={t("magazineRequest.referencesHint")}
        />

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
