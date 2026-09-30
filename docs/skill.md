# Multi-Agent Skill & Contract Architecture

레이어 순서: `app/schemas` → `app/services` → `app/agents` → `app/main.py`

## 0. Data Contracts (`app/schemas/guide_schema.py`)

에이전트 간 교환되는 유일한 DTO 정의다.

```python
class GenerateRequest(BaseModel):
    destination: str
    keyword: str = ""

class CityKeywordProfile(BaseModel):
    primary_keyword: str         # 도시 대표 검색 키워드
    long_tail_keywords: list[str]
    local_food_spots: list[str]  # 현지 음식 또는 스팟

class ResearchOutput(BaseModel):
    attractions: list[str]       # 필수 관광지 3곳
    food_spots: list[str]        # 가성비/로컬 맛집 3곳
    seo_keywords: list[str]      # 롱테일 SEO 키워드 5개
    target_currency: str         # 통화 기호 (예: $, ¥, ₩)
    local_tip: str               # 현지인만 아는 꿀팁 1가지

class QAOutput(BaseModel):
    is_approved: bool
    quality_score: int           # 0~100
    violations: list[str]

class RedditSyndication(BaseModel):
    subreddit: str
    title: str
    body: str

class QuoraSyndication(BaseModel):
    question: str
    answer: str

class PinterestSyndication(BaseModel):
    board: str
    pin_title: str
    description: str
    image_alt: str

class BacklinkSyndication(BaseModel):
    anchor_text: str
    target_path: str
    outreach_note: str

class SyndicationOutput(BaseModel):
    social_teasers: list[str]
    platform_hashtags: list[str]
    reddit: RedditSyndication
    quora: QuoraSyndication
    pinterest: PinterestSyndication
    backlink: BacklinkSyndication

class GenerateResponse(BaseModel):
    article_markdown: str
    qa_result: QAOutput
    syndication: SyndicationOutput
    research_model: str          # Research Agent가 실제로 사용한 모델명
    writer_model: str            # Writer Agent가 실제로 사용한 모델명
```

`ResearchOutput`의 5개 필드는 모두 필수다. 백업 LLM의 느슨한 응답은
검증 전에 Sanitizer가 이 구조로 맞춰 주므로 스키마를 느슨하게 풀지 않는다.

## 1. JSON Sanitizer (`app/services/json_sanitizer.py`)

- **Role:** LLM 원문 응답을 `ResearchOutput` 계약 JSON으로 정제하는 순수 로직. LLM SDK 의존성 0%.
- **Entry point:** `normalize_research_json(raw_text: str) -> str`
- **처리 단계:** 마크다운 백틱 제거 → 잡담 사이에서 JSON 본문만 추출 →
  느슨한 문법(후행 콤마, 파이썬 리터럴) 보정 → 래퍼 키(`{"research": {...}}`) 해제 →
  키 별칭 매핑(`top_attractions`/`restaurants`/`currency` 등) → 타입 강제 변환.
- **보장:** 반환된 JSON에는 계약 키 5개가 항상 존재한다. 비어 있는 키는
  `missing_research_fields()`로 확인해 경고를 남긴다.

## 2. Guide Service (`app/services/guide_service.py`)

- **Role:** QA 규칙 평가, 신디케이션 문구 생성, 가이드 메모리 저장소. 순수 로직.
- `evaluate_article()`: H2 소제목 / 마크다운 표 / 본문 분량을 점검해 75점 이상이면 승인.
- `inject_images_below_h2()`: H2 바로 아래에 `![설명](url)`을 최대 2장 삽입.
- `build_generate_response()`, `save_guide()`, `get_guide()`, `list_guides()`.

## 2-0. Keyword Map (`app/services/keyword_map.py`)

- **Role:** 스케줄 대상 10개 도시의 Primary Keyword, Long-tail Keywords, Local Food/Spot 상수.
- **Entry point:** `resolve_city_keywords(destination, keyword="") -> CityKeywordProfile | None`
- `format_keyword_context()`가 위 세 필드를 `[도시 타겟 키워드]` 블록으로 만들어 Research/Writer 프롬프트에 주입한다.
- 요청 `keyword`가 있으면 해당 도시의 Primary Keyword만 그 값으로 덮는다.

## 2-1. Image Service (`app/services/image_service.py`)

- **Role:** Pexels 검색으로 여행지/음식 이미지 URL을 수집. LLM 의존성 없음.
- **Entry point:** `fetch_guide_images(destination, food_query="") -> [{"url", "alt"}, ...]`
- `PEXELS_API_KEY`가 없거나 호출이 실패하면 Unsplash 썸네일 URL을 반환하고 파이프라인은 계속된다.

