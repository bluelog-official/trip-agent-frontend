import { useState } from "react";
import { useTranslation } from "react-i18next";
import { apiOrigin } from "../lib/guideCards";

const CATEGORIES = [
  ["K-Food", "promote.categories.food"],
  ["K-Beauty", "promote.categories.beauty"],
  ["Stay", "promote.categories.stay"],
  ["Experience", "promote.categories.experience"],
  ["Tour", "promote.categories.tour"],
];

function readPhoto(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("photo"));
    reader.readAsDataURL(file);
  });
}

export default function PromoteStorePage({ onNavigate }) {
  const { t } = useTranslation();
  const [storeName, setStoreName] = useState("");
  const [category, setCategory] = useState("K-Food");
  const [address, setAddress] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [description, setDescription] = useState("");
  const [images, setImages] = useState("");
  const [benefit, setBenefit] = useState("");
  const [photoFile, setPhotoFile] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [sending, setSending] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    setNotice("");
    if (description.trim().length < 10) {
      setError(t("promote.failed"));
      return;
    }
    setError("");
    setSending(true);
    try {
      let catalogData = "";
      if (photoFile) catalogData = await readPhoto(photoFile);
      const response = await fetch(`${apiOrigin()}/api/partners`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          store_name: storeName.trim(),
          category,
          address: address.trim(),
          contact_email: email.trim(),
          phone: phone.trim(),
          store_description: description.trim(),
          catalog_images: images.trim(),
          catalog_data: catalogData,
          offered_benefit: benefit.trim(),
        }),
      });
      if (!response.ok) throw new Error(t("promote.failed"));
      setNotice(t("promote.success"));
      setStoreName("");
      setAddress("");
      setEmail("");
      setPhone("");
      setDescription("");
      setImages("");
      setBenefit("");
      setPhotoFile(null);
    } catch (err) {
      setError(err.message || t("promote.failed"));
    } finally {
      setSending(false);
    }
  };

  return (
    <article className="policy-page magazine-request-page">
      <h1>{t("promote.pageTitle")}</h1>
      <p>{t("promote.pageLead")}</p>
      <p>{t("promote.purpose")}</p>
      <form className="contact-form" onSubmit={onSubmit}>
        <label className="contact-label" htmlFor="partner-name">{t("promote.storeName")}</label>
        <input id="partner-name" className="contact-input" required value={storeName} onChange={(event) => setStoreName(event.target.value)} />

        <label className="contact-label" htmlFor="partner-category">{t("promote.category")}</label>
        <select id="partner-category" className="contact-input" value={category} onChange={(event) => setCategory(event.target.value)}>
          {CATEGORIES.map(([value, key]) => (
            <option key={value} value={value}>{t(key)}</option>
          ))}
        </select>

        <label className="contact-label" htmlFor="partner-address">{t("promote.address")}</label>
        <input id="partner-address" className="contact-input" required value={address} onChange={(event) => setAddress(event.target.value)} />

        <label className="contact-label" htmlFor="partner-email">{t("promote.email")}</label>
        <input id="partner-email" className="contact-input" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />

        <label className="contact-label" htmlFor="partner-phone">{t("promote.phone")}</label>
        <input id="partner-phone" className="contact-input" value={phone} onChange={(event) => setPhone(event.target.value)} />

        <label className="contact-label" htmlFor="partner-description">{t("promote.description")}</label>
        <textarea id="partner-description" className="contact-input contact-message" rows={5} required value={description} onChange={(event) => setDescription(event.target.value)} />

        <label className="contact-label" htmlFor="partner-images">
          {t("promote.images")}
          <span> {t("promote.imagesHint")}</span>
        </label>
        <textarea id="partner-images" className="contact-input contact-message" rows={3} value={images} onChange={(event) => setImages(event.target.value)} />

        <label className="contact-label" htmlFor="partner-photo">{t("promote.photoFile")}</label>
        <input id="partner-photo" className="contact-input" type="file" accept="image/*" onChange={(event) => setPhotoFile(event.target.files?.[0] || null)} />

        <label className="contact-label" htmlFor="partner-benefit">{t("promote.benefit")}</label>
        <input id="partner-benefit" className="contact-input" required placeholder={t("promote.benefitHint")} value={benefit} onChange={(event) => setBenefit(event.target.value)} />

        {error ? <p className="form-error" role="alert">{error}</p> : null}
        {notice ? <p className="form-notice" role="status">{notice}</p> : null}
        <button type="submit" className="contact-submit" disabled={sending}>
          {sending ? t("promote.submitting") : t("promote.submit")}
        </button>
      </form>
      <button type="button" className="text-link" onClick={() => onNavigate?.("/")}>
        {t("promote.home")}
      </button>
    </article>
  );
}
