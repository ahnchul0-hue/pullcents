# M1-1 주석: 스캐폴딩 + DB 마이그레이션

> **STEP 3 — 주석달기. 아직 구현하지 마.**
> 이 문서는 M1-1의 로직을 주석으로 기술합니다.
> 리뷰 → 피드백 → 반복 후 승인되면 STEP 4(구현)로 진입합니다.

---

## 1. server/ 프로젝트 생성

### Cargo.toml 구조

```
[package]
name = "gapttuk-server"
edition = "2021"
# Rust 최소 버전: 1.75+ (async fn in trait 지원)

[dependencies]
# --- HTTP 프레임워크 ---
# axum 0.8.x — Router, Json, State, Extension
# tokio 1.x — rt-multi-thread, macros, signal

# --- DB ---
# sqlx 0.8.x — features: runtime-tokio, tls-rustls, postgres, chrono, uuid, migrate
# → 컴파일타임 SQL 검증 활성화

# --- 직렬화 ---
# serde 1.x — derive
# serde_json 1.x

# --- 인증 ---
# jsonwebtoken 9.x

# --- HTTP 클라이언트 (크롤링용) ---
# reqwest 0.12.x — features: json, cookies
# scraper 0.22.x

# --- Rate Limiting ---
# tower-governor 0.6.x

# --- 스케줄러 ---
# tokio-cron-scheduler 0.13.x

# --- 푸시 ---
# a2 0.10.x (APNs)
# fcm 0.9.x (FCM)

# --- 캐시 ---
# moka 0.12.x — features: future

# --- 모니터링 ---
# sentry 0.35.x

# --- 유틸리티 ---
# dotenvy 0.15.x — .env 로드
# thiserror 2.x — 에러 타입
# tracing 0.1.x + tracing-subscriber 0.3.x — 구조화 로깅
# uuid 1.x — features: v4, serde
# chrono 0.4.x — features: serde
```

**주의:** 구현 직전 `cargo search <crate>` 로 실제 최신 버전 확인 후 확정.

---

## 2. config.rs — 환경변수 관리

### 로직

1. `dotenvy::dotenv()` 호출 → `.env` 파일 로드 (없으면 무시)
2. `Config` 구조체에 모든 환경변수 매핑
3. 필수 변수가 없으면 서버 시작 실패 (panic with 명확한 메시지)

### 환경변수 목록

| 변수명 | 타입 | 필수 | 기본값 | 설명 |
|--------|------|------|--------|------|
| `DATABASE_URL` | String | ✅ | - | PostgreSQL 연결 문자열 |
| `APP_ENV` | String | ❌ | `"dev"` | dev / test / prod |
| `HOST` | String | ❌ | `"0.0.0.0"` | 바인딩 주소 |
| `PORT` | u16 | ❌ | `8080` | 포트 |
| `JWT_SECRET` | String | ✅ | - | JWT 서명 키 (최소 32자) |
| `JWT_ACCESS_TTL_SECS` | u64 | ❌ | `1800` | Access 토큰 유효기간 (30분) |
| `JWT_REFRESH_TTL_SECS` | u64 | ❌ | `604800` | Refresh 토큰 유효기간 (7일) |
| `COUPANG_ACCESS_KEY` | String | ❌ | - | 쿠팡파트너스 Access Key (승인 전 없을 수 있음) |
| `COUPANG_SECRET_KEY` | String | ❌ | - | 쿠팡파트너스 Secret Key |
| `NAVER_CLIENT_ID` | String | ❌ | - | 네이버 검색 API (M5) |
| `NAVER_CLIENT_SECRET` | String | ❌ | - | |
| `KAKAO_REST_API_KEY` | String | ❌ | - | 카카오 로그인 |
| `GOOGLE_CLIENT_ID` | String | ❌ | - | 구글 로그인 |
| `APPLE_CLIENT_ID` | String | ❌ | - | 애플 로그인 |
| `APNS_KEY_PATH` | String | ❌ | - | APNs P8 키 파일 경로 |
| `APNS_KEY_ID` | String | ❌ | - | APNs 키 ID |
| `APNS_TEAM_ID` | String | ❌ | - | Apple 팀 ID |
| `FCM_SERVICE_ACCOUNT` | String | ❌ | - | FCM 서비스 계정 JSON 경로 |
| `SENTRY_DSN` | String | ❌ | - | Sentry DSN (없으면 비활성화) |