## 3. LLM Harness (`app/agents/utils.py`)

- **Role:** Gemini 직접 호출 → 실패 시 OpenRouter 우회하는 공용 하네스.
- **Entry point:** `generate_with_fallback(prompt, system_prompt, config, expect_json) -> (원문, 사용 모델명)`
- Gemini 모델 체인을 먼저 순회한 뒤, 전부 실패하면 OpenRouter 모델 체인으로 넘어간다.
- `FORCE_LLM_FALLBACK=1` 환경변수로 백업 경로를 강제 검증할 수 있다.

## 4. Research Agent (`app/agents/research_agent.py`)

- **Role:** 목적지의 관광지·맛집·SEO 키워드·통화·로컬 팁 수집.
- **Signature:** `run_research_agent(destination, keyword="", profile=None) -> (ResearchOutput, research_model)`
- `profile`이 없으면 `resolve_city_keywords()`로 도시 키워드를 찾아 프롬프트에 넣는다.
- 응답은 **반드시** `normalize_research_json()`을 거친 뒤 `ResearchOutput.model_validate_json()`으로 검증한다.

## 5. Writer Agent (`app/agents/writer_agent.py`)

- **Role:** 리서치 데이터를 AdSense 최적화 한국어 마크다운 아티클로 작성.
- **Signature:** `run_writer_agent(destination, research, profile=None) -> (article_markdown, writer_model)`
- 도시 키워드 프로필이 있으면 Primary Keyword, Long-tail Keywords, Local Food/Spot을 작성 규칙에 포함한다.
- 마크다운 표(카테고리·추천 장소·예상 비용·별점)와 H2/H3 구조를 필수로 요구한다.

## 6. API Layer (`app/main.py`)

