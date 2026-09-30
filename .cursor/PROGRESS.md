# Progress

## Current
Step 3 of 4 is complete. Waiting for approval before step 4.

## Completed
1. Guest magazine request system
   - Home CTA under the map links to `/magazine-request`
   - Form accepts anonymous or public name, optional nickname/email, country, city, place, review (50+ characters), photo URL or upload
   - `POST /api/magazine-requests` stores rows in `magazine_requests` with status `PENDING_REVIEW`
   - Each row includes `guide_source` (`destination`, `keyword`, review, photo) for a later one-click guide
   - Dashboard tab `Guest Requests` lists those rows

2. Flat world map and IP votes
   - The home map is an SVG flat world. Pins use latitude and longitude. The WebGL globe is gone.
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

## Remaining
4. UGC fact-check mapping and points / O2O reward foundation — not started

## Files touched
- `app/schemas/magazine_matrix.py`
- `app/schemas/guide_schema.py`
- `app/services/magazine_matrix.py`
- `app/services/guide_service.py`
- `app/services/scheduler_service.py`
- `app/agents/research_agent.py`
- `app/agents/writer_agent.py`
- `scripts/magazine_matrix_generator.py`
- `tests/test_magazine_matrix.py`
- `guides/tokyo_1_days_50usd_guide.md`
- `guides/tokyo_3_days_200usd_guide.md`
- `guides/tokyo_1_week_budget_guide.md`
- `frontend/src/lib/magazineMatrix.js`
- `frontend/src/components/portal/MagazineFilters.jsx`
- `frontend/src/App.jsx`
- `docs/skill.md`

## Notes
- Legacy `{city}_guide.md` files stay on the city page when both chips are All. A specific duration or budget hides them.
- `$200/day` is its own chip because `tokyo_3_days_200usd_guide.md` uses that budget token.
- Importing `app.main` can still fail when installed `litellm` raises `NameError: InputAudio`. Matrix tests do not import the LLM harness.
