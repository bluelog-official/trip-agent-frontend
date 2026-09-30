const CERT = "f08c47fec0942fa0";

export function normalizePublisherId(raw) {
  const value = String(raw || "").trim();
  if (!value || value.startsWith("%") || value.includes("VITE_")) return "";
  const match = /^(?:ca-)?pub-(\d{10,20})$/i.exec(value);
  return match ? `pub-${match[1]}` : "";
}

export function adsTxtLine(publisherId) {
  const publisher = normalizePublisherId(publisherId);
  if (!publisher) return "";
  return `google.com, ${publisher}, DIRECT, ${CERT}`;
}

export function adsTxtBody(publisherId) {
  const line = adsTxtLine(publisherId);
  if (!line) return "# ads.txt disabled: set VITE_ADSENSE_PUBLISHER_ID\n";
  return `${line}\n`;
}