### 검증 로직

- `DATABASE_URL`: 빈 문자열이면 panic
- `JWT_SECRET`: 32자 미만이면 경고 로그 (prod에서는 panic)
- `APP_ENV`: "dev", "test", "prod" 중 하나가 아니면 panic
- 쿠팡/네이버/소셜 로그인 키: 없으면 경고 로그만 (해당 기능 비활성화)

---

## 3. db/mod.rs — PgPool 초기화

### 로직

1. `Config.database_url` 사용하여 `PgPoolOptions` 생성
2. 연결 풀 설정:
   - `max_connections`: 10 (로컬 서버 기준, prod에서도 충분)
   - `min_connections`: 2
   - `acquire_timeout`: 5초
   - `idle_timeout`: 10분
   - `max_lifetime`: 30분
3. `.connect()` 호출 → 실패 시 재시도 3회 (5초 간격)
4. 연결 성공 시 `sqlx::migrate!()` 실행 (임베디드 마이그레이션)
5. 연결 실패 시 명확한 에러 메시지와 함께 서버 종료

### 반환

- `PgPool` — Axum의 `State`로 공유

### 환경별 DB

| APP_ENV | DB 이름 | 비고 |
|---------|---------|------|
| dev | `gapttuk_dev` | 개발용 |
| test | `gapttuk_test` | 테스트 (트랜잭션 롤백) |
| prod | `gapttuk` | 운영 |

---

## 4. main.rs — 진입점

### 로직

1. `tracing_subscriber` 초기화 (JSON 포맷, stdout)
2. `sentry` 초기화 (DSN 있으면)
3. `Config` 로드
4. `PgPool` 초기화 + 마이그레이션 실행
5. `AppCache` 초기화 (moka — M1-2에서 상세 구현, 여기서는 구조만)
6. `Router` 구성:
   - `/health` — 헬스체크 (DB 연결 확인)
   - `/api/v1/...` — API 라우트 (M1-4~8에서 추가)
7. `axum::serve()` + graceful shutdown (Ctrl+C / SIGTERM)

### graceful shutdown

- `tokio::signal::ctrl_c()` 대기
- 종료 시: 진행 중인 요청 완료 대기 (30초 타임아웃) → PgPool close → 종료

---

## 5. migrations/001_initial_schema.sql

### 테이블 생성 순서 (FK 의존성 기준)

FK 참조가 없는 테이블부터 생성 → 참조하는 테이블 순으로:

```
1단계 (독립 테이블 — FK 없음):
  ① shopping_malls
  ② categories (self-referencing parent_id는 ALTER로 후처리)
  ③ events
  ④ popular_searches
  ⑤ blocked_ips

2단계 (users만 참조):
  ⑥ users
  ⑦ user_devices → users
  ⑧ user_points → users
  ⑨ referrals → users (2개 FK: referrer_id, referred_id)
  ⑩ daily_checkins → users
  ⑪ roulette_results → users
  ⑫ point_transactions → users
  ⑬ api_access_logs → users (nullable FK)

3단계 (products + 관련):
  ⑭ products → shopping_malls, categories
  ⑮ price_history → products
  ⑯ ai_predictions → products
  ⑰ card_discounts → products
  ⑱ user_favorites → users, products

4단계 (알림 — users + products/categories):
  ⑲ price_alerts → users, products
  ⑳ category_alerts → users, categories
  ㉑ keyword_alerts → users, categories(nullable)
  ㉒ notifications → users

5단계 (이벤트 참여):
  ㉓ event_participations → events, users
```

### 각 테이블 상세

#### ① shopping_malls
- id: INTEGER PK GENERATED ALWAYS AS IDENTITY
- name: TEXT NOT NULL
- code: TEXT UNIQUE NOT NULL
- base_url: TEXT NOT NULL
- is_active: BOOLEAN NOT NULL DEFAULT TRUE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ② categories
- id: INTEGER PK GENERATED ALWAYS AS IDENTITY
- name: TEXT NOT NULL
- slug: TEXT UNIQUE NOT NULL
- parent_id: INTEGER (FK → categories.id, NULL이면 최상위) — 테이블 생성 후 ALTER ADD CONSTRAINT
- sort_order: INTEGER NOT NULL DEFAULT 0

