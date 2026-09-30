# Progress

## Current
Step 1 of 3 is complete. Waiting for approval before step 2.

## Completed
1. Guest magazine request system
   - Home CTA under the globe links to `/magazine-request`
   - Form accepts anonymous or public name, optional nickname/email, country, city, place, review (50+ characters), photo URL or upload
   - `POST /api/magazine-requests` stores rows in `magazine_requests` with status `PENDING_REVIEW`
   - Each row includes `guide_source` (`destination`, `keyword`, review, photo) for a later one-click guide
   - Dashboard tab `Guest Requests` lists those rows

## Remaining
2. IP-based article votes — not started
3. Duration × budget magazine engine — not started

## Files touched
- `app/schemas/magazine_request_schema.py`
- `app/models/magazine_requests.py`
- `app/services/magazine_request_service.py`
- `app/routers/magazine_requests.py`
- `app/main.py`
- `docs/skill.md`
- `tests/test_magazine_requests.py`
- `frontend/src/components/portal/MagazineRequestCta.jsx`
- `frontend/src/pages/MagazineRequestPage.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/App.jsx`
- `frontend/src/lib/usePortalRoute.js`
- `frontend/src/lib/magazineRequests.js`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/ko.json`
- `frontend/src/App.css`

## Notes
- DB default path: `output/magazine_requests.db`. Tests override `MAGAZINE_REQUESTS_DB_PATH` and `MAGAZINE_UPLOAD_DIR`.
- Admin list: `GET /api/v1/admin/magazine-requests` (Bearer token).
- Importing `app.main` currently fails in this environment because installed `litellm` raises `NameError: InputAudio` during import. The step 1 API test mounts the magazine router on its own FastAPI app so it does not load that dependency.
