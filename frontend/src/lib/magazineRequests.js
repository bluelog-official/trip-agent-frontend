import { API_BASE_URL } from "./guideCards";

export function magazineRequestEndpoint() {
  return `${API_BASE_URL.replace(/\/api\/v1$/, "")}/api/magazine-requests`;
}

export const REVIEW_MIN = 50;