#### ③ events
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- title: TEXT NOT NULL
- description: TEXT
- event_type: TEXT NOT NULL — quiz / roulette / survey / promotion
- reward_points: INTEGER NOT NULL DEFAULT 0
- max_participants: INTEGER (NULL = 무제한)
- quiz_data: JSONB
- starts_at: TIMESTAMPTZ NOT NULL
- ends_at: TIMESTAMPTZ NOT NULL
- is_active: BOOLEAN NOT NULL DEFAULT TRUE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ④ popular_searches
- id: INTEGER PK GENERATED ALWAYS AS IDENTITY
- keyword: TEXT NOT NULL
- search_count: INTEGER NOT NULL DEFAULT 0
- rank: SMALLINT NOT NULL
- trend: TEXT — up / down / new / stable
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑤ blocked_ips
- id: INTEGER PK GENERATED ALWAYS AS IDENTITY
- ip_address: INET UNIQUE NOT NULL
- reason: TEXT NOT NULL — rate_limit / bot_ua / pattern_abuse
- blocked_until: TIMESTAMPTZ (NULL = 영구)
- hit_count: INTEGER NOT NULL DEFAULT 1
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑥ users
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- email: TEXT UNIQUE NOT NULL
- nickname: TEXT
- auth_provider: TEXT NOT NULL — kakao / google / apple
- auth_provider_id: TEXT NOT NULL
- profile_image_url: TEXT
- point_balance: INTEGER NOT NULL DEFAULT 0
- referral_code: TEXT UNIQUE NOT NULL
- referred_by: BIGINT (FK → users.id) — 후처리 ALTER
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- deleted_at: TIMESTAMPTZ (soft delete)
- **subscription_tier 컬럼 없음 (제거됨)**
- UNIQUE(auth_provider, auth_provider_id) — 소셜 로그인 고유 식별

#### ⑦ user_devices
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- device_token: TEXT NOT NULL
- platform: TEXT NOT NULL — android / ios / web
- push_enabled: BOOLEAN NOT NULL DEFAULT TRUE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑧ user_points
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) UNIQUE NOT NULL — 1:1 관계
- balance: INTEGER NOT NULL DEFAULT 0
- total_earned: INTEGER NOT NULL DEFAULT 0
- total_spent: INTEGER NOT NULL DEFAULT 0
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑨ referrals
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- referrer_id: BIGINT FK → users(id) NOT NULL
- referred_id: BIGINT FK → users(id) UNIQUE NOT NULL — 한 사용자는 한 번만 추천받음
- referral_code: TEXT NOT NULL
- referrer_rewarded: BOOLEAN NOT NULL DEFAULT FALSE
- referred_rewarded: BOOLEAN NOT NULL DEFAULT FALSE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑩ daily_checkins
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- checkin_date: DATE NOT NULL
- streak_count: INTEGER NOT NULL DEFAULT 1
- roulette_earned: BOOLEAN NOT NULL DEFAULT FALSE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- UNIQUE(user_id, checkin_date) — 하루 1회

#### ⑪ roulette_results
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- roulette_type: TEXT NOT NULL — checkin / event / quiz
- reference_id: BIGINT (관련 엔티티 ID)
- is_winner: BOOLEAN NOT NULL
- reward_amount: INTEGER NOT NULL DEFAULT 0
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑫ point_transactions
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- amount: INTEGER NOT NULL — 양수=획득, 음수=사용
- transaction_type: TEXT NOT NULL — roulette_checkin / roulette_event / referral_reward / referral_welcome / signup_bonus / gifticon_exchange / ad_removal / admin_adjustment
- reference_id: BIGINT
- reference_type: TEXT
- description: TEXT
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑬ api_access_logs (파티셔닝 대상)
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- ip_address: INET NOT NULL
- user_id: BIGINT FK → users(id) (nullable)
- endpoint: TEXT NOT NULL
- method: TEXT NOT NULL
- status_code: SMALLINT NOT NULL
- user_agent: TEXT
- response_time_ms: INTEGER
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- **파티셔닝:** RANGE(created_at) — 월별 파티션 (api_access_logs_YYYYMM)
- **참고:** 파티셔닝된 테이블은 PK가 (id, created_at) 복합키여야 함