라우팅과 HTTP 예외 변환만 담당한다.

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/api/v1/generate-guide` | 가이드 생성 (Research → Writer → Pexels → Syndication → QA → 저장) |
| POST | `/api/v1/cron/trigger` | 도시 큐의 다음 목적지를 검수 전 초안으로 저장한다. sitemap과 Google ping은 보내지 않는다 |
| GET | `/api/v1/cron/status` | 스케줄러 실행 여부와 다음 실행 시각 |
| GET | `/sitemap.xml`, `/api/v1/sitemap.xml` | 가이드, K-Culture, 승인 제휴 상점, 고정 페이지 sitemap. `loc`, `lastmod`, `changefreq`, `priority` |
| GET | `/ads.txt`, `/api/ads.txt` | `VITE_ADSENSE_PUBLISHER_ID` 또는 클라이언트 ID로 `google.com, pub-…, DIRECT, f08c47fec0942fa0` |
| GET | `/robots.txt`, `/api/robots.txt` | `User-agent: *` / `Allow: /` 와 공개 sitemap |
| GET | `/api/v1/opengraph?path=` | 매거진·K-Culture·제휴 상점 Open Graph HTML. 소셜 크롤러용 |
| GET | `/api/v1/guides` | 생성된 가이드 목록 |
| GET | `/api/v1/guides/{guide_id}` | 가이드 상세. 승인 전에는 `qa_result.is_approved`가 false |
| POST | `/api/v1/guides/{guide_id}/approve` | 휴먼 리뷰 승인. `is_approved`를 true로 바꾸고 sitemap 갱신 후 Google ping. 응답 후 Marketing Agent를 Background Task로 실행 |
| GET | `/api/v1/admin/dashboard-stats` | Bearer 필수. 전체 가이드 수, 승인된 발행 수, 미승인 검수 대기 수, 배치 상태, 에이전트 헬스, 최근 10개, `marketing_alerts` 최근 20개 |
| DELETE | `/api/v1/admin/marketing-alerts/{alert_id}` | Bearer 필수. 확인한 마케팅 초안을 삭제 |
| GET | `/api/v1/stats/visitors` | 오늘(Asia/Seoul) 순 방문자와 누적 순 방문자 |
| POST | `/api/v1/stats/hit` | 방문 1회 기록. 같은 IP 해시는 하루에 한 번만 집계 |

`/guides`, `/guides/{guide_id}`는 프론트엔드 호환용 동일 라우트다.

## 7. Visitor Stats

- **Schema:** `app/schemas/stats_schema.py` — `VisitorStats`, `VisitorHit`
- **Table:** `app/models/daily_stats.py` — `daily_stats(stat_date, visitor_count)`, 중복 방지용 `visitor_seen(stat_date, ip_hash)`
- **Service:** `app/services/stats_service.py` — `record_hit(ip)`, `visitor_counts()`. 원본 IP는 저장하지 않는다.
- **Router:** `app/routers/stats.py`
- DB 파일 기본 경로는 `output/visitor_stats.db`. 테스트는 `STATS_DB_PATH`로 바꾼다.

## 8. Marketing Agent (`app/agents/marketing_agent.py`)

- **Trigger:** `POST /api/v1/guides/{guide_id}/approve`가 게시에 성공한 뒤 `run_marketing_pipeline(guide_data)`를 Background Task로 실행한다. 매일 09:00 자동 발행(`publish_approved_guide`, QA >= 75)도 같은 파이프라인을 백그라운드 스레드로 트리거한다.
- `post_to_pinterest(guide_data)`: Pins API 형태의 `title`, `description`, `alt_text`, `link`, `media_source`를 만든다. 전송은 하지 않는다.
- `send_discord_webhook(guide_data)`: `DISCORD_WEBHOOK_URL`이 있으면 `requests.post`로 발행 알림을 보낸다. 없으면 건너뛴다.
- `draft_reddit_post(guide_data)`: Reddit에는 올리지 않고 마크다운 초안을 `marketing_alerts` 테이블에 관리자 알림으로 저장한다.
- 해외 서브레딧 초안은 `app/services/reddit_draft_service.py`가 가이드 본문·리서치 스팟으로 100% 영문 작성한다. 스타일은 경험 공유, 질문, 팁 세 가지를 도시마다 나눈다.
- 서브레딧: 일본 도시(Tokyo, Osaka, Kyoto 등)는 `JapanTravel` 또는 `travel`. 유럽은 `travel`, `solotravel`, `Europe`. 그 외 도시는 `travel` 또는 `solotravel`. 본문 끝에 도시·스팟 태그를 붙인다.
- 한글 정형문(`첫 방문 때 실제로 도움이 됐던 동선`)이 남아 있으면 알림 저장 전에 영문 초안으로 다시 쓴다.

## 9. Magazine Requests

- **Schema:** `app/schemas/magazine_request_schema.py` — `MagazineRequestCreate`, `MagazineRequestRecord`, `GuideSource`
- **Table:** `app/models/magazine_requests.py` — `magazine_requests`. 신규 행 `status`는 `PENDING_REVIEW`.
- **Service:** `app/services/magazine_request_service.py` — `create_magazine_request()`, `list_magazine_requests()`, `build_guide_source()`.
- **Router:** `POST /api/magazine-requests` 공개 접수. `GET /api/v1/admin/magazine-requests`는 Bearer 필수.
- `guide_source`는 `destination`(도시, 국가), `keyword`(추천 장소), 후기, 사진 주소, `transport_info`, `discovery_story`, `reference_urls`를 담는다.
- 신규 행의 `fact_check_status`는 `PENDING`이다. `VERIFIED`이고 아직 초안이 없을 때만 `ready_for_one_click`이 true다.
- `PATCH /api/v1/admin/magazine-requests/{id}/fact-check`는 `PENDING`, `VERIFIED`, `REJECTED`와 검증 노트를 저장한다. Bearer 필수.
- `POST /api/v1/admin/magazine-requests/{id}/publish`는 `VERIFIED` 제보만 영어 표준 `{city}_guest_{id}_guide.md`와 한국어 표준 `{city}_guest_{id}_ko_guide.md`를 쓴다. 본문에 교통, 발굴 계기, 참고 URL이 들어간다.
- 접수 본문의 `submit_language`는 `en`, `ko`, `ja`, `zh-CN`, `zh-TW`, `vi`, `th`, `es`, `fr` 중 하나다. 비어 있으면 `en`.
- 영문 파일의 SHA-256은 `english_sha256`에 남는다. 이 값이 XRPL에 앵커링할 표준 해시이다. `MAGAZINE_TRANSLATE_LLM=1`이면 번역 에이전트가 본문을 먼저 옮기고, 실패하면 규칙 기반 표준 문서로 떨어진다.
- DB 기본 경로는 `output/magazine_requests.db`. 테스트는 `MAGAZINE_REQUESTS_DB_PATH`, `MAGAZINE_UPLOAD_DIR`, `MAGAZINE_GUIDE_DIR`로 바꾼다.

## 12. Points and partner shops

- **Schema:** `app/schemas/rewards_schema.py`
- **Tables:** `app/models/rewards.py`
  - `users(id, email, auth_provider, points_balance, created_at)`
  - `point_logs(id, user_id, reporter_email, amount, reason, article_id, created_at)` — 같은 사용자·사유·글은 한 행
  - `partner_merchants(id, name, city, discount_rate, status)`
- **Service:** `app/services/rewards_service.py` — `accrue_points()`, `award_published_guide()`, `award_top_rank()`
- 정식 발행(`publish_approved_guide`)이 제보 초안과 연결되면 `MAGAZINE_PUBLISHED` 100포인트.
- 그 글의 추천 수가 상위 5개에 들어가면 `UGC_TOP_RANK_BONUS` 50포인트. 추천 API가 적립을 호출한다.
- `GET /api/v1/rewards/overview`는 공개. `POST /api/v1/rewards/accrue`는 Bearer 필수.
- DB 기본 경로는 `output/rewards.db`. 테스트는 `REWARDS_DB_PATH`로 바꾼다.
- 구글·애플·카카오 로그인은 `auth_provider`에 기록한다. 이벤트 페이지(`/events`)가 적립 규칙, 포인트 조회, 바우처 진입을 보여 준다.
- 제휴 입점 `POST /api/partners`는 `partner_merchants.status = PENDING_APPROVAL`로 저장한다. 필드는 상점 이름, 분류, 주소, 연락 메일, 전화, 소개, 사진 주소, 손님 혜택이다.
- `POST /api/v1/admin/partners/{id}/approve`는 Bearer 필수. 승인하면 `APPROVED`, `is_active = 1`이 되고 `{slug}_partner_{id}_guide.md` Partner Verified Magazine이 생긴다.
- 공개 `GET /api/v1/rewards/overview`의 `partners`는 활성화된 상점만 돌려준다. 연락 메일은 넣지 않는다.

## 10. Article Votes

- **Schema:** `app/schemas/vote_schema.py` — `VoteCreate`, `VoteResult`, `VoteStatus`
- **Table:** `app/models/votes.py` — `votes(id, article_id, ip_address, created_at)`. `(article_id, ip_address)`는 한 행만 허용한다.
- **Service:** `app/services/vote_service.py` — `cast_vote()`, `vote_statuses()`, `counts_for_period()`.
- **Router:** `POST /api/votes`는 요청 IP(우선 `X-Forwarded-For`)로 글마다 한 표만 저장한다. 중복이면 409. `GET /api/votes?article_ids=`는 그 IP의 투표 여부와 글별 추천 수를 돌려준다.
- DB 기본 경로는 `output/votes.db`. 테스트는 `VOTES_DB_PATH`로 바꾼다.
- 평면 지도 `GET /api/v1/globe/cities`의 도시 순위는 선택 기간(1주, 1개월, 전체 등)의 IP 추천 수를 먼저 보고, 이어서 발행 건수와 품질 점수 합을 본다.

## 11. Duration × Budget Magazines

- **Schema:** `app/schemas/magazine_matrix.py` — `MagazineMatrix`
- **Service:** `app/services/magazine_matrix.py` — `resolve_matrix()`, `parse_matrix_guide_id()`, `matrix_prompt_block()`, `render_offline_guide()`
- **Script:** `scripts/magazine_matrix_generator.py`
- 파일명: `{city}_{duration}_{budget}_guide.md`
  - 기간 키: `1_days`, `3_days`, `1_week`
  - 예산 키: `50usd` (Under $50/day), `100usd`, `200usd`, `budget` (Under $50/day와 같은 필터), `luxury`
  - 예: `tokyo_1_days_50usd_guide.md`, `tokyo_3_days_200usd_guide.md`, `tokyo_1_week_budget_guide.md`
- 프론트매터에 `duration`, `duration_key`, `budget`, `budget_key`를 둔다. 도시 목록은 이 값으로 기간·하루 예산 칩을 거른다.
- `POST /api/v1/generate-guide`에 `duration`과 `budget`을 함께 넘기면 리서치·작성 프롬프트에 같은 표를 넣고, 저장 파일명도 이 규격을 따른다. 둘 중 하나만 오면 400.
- 기본 생성 스크립트는 모델 없이 큐레이션 표로 마크다운을 쓴다. `--llm`은 에이전트 본문을 받은 뒤 같은 프론트매터를 붙인다.

## 13. Social sign-in and point wallet

- **Schema:** `app/schemas/oauth_schema.py` — `UserSession`, `WalletView`, `WalletReport`
- **Service:** `app/services/oauth_service.py`, `app/services/wallet_service.py`
- 프론트는 Vite다. NextAuth 경로를 FastAPI가 연다.
  - `GET /api/auth/providers`
  - `GET /api/auth/signin/{google|apple|kakao}`
  - `GET|POST /api/auth/callback/{provider}`
  - `GET /api/auth/session`
- 제공자 키: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `APPLE_CLIENT_ID`, `APPLE_CLIENT_SECRET`, `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET`. 리다이렉트 기준은 `OAUTH_PUBLIC_URL`, 로그인 후 이동은 `FRONTEND_URL`.
- 키가 없으면 sign-in은 503이다. 콜백은 인가 코드를 프로필로 바꾼 뒤 사용자 세션 토큰을 `#session`으로 프론트 `/wallet`에 넘긴다.
- 소셜 이메일이 제보 `email`(게스트 이메일)과 같으면 `magazine_requests.user_id`와 `point_logs.user_id`를 그 `users.id`로 옮기고, `points_balance`는 그 사용자의 로그 합계로 다시 맞춘다.
- `GET /api/v1/wallet`는 잔액, 적립 내역, 제보의 `PENDING` / `VERIFIED` / `PUBLISHED` 상태, `xrpl_tx_hash`가 있을 때 `https://livenet.xrpl.org/transactions/{hash}` 링크를 돌려준다.
- `POST /api/v1/wallet/saved`와 `DELETE /api/v1/wallet/saved/{guide_id}`는 저장한 매거진이다. 사용자 Bearer가 필요하다. 관리자 토큰으로는 열리지 않는다.

