# Progress

## Current
Steps 1–4 are complete and ready to deploy from `main`.

## Completed
1. Guest magazine request system
   - Home CTA under the map links to `/magazine-request`
   - Form accepts anonymous or public name, optional nickname/email, country, city, place, review (50+ characters), photo URL or upload
   - Transport notes, discovery story, and reference URLs are stored with the request
   - `POST /api/magazine-requests` stores rows in `magazine_requests` with status `PENDING_REVIEW` and `fact_check_status` `PENDING`
   - Each row includes `guide_source` for a later one-click guide
   - Dashboard tab `Guest Requests` lists those rows

2. Flat world map and IP votes
   - The home map is an SVG flat world. Pins use latitude and longitude. The WebGL globe is gone.
   - Continent and ocean names sit on the map as faint watermark text: Asia, Europe, Africa, North America, South America, Oceania, Pacific, Atlantic, Indian Ocean.
   - Hovering a pin opens a preview with the city, flag, keyword chips, thumbnail, and live vote count. Clicking a pin opens that city's guides.
   - `POST /api/votes` stores one vote per IP per article in `votes(id, article_id, ip_address, created_at)`. A repeat vote returns 409.
   - Vote controls sit on the map preview, every guide card, and the guide detail footer. The count goes up immediately and steps back if the server rejects the vote.
   - City rank uses that period's IP votes first, then published guide count and quality score. Periods include 1 week, 1 month, and all time.

3. Duration × budget magazine engine
   - Guide files can be named `{city}_{duration}_{budget}_guide.md`.
   - Duration keys: `1_days`, `3_days`, `1_week`.
   - Budget keys: `50usd`, `100usd`, `200usd`, `budget`, `luxury`. `50usd` and `budget` share the Under $50/day filter.
   - Samples: `tokyo_1_days_50usd_guide.md`, `tokyo_3_days_200usd_guide.md`, `tokyo_1_week_budget_guide.md`.
   - `scripts/magazine_matrix_generator.py` writes those files from the curation table. `--llm` uses the research and writer prompts with the same duration and budget block.
   - `POST /api/v1/generate-guide` accepts `duration` and `budget` together. One without the other returns 400.
   - Each city guide list has Duration and Daily budget chips. The browser filters the loaded magazines immediately.

4. UGC fact-check, points, and events
   - Dashboard fact check sets `fact_check_status` to `PENDING`, `VERIFIED`, or `REJECTED` and stores a verification note.
   - Only a `VERIFIED` request can be turned into a magazine draft with one click. The draft includes transport, discovery, and reference links.
   - `users`, `point_logs`, and `partner_merchants` tables back the reward ledger.
   - Publishing that draft awards 100 points (`MAGAZINE_PUBLISHED`). Entering the top five vote ranks awards 50 points once (`UGC_TOP_RANK_BONUS`).
   - `/events` explains the point rules, upcoming Google and Apple sign-in, and partner-shop discounts. The nav and footer link to it.

## Deployment checklist
- `app.main` imports without loading `litellm`. OpenRouter still imports it only when a fallback call runs.
- Frontend `npm run build` and `npm test` pass.
- Backend pytest for magazine requests, rewards, votes, and the app import pass.
- Push `main` to `origin` so the host redeploys the flat map. The live 3D globe was the last deployed commit, three feature commits behind this branch.
- Do not commit `venv/`. Local site-packages were mutated outside the project requirements.

## Files touched in step 4
- `app/agents/utils.py`
- `app/schemas/magazine_request_schema.py`
- `app/schemas/rewards_schema.py`
- `app/models/magazine_requests.py`
- `app/models/rewards.py`
- `app/services/magazine_request_service.py`
- `app/services/rewards_service.py`
- `app/services/vote_service.py`
- `app/services/scheduler_service.py`
- `app/routers/magazine_requests.py`
- `app/routers/rewards.py`
- `app/main.py`
- `frontend/src/lib/flatMap.js`
- `frontend/src/components/portal/FlatWorldMap.jsx`
- `frontend/src/pages/MagazineRequestPage.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/pages/EventsPage.jsx`
- `frontend/src/components/portal/GlobalNav.jsx`
- `frontend/src/App.jsx`
- `docs/skill.md`

## Notes
- Legacy `{city}_guide.md` files stay on the city page when both chips are All. A specific duration or budget hides them.
- `$200/day` is its own chip because `tokyo_3_days_200usd_guide.md` uses that budget token.
- Point balances attach to the reporter email until Google or Apple sign-in exists. `auth_provider` is stored on `users` for that later link.
- Partner shops stay an empty table until a merchant row is inserted. The events page says so.