#### ⑭ products
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- shopping_mall_id: INTEGER FK → shopping_malls(id) NOT NULL
- category_id: INTEGER FK → categories(id)
- external_product_id: TEXT NOT NULL
- vendor_item_id: TEXT
- product_name: TEXT NOT NULL
- product_url: TEXT
- image_url: TEXT
- current_price: INTEGER
- lowest_price: INTEGER
- highest_price: INTEGER
- average_price: INTEGER
- unit_type: TEXT
- unit_price: NUMERIC(12,2)
- rating: NUMERIC(2,1)
- review_count: INTEGER DEFAULT 0
- is_out_of_stock: BOOLEAN NOT NULL DEFAULT FALSE
- price_trend: TEXT — rising / falling / stable
- days_since_lowest: INTEGER
- drop_from_average: INTEGER
- buy_timing_score: SMALLINT
- sales_velocity: NUMERIC(8,2)
- first_tracked_at: TIMESTAMPTZ
- price_updated_at: TIMESTAMPTZ
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- UNIQUE(shopping_mall_id, external_product_id, vendor_item_id)

#### ⑮ price_history (파티셔닝 대상)
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- product_id: BIGINT FK → products(id) NOT NULL
- price: INTEGER NOT NULL
- is_out_of_stock: BOOLEAN NOT NULL DEFAULT FALSE
- recorded_at: TIMESTAMPTZ NOT NULL
- **파티셔닝:** RANGE(recorded_at) — 월별 파티션 (price_history_YYYYMM)
- **참고:** PK = (id, recorded_at) 복합키

#### ⑯ ai_predictions
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- product_id: BIGINT FK → products(id) NOT NULL
- predicted_action: TEXT NOT NULL — buy_now / wait / neutral
- confidence: NUMERIC(3,2) NOT NULL
- predicted_lowest_price: INTEGER
- predicted_lowest_date: DATE
- price_at_prediction: INTEGER NOT NULL
- factors: JSONB
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- expires_at: TIMESTAMPTZ NOT NULL

#### ⑰ card_discounts
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- product_id: BIGINT FK → products(id) NOT NULL
- card_name: TEXT NOT NULL
- card_type: TEXT NOT NULL — credit / check / membership
- discount_type: TEXT NOT NULL — percent / fixed_amount
- discount_value: INTEGER NOT NULL
- discounted_price: INTEGER
- min_purchase: INTEGER
- valid_from: DATE
- valid_until: DATE
- is_active: BOOLEAN NOT NULL DEFAULT TRUE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑱ user_favorites
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- product_id: BIGINT FK → products(id) NOT NULL
- memo: TEXT
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- UNIQUE(user_id, product_id)

#### ⑲ price_alerts
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- product_id: BIGINT FK → products(id) NOT NULL
- alert_type: TEXT NOT NULL — target_price / below_average / near_lowest / all_time_low
- target_price: INTEGER (alert_type = target_price 시만 사용)
- is_active: BOOLEAN NOT NULL DEFAULT TRUE
- last_triggered_at: TIMESTAMPTZ
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ⑳ category_alerts
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- category_id: INTEGER FK → categories(id) NOT NULL
- alert_condition: TEXT NOT NULL — price_drop_percent / all_time_low / buy_timing / sales_spike
- threshold_percent: INTEGER
- max_price: INTEGER
- is_active: BOOLEAN NOT NULL DEFAULT TRUE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ㉑ keyword_alerts
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- keyword: TEXT NOT NULL
- category_id: INTEGER FK → categories(id) (nullable)
- max_price: INTEGER
- is_active: BOOLEAN NOT NULL DEFAULT TRUE
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- updated_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()