## 14. K-Culture spotlight

- 샘플: `guides/korea_3_days_kbeauty_kfood_guide.md`, `guides/seoul_1_day_kpop_trend_guide.md`, `guides/korea_1_week_heritage_luxury_guide.md`
- 프론트매터 `hot_country: Korea`와 `k_themes`가 테마를 정한다. 파일명의 `kfood`, `kbeauty`, `kpop`, `trend`, `heritage`도 같은 태그에 매핑된다.
- 태그: `K-Food`, `K-Beauty`, `K-Pop & Culture`, `K-Trend`
- 헤더의 Hot Spot: Korea 토글과 지도 위 배너가 같은 필터를 켠다. 켜져 있으면 목록은 이 테마 가이드만 보여 준다.

## 15. Language picker

- 헤더 지구본은 `en`, `ko`, `ja`, `zh-CN`, `zh-TW`, `vi`, `th`, `es`, `fr`를 고른다. 선택은 `app_lang`에 남고 화면 문구가 바로 바뀐다.
- 제보 양식은 고른 `submit_language`를 `POST /api/magazine-requests`에 같이 보낸다.

## 16. Point vouchers

- `POST /api/vouchers/claim`은 사용자 Bearer가 필요하다. 승인된 상점의 `voucher_points`(기본 50)를 빼고 8자 `voucher_code`와 서명 `qr_token`, SVG QR을 만든다.
- `POST /api/vouchers/verify`는 코드와 선택적 `qr_token`을 확인한다. `consume: true`면 `REDEEMED`로 바꾼다.
- 지갑 `/wallet`과 `/mypage`의 내 바우처 탭이 QR을 연다. 서명 비밀은 `VOUCHER_SECRET`이고, 없으면 `OAUTH_TOKEN_SECRET`을 쓴다.
- 프로세스 기동은 `VOUCHER_SECRET`과 `OAUTH_TOKEN_SECRET`이 비어 있거나 32자 미만이거나 `test`·`secret`·`your_super_secret` 같은 기본 문자열이면 `SystemExit`로 멈춘다. pytest 수집 중에는 이 검사를 건너뛴다.

## 17. Request limits and browser hardening

- `POST /api/vouchers/claim`, `POST /api/vouchers/verify`, `GET /api/auth/signin/{provider}`는 IP당 분당 10회다.
- `POST /api/magazine-requests`(`/magazine-request`)와 `POST /api/partners`(`/promote-store`)는 IP당 분당 5회다.
- CORS `allow_origins`는 `*`와 `*.vercel.app` 정규식을 쓰지 않는다. `FRONTEND_URL`, `SITE_URL`, `https://bluelogtrip.com`, `https://www.bluelogtrip.com`, `http://localhost:5173`, `http://127.0.0.1:5173`만 허용하고 `allow_credentials=True`다.
- 모든 HTTP 응답에 `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`를 붙인다.
- 매거진 본문 `ArticleView`는 DOMPurify로 `script`, `iframe`, `onload`, `javascript:`를 지운 뒤 렌더한다.

