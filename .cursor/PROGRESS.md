# Progress

## Current
Step 2 of 3 is complete. Waiting for approval before step 3.

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

## Remaining
3. Duration × budget magazine engine — not started

## Files touched
- `app/schemas/vote_schema.py`
- `app/schemas/globe_schema.py`
- `app/models/votes.py`
- `app/services/vote_service.py`
- `app/services/globe_service.py`
- `app/routers/votes.py`
- `app/main.py`
- `docs/skill.md`
- `tests/test_votes.py`
- `frontend/src/components/portal/FlatWorldMap.jsx`
- `frontend/src/components/portal/GlobeMap.jsx`
- `frontend/src/components/portal/VoteButton.jsx`
- `frontend/src/components/portal/ArticleGrid.jsx`
- `frontend/src/components/portal/GuideArticle.jsx`
- `frontend/src/lib/flatMap.js`
- `frontend/src/lib/votes.js`
- `frontend/src/lib/globeCities.js`
- `frontend/package.json`

## Notes
- Votes DB default path: `output/votes.db`. Tests override `VOTES_DB_PATH`.
- `GET /api/votes?article_ids=` returns the count and whether this IP already voted.
- A local browser check rendered the flat map. The deployed cities API timed out, so live pins were not on that page. Component tests cover hover, vote, and pin navigation.
- Importing `app.main` can still fail when installed `litellm` raises `NameError: InputAudio`. Vote tests mount the vote router on their own FastAPI app.