#### ㉒ notifications
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- user_id: BIGINT FK → users(id) NOT NULL
- notification_type: TEXT NOT NULL — price_alert / category_alert / keyword_alert / referral / event / system
- reference_id: BIGINT
- reference_type: TEXT
- title: TEXT NOT NULL
- body: TEXT
- deep_link: TEXT
- is_read: BOOLEAN NOT NULL DEFAULT FALSE
- sent_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- read_at: TIMESTAMPTZ

#### ㉓ event_participations
- id: BIGINT PK GENERATED ALWAYS AS IDENTITY
- event_id: BIGINT FK → events(id) NOT NULL
- user_id: BIGINT FK → users(id) NOT NULL
- answer: JSONB
- is_correct: BOOLEAN
- points_earned: INTEGER NOT NULL DEFAULT 0
- created_at: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- UNIQUE(event_id, user_id)

### 후처리 ALTER (self-referencing FK)

```
-- categories.parent_id FK 추가
ALTER TABLE categories ADD CONSTRAINT fk_categories_parent
  FOREIGN KEY (parent_id) REFERENCES categories(id);

-- users.referred_by FK 추가
ALTER TABLE users ADD CONSTRAINT fk_users_referred_by
  FOREIGN KEY (referred_by) REFERENCES users(id);
```

### 인덱스 생성

schema-design.md 3장 기준, 총 22개 인덱스:

**기존 (v0.1):**
1. idx_products_mall_external — products(shopping_mall_id, external_product_id, vendor_item_id)
2. idx_products_category — products(category_id, current_price)
3. idx_products_trend — products(price_trend, is_out_of_stock)
4. idx_products_timing — products(buy_timing_score)
5. idx_price_history_product_time — price_history(product_id, recorded_at DESC)
6. idx_price_alerts_product_active — price_alerts(product_id) WHERE is_active = TRUE
7. idx_keyword_alerts_active — keyword_alerts(keyword) WHERE is_active = TRUE
8. idx_notifications_user_unread — notifications(user_id, is_read, sent_at DESC)
9. idx_users_auth — users(auth_provider, auth_provider_id)
10. idx_user_favorites_user — user_favorites(user_id, created_at DESC)

**신규 (v0.2+):**
11. idx_users_referral_code — users(referral_code)
12. idx_ai_predictions_product — ai_predictions(product_id, expires_at DESC)
13. idx_card_discounts_product — card_discounts(product_id) WHERE is_active = TRUE
14. idx_category_alerts_cat — category_alerts(category_id) WHERE is_active = TRUE
15. idx_daily_checkins_user — daily_checkins(user_id, checkin_date DESC)
16. idx_point_transactions_user — point_transactions(user_id, created_at DESC)
17. idx_referrals_referrer — referrals(referrer_id)
18. idx_roulette_user_type — roulette_results(user_id, roulette_type, created_at DESC)
19. idx_popular_searches_rank — popular_searches(rank)
20. idx_access_logs_ip_time — api_access_logs(ip_address, created_at DESC)
21. idx_access_logs_status_time — api_access_logs(status_code, created_at DESC) WHERE status_code = 429
22. idx_blocked_ips_addr — blocked_ips(ip_address)

### 파티셔닝 설정

**price_history — 월별 RANGE:**
- 파티션 키: recorded_at
- 초기 파티션: 현재 월 + 향후 3개월 미리 생성
- 네이밍: price_history_202603, price_history_202604, ...
- 보관: 무기한

**api_access_logs — 월별 RANGE:**
- 파티션 키: created_at
- 초기 파티션: 현재 월 + 향후 3개월
- 30일 보관 후 DROP (크론에서 처리, 마이그레이션에서는 생성만)

**파티셔닝 주의사항:**
- 파티셔닝된 테이블의 PK는 파티션 키를 포함해야 함
- price_history: PK = (id, recorded_at)
- api_access_logs: PK = (id, created_at)
- FK를 파티셔닝된 테이블로 걸 때: PostgreSQL 11+에서 지원하지만, 성능상 애플리케이션 레벨에서 관리 권장

---

## 6. migrations/001_down.sql

### 로직

생성의 역순으로 DROP:

