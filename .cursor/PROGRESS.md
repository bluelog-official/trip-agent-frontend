# Progress

## Current
Globe language picker, Promote My Store applications, and point vouchers are on `main`.

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
   - `/events` explains the point rules and partner-shop discounts. The nav and footer link to it.

5. K-Culture spotlight
   - Header control and the map banner: Hot Spot: Korea (K-Culture Guide).
   - Theme chips: K-Food, K-Beauty, K-Pop & Culture, K-Trend.
   - Samples: `korea_3_days_kbeauty_kfood_guide.md`, `seoul_1_day_kpop_trend_guide.md`, `korea_1_week_heritage_luxury_guide.md`.
   - Turning the spotlight on hides guides that are not tagged `hot_country: Korea`.

6. Social sign-in and point wallet
   - FastAPI serves the NextAuth-style routes under `/api/auth` for Google, Apple, and Kakao. The Vite app is not a Next.js host.
   - A configured provider redirects back to `/wallet#session=`. Missing client keys return 503 and the button stays disabled.
   - When the social email matches a guest report email, `point_logs` and `magazine_requests` move to that `users.id` and the balance becomes the sum of the logs.
   - `/wallet` and `/mypage` show the profile, point balance, history, report state (`PENDING`, `VERIFIED`, `PUBLISHED`), an XRPL explorer link when `xrpl_tx_hash` is set, and saved magazines.
   - The sign-in modal opens for a report, point check, voucher, or save when there is no session. A report can continue as a guest.

7. Globe picker, partner applications, and O2O vouchers
   - The header globe opens English, Korean, Japanese, Simplified Chinese, Traditional Chinese, Vietnamese, Thai, Spanish, and French. The choice is stored as `app_lang` and the visible chrome switches immediately.
   - `/magazine-request` sends `submit_language`. A verified report publishes `{city}_guest_{id}_guide.md` in English and `{city}_guest_{id}_ko_guide.md` in Korean. `english_sha256` is the SHA-256 of the English file and is the hash to anchor on XRPL.
   - Set `MAGAZINE_TRANSLATE_LLM=1` when the translation agent should call Gemini before the offline standard text. Without that flag, publish stays offline.
   - Header, home banner, and footer link to `/promote-store`. `POST /api/partners` stores `PENDING_APPROVAL`. Admin approval writes a Partner Verified Magazine and sets `is_active`.
   - `/events` and the guide footer list active shops. `POST /api/vouchers/claim` spends points for an 8-character code and a signed QR. `/wallet` shows it. `POST /api/vouchers/verify` checks or redeems the code.

## Deployment checklist
- `app.main` imports without loading `litellm`. OpenRouter still imports it only when a fallback call runs.
- Frontend `npm run build` and `npm test` pass.
- Backend pytest for magazine requests, rewards, votes, oauth/wallet, and the app import pass.
- Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `APPLE_CLIENT_ID`, `APPLE_CLIENT_SECRET`, `KAKAO_CLIENT_ID`, and `KAKAO_CLIENT_SECRET` on the API host before the live buttons can complete a redirect. `OAUTH_PUBLIC_URL` is the API origin. `FRONTEND_URL` is the site origin.
- Do not commit `venv/`. Local site-packages were mutated outside the project requirements.

## Files touched in this step
- `app/services/magazine_translation.py`
- `app/agents/translation_agent.py`
- `app/services/partner_service.py`
- `app/services/voucher_service.py`
- `app/services/qr_svg.py`
- `app/routers/partners.py`
- `app/routers/vouchers.py`
- `frontend/src/i18n/i18n.js`
- `frontend/src/components/portal/GlobalNav.jsx`
- `frontend/src/pages/PromoteStorePage.jsx`
- `frontend/src/pages/WalletPage.jsx`
- `docs/skill.md`

## Notes
- Legacy `{city}_guide.md` files stay on the city page when both duration and budget chips are All, and when the Korea spotlight is off.
- Point balances now follow the signed-in user. Until someone signs in, accrual still keys off the reporter email.
- Partner shops appear on `/events` after an admin approves the application. Until then the public list stays empty.
- An XRPL link appears only after `xrpl_tx_hash` is stored on the report. The English magazine SHA-256 is stored separately as `english_sha256`.
- `VOUCHER_SECRET` signs voucher QR payloads. It falls back to `OAUTH_TOKEN_SECRET`.