```
DROP 순서: ㉓→㉒→㉑→⑳→⑲→⑱→⑰→⑯→⑮→⑭→⑬→⑫→⑪→⑩→⑨→⑧→⑦→⑥→⑤→④→③→②→①

-- 먼저 self-referencing FK 제거
ALTER TABLE categories DROP CONSTRAINT IF EXISTS fk_categories_parent;
ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_referred_by;

-- 테이블 DROP (CASCADE 불필요 — FK 역순이므로)
DROP TABLE IF EXISTS event_participations;
DROP TABLE IF EXISTS notifications;
...
DROP TABLE IF EXISTS shopping_malls;
```

---

## 7. migrations/002_seed_data.sql

### shopping_malls (2건)

| id | name | code | base_url |
|----|------|------|----------|
| 1 | 쿠팡 | coupang | https://www.coupang.com |
| 2 | 네이버쇼핑 | naver | https://shopping.naver.com |

### categories (18건)

쿠팡 메인 카테고리 기준:

| id | name | slug | parent_id | sort_order |
|----|------|------|-----------|------------|
| 1 | 패션의류/잡화 | fashion | NULL | 1 |
| 2 | 뷰티 | beauty | NULL | 2 |
| 3 | 출산/유아동 | baby | NULL | 3 |
| 4 | 식품 | food | NULL | 4 |
| 5 | 주방용품 | kitchen | NULL | 5 |
| 6 | 생활용품 | living | NULL | 6 |
| 7 | 홈인테리어 | interior | NULL | 7 |
| 8 | 가전디지털 | electronics | NULL | 8 |
| 9 | 스포츠/레저 | sports | NULL | 9 |
| 10 | 자동차용품 | auto | NULL | 10 |
| 11 | 도서/음반/DVD | books | NULL | 11 |
| 12 | 완구/취미 | toys | NULL | 12 |
| 13 | 문구/오피스 | office | NULL | 13 |
| 14 | 반려동물용품 | pets | NULL | 14 |
| 15 | 헬스/건강식품 | health | NULL | 15 |
| 16 | 가구 | furniture | NULL | 16 |
| 17 | 여행/티켓 | travel | NULL | 17 |
| 18 | 컴퓨터/노트북 | computer | NULL | 18 |

> 하위 카테고리(parent_id 사용)는 MVP에서는 생성하지 않음. 향후 필요 시 추가.

---

## 8. migrations/002_down.sql

### 로직

```
DELETE FROM categories;
DELETE FROM shopping_malls;
```

---

## 9. SQLx 검증 절차

### 마이그레이션 실행 순서

1. `gapttuk_dev` DB 생성 (없으면)
2. `sqlx migrate run` — 001 + 002 순차 실행
3. `sqlx prepare` — 오프라인 모드 캐시 생성 (sqlx-data.json)
4. `cargo build` — 컴파일타임 SQL 검증 통과 확인

### 검증 체크리스트

- [ ] 23개 테이블 모두 생성 확인: `\dt` 명령
- [ ] 22개 인덱스 생성 확인: `\di` 명령
- [ ] shopping_malls 2건 확인
- [ ] categories 18건 확인
- [ ] 파티셔닝 확인: price_history, api_access_logs 파티션 존재
- [ ] FK 제약조건 확인: `\d+ users` 등
- [ ] down migration 테스트: `sqlx migrate revert` → `sqlx migrate run` → 데이터 무결성 확인

---

## 10. .gitignore 추가 항목

```
# 환경변수
.env
.env.*

# 백업
backups/

# Rust
target/

# Flutter
app/.dart_tool/
app/build/

# IDE
.idea/
.vscode/
*.iml
```

---

## 11. DoD (Definition of Done)

M1-1 완료 조건:

1. ✅ `cargo build` 성공 (경고 0)
2. ✅ `sqlx migrate run` 완료 → 23개 테이블 + 22개 인덱스 생성
3. ✅ `sqlx migrate revert` → `sqlx migrate run` 왕복 테스트 통과
4. ✅ seed data (shopping_malls 2건, categories 18건) 확인
5. ✅ `/health` 엔드포인트 응답 확인 (200 OK + DB 연결 상태)
6. ✅ 파티셔닝 확인 (price_history, api_access_logs)
7. ✅ `.env.example` 파일 생성 (실제 값 없이 키 목록만)
8. ✅ Git 커밋
