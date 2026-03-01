# 값뚝 구현 계획 (plan.md)

> **상태: DRAFT v0.3**
> 작성일: 2026-03-01 | 갱신: 2026-03-01
> 근거 문서: prd.md v0.5 | schema-design.md v0.4 | ui-architecture.md v0.3 | tech-stack-research.md
> **이 문서는 STEP 2 계획 단계입니다. 아직 구현하지 마.**

---

## ⛔️ DO NOT TOUCH

- `documents/` — 설계 문서 (plan.md 제외)
- `scripts/doc_cross_check.py` — 교차 검증 스크립트
- `.claude/` — AI 설정 및 메모리

---

## 0. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자                                    │
│              (Android / iOS / Web 브라우저)                       │
└──────────────┬──────────────────────────────┬───────────────────┘
               │ HTTPS                        │ 푸시
               ▼                              │
┌──────────────────────────────┐              │
│     Flutter App (Dart)       │              │
│  ┌────────┐ ┌──────┐ ┌────┐ │              │
│  │Riverpod│ │  dio │ │ fl │ │              │
│  │Provider│ │Client│ │chart│ │              │
│  └────────┘ └──┬───┘ └────┘ │              │
└────────────────┼─────────────┘              │
                 │ REST API (JSON)             │
                 ▼                             │
┌──────────────────────────────────────────────┼──────────────────┐
│              Axum Server (Rust)               │                  │
│                                               │                  │
│  ┌─────────────────────────────────────────┐ │                  │
│  │  Middleware                              │ │                  │
│  │  ┌──────┐ ┌───────────┐ ┌────────────┐ │ │                  │
│  │  │ JWT  │ │rate_limit │ │ bot_guard  │ │ │                  │
│  │  │ Auth │ │(tower-gov)│ │(blocked_ip)│ │ │                  │
│  │  └──────┘ └───────────┘ └────────────┘ │ │                  │
│  └─────────────────────────────────────────┘ │                  │
│                                               │                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │                  │
│  │ Routes   │ │ Services │ │  Crawlers    │ │                  │
│  │ (API)    │→│ (로직)   │ │  (cron)      │ │                  │
│  └──────────┘ └────┬─────┘ └──────┬───────┘ │                  │
│                    │              │           │                  │
│  ┌─────────┐       │              │           │  ┌────────────┐ │
│  │  moka   │       │              │           │  │   Push      │ │
│  │ (cache) │       │              │           │  │ ┌────┐┌───┐│ │
│  └─────────┘       │              │           │  │ │APNs││FCM││ │
│                    │              │           │  │ └────┘└───┘│ │
│                    ▼              ▼           │  └──────┬─────┘ │
│            ┌───────────────┐ ┌────────────┐  │         │       │
│            │   SQLx        │ │ reqwest +  │  │         │       │
│            │  (PostgreSQL) │ │ scraper    │  │         │       │
│            └───────┬───────┘ └─────┬──────┘  │         │       │
└────────────────────┼───────────────┼─────────┘         │       │
                     ▼               ▼                    ▼
              ┌────────────┐  ┌──────────────┐   ┌──────────────┐
              │PostgreSQL  │  │ 쿠팡/네이버  │   │ APNs / FCM   │
              │17.9 (로컬) │  │  외부 서버   │   │   (외부)     │
              └────────────┘  └──────────────┘   └──────────────┘
```

**데이터 플로우:**
1. **사용자 → 앱 → API**: 검색/알림 설정/즐겨찾기 등 CRUD
2. **크롤러 → 외부 → DB**: 6시간마다 가격 수집 → price_history INSERT → products 갱신
3. **크롤러 → 알림 평가 → 푸시**: 가격 변동 감지 → 활성 알림 조건 체크 → APNs/FCM 발송

---

## 1. 사전 준비 체크리스트 (M0)

M1 시작 **전에** 병렬로 진행해야 하는 항목:

| # | 항목 | 리드타임 | 상태 |
|---|------|---------|------|
| 1 | **쿠팡파트너스 API 키 신청** | 2~4주 | ⬜ 미신청 |
| 2 | **카카오 개발자 앱 등록** (소셜 로그인) | 1~3일 | ⬜ |
| 3 | **Google Cloud 프로젝트** (OAuth + FCM) | 1일 | ⬜ |
| 4 | **Apple Developer Program** ($99/년) | 1~2일 | ⬜ 미가입 |
| 5 | **APNs P8 인증 키** 생성 | Apple 가입 후 즉시 | ⬜ |
| 6 | **네이버 검색 API 키** 신청 | 즉시 | ⬜ |
| 7 | **도메인 구매** (gapttuk.com 등) | 즉시 | ⬜ 미확보 |
| 8 | **Sentry 프로젝트** 생성 (무료 플랜) | 즉시 | ⬜ |
| 9 | **PostgreSQL 17.9** 설치 확인 | - | ✅ 완료 |

> **블로커:** #1 쿠팡파트너스가 승인되지 않으면 M1-6(크롤링)에서 API 연동 불가. 즉시 신청 필수.

---

## 2. 프로젝트 구조

```
gapttuk/                             # 값뚝 프로젝트 루트
├── documents/                    # 설계 문서 (기존)
├── scripts/                      # 유틸리티 스크립트 (기존)
│
├── server/                       # Rust 백엔드 (Axum)
│   ├── Cargo.toml
│   ├── .env                      # DB_URL, API 키 등 (gitignore)
│   ├── sqlx-data.json            # SQLx 오프라인 모드 캐시
│   ├── migrations/               # SQLx 마이그레이션
│   ├── src/
│   │   ├── main.rs               # 진입점 + graceful shutdown
│   │   ├── config.rs             # 환경변수 (dotenvy)
│   │   ├── error.rs              # 통합 에러 (thiserror + IntoResponse)
│   │   ├── cache.rs              # moka 인메모리 캐시 관리
│   │   ├── db/
│   │   │   ├── mod.rs            # PgPool 초기화
│   │   │   └── models/           # SQLx 모델 (FromRow)
│   │   ├── api/
│   │   │   ├── mod.rs            # Router 조합 (/api/v1/ 프리픽스)
│   │   │   ├── pagination.rs     # Cursor 기반 페이지네이션 공통 구조
│   │   │   ├── middleware/       # auth, rate_limit, bot_guard
│   │   │   └── routes/           # 엔드포인트별 핸들러
│   │   ├── services/             # 비즈니스 로직
│   │   ├── crawlers/             # 쿠팡/네이버 크롤링 + 스케줄러
│   │   └── push/                 # APNs (a2) + FCM (fcm)
│   └── tests/
│       ├── api/                  # 통합 테스트 (실제 DB)
│       └── services/             # 단위 테스트
│
├── app/                          # Flutter (Android + iOS + Web)
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── main.dart
│   │   ├── config/               # routes, theme, constants
│   │   ├── models/               # freezed 데이터 모델
│   │   ├── providers/            # Riverpod 상태관리
│   │   ├── services/             # dio API 호출
│   │   ├── screens/              # 21개 화면 (SUBSCRIPTION 제거)
│   │   │   ├── home/
│   │   │   ├── product/
│   │   │   ├── search/
│   │   │   ├── alert/            # center, setting, keyword, category
│   │   │   ├── favorites/
│   │   │   ├── rewards/          # rewards, referral, daily_checkin
│   │   │   ├── auth/             # login, signup
│   │   │   ├── profile/          # my_page, settings
│   │   │   ├── event/
│   │   │   ├── onboarding/
│   │   │   └── web/              # landing, share_preview
│   │   └── widgets/              # 공용 위젯
│   └── test/
│
├── backups/                      # pg_dump 일일 백업 (gitignore)
└── .github/workflows/            # CI/CD (M3 전에 구성)
```

---

## 3. 라이브러리 버전

### Rust (server/Cargo.toml)

| 크레이트 | 용도 | 버전 |
|----------|------|------|
| axum | HTTP 프레임워크 | 0.8.x |
| tokio | 비동기 런타임 | 1.x |
| sqlx | PostgreSQL ORM | 0.8.x |
| serde / serde_json | 직렬화 | 1.x |
| jsonwebtoken | JWT | 9.x |
| reqwest | HTTP 클라이언트 | 0.12.x |
| scraper | HTML 파싱 | 0.22.x |
| tower-governor | Rate Limiting | 0.6.x |
| tokio-cron-scheduler | 스케줄러 | 0.13.x |
| a2 | APNs 푸시 | 0.10.x |
| fcm | FCM 푸시 | 0.9.x |
| **moka** | **인메모리 캐시** | 0.12.x |
| **sentry** | **에러 트래킹** | 0.35.x |
| dotenvy | .env | 0.15.x |
| thiserror | 에러 타입 | 2.x |
| tracing | 로깅 | 0.1.x |
| uuid | ID 생성 | 1.x |
| chrono | 날짜/시간 | 0.4.x |

### Flutter (app/pubspec.yaml)

| 패키지 | 용도 | 버전 |
|--------|------|------|
| flutter_riverpod | 상태관리 | 2.x |
| go_router | 라우팅 | 14.x |
| dio | HTTP 클라이언트 | 5.x |
| fl_chart | 가격 차트 | 0.70.x |
| freezed / json_serializable | 모델 코드 생성 | 2.x / 6.x |
| flutter_secure_storage | 토큰 저장 | 9.x |
| firebase_messaging | FCM 수신 | 15.x |
| cached_network_image | 이미지 캐싱 | 3.x |
| shimmer | 로딩 스켈레톤 | 3.x |
| intl | 숫자 포맷 | 0.19.x |
| **sentry_flutter** | **에러 트래킹** | 8.x |

> 구현 직전 `cargo search` / `pub.dev`에서 실제 최신 버전 확인 후 확정.

---

## 4. 리스크 레지스터

| # | 리스크 | 확률 | 영향 | 대응 |
|---|--------|------|------|------|
| R1 | **쿠팡 크롤링 차단** (IP 차단/구조 변경) | 높음 | 치명적 | UA 로테이션 + 랜덤 딜레이(3~10초) + reqwest 우선, 필요 시 headless 전환. 최악 시 네이버 전용 전환 |
| R2 | **쿠팡파트너스 API 승인 지연** | 중간 | 높음 | 즉시 신청. 승인 전에는 딥링크 없이 일반 URL로 개발. 승인 후 교체 |
| R3 | **Apple 앱 심사 리젝** (가격 추적 앱 제한) | 중간 | 높음 | 심사 가이드라인 사전 검토. 리젝 시 사유별 대응 (웹앱 대안 보유) |
| R4 | **Flutter Web 성능** (초기 로드 3~5MB) | 높음 | 중간 | deferred loading + 이미지 lazy load. 치명적이면 웹은 별도 경량 SPA 검토 |
| R5 | **1인 개발 병목** | 높음 | 중간 | AI 보조로 생산성 극대화. 범위 초과 시 M5 기능 과감히 축소 |
| R6 | **로컬 서버 장애** (정전/네트워크) | 중간 | 높음 | pg_dump 일일 백업 + UPS 검토. 치명적이면 VPS 이전 |

---

## 5. 캐싱 전략 (moka 인메모리)

> **원칙: Redis 사용하지 않음.** PostgreSQL + moka 인메모리 캐시만 사용.

| 대상 | 캐시 TTL | 근거 |
|------|---------|------|
| **blocked_ips** | 5분 | 매 요청 DB 조회 방지. 5분마다 갱신 |
| **categories** | 1시간 | 거의 불변. 서버 시작 시 로드 |
| **popular_searches** | 10분 | 주기적 집계 결과. 높은 조회 빈도 |
| **상품 상세** | 5분 | 동일 상품 반복 조회 대응 |
| **카테고리 알림 목록** | 5분 | 크롤러가 알림 평가 시 반복 조회 |

```rust
// moka 캐시 구조 예시 (의사코드)
struct AppCache {
    blocked_ips: Cache<IpAddr, BlockedIp>,       // TTL 5분
    categories: Cache<i32, Category>,             // TTL 1시간
    popular_searches: Cache<(), Vec<PopularSearch>>, // TTL 10분
    products: Cache<i64, Product>,                // TTL 5분, 최대 10,000건
}
```

---

## 6. 크롤링 상세 설계

### 6.1 데이터 소스

| 소스 | 용도 | 방식 | 시점 |
|------|------|------|------|
| 쿠팡파트너스 API | 상품 검색 + 딥링크 생성 | 공식 REST API | **M1** |
| 쿠팡 웹 | 가격 이력 수집 (API 미제공 시) | reqwest + scraper | **M1** |
| 네이버 검색 API | 최저가(lprice) + 최고가(hprice) | 공식 REST API | **M5** (다중 쇼핑몰 비교) |

### 6.2 차단 우회 전략 (비용 0)

| 기법 | 설명 |
|------|------|
| **랜덤 딜레이** | 요청 간 3~10초 랜덤 sleep |
| **UA 로테이션** | 10+ 브라우저 UA 풀에서 랜덤 선택 |
| **요청 분산** | 카테고리별 시차 배치 (동시에 전체 수집하지 않음) |
| **Referer 설정** | 자연스러운 Referer 헤더 |
| **세션 유지** | Cookie jar로 세션 유지 (쿠팡 세션 필요 시) |
| **Headless 대기** | reqwest 차단 시 headless-chrome 크레이트로 전환 |

### 6.3 수집 스케줄

| 작업 | 주기 | 대상 | 예상 시간 |
|------|------|------|----------|
| **가격 수집** | 6시간 | 전체 추적 상품 (~1,800개) | ~90분 (3초 간격) |
| **인기 검색어 집계** | 1시간 | 검색 로그 집계 → popular_searches | <1초 |
| **products 통계 갱신** | 가격 수집 직후 | current_price, trend, timing_score | <1분 |
| **알림 평가** | 가격 수집 직후 | 활성 알림 조건 체크 → 푸시 발송 | <1분 |

### 6.4 초기 상품 확보

- **카테고리별 Top 100** = 18 카테고리 × 100 = **~1,800개** 상품
- 쿠팡파트너스 API `searchItems`로 카테고리별 인기 상품 100개씩 수집
- 첫 가격 수집 후 즉시 price_history에 기록 (기준점)
- 이후 사용자가 URL/검색으로 추가하는 상품도 자동 추적 대상에 포함

### 6.5 기프티콘 시세 수집 (M5)

| 소스 | 대상 | 방식 | 주기 |
|------|------|------|------|
| 기프티쇼 | 편의점/카페 기프티콘 도매가 | reqwest + scraper | 일 1회 |
| 카카오선물하기 | 대중 브랜드 기프티콘 정가 | reqwest + scraper | 일 1회 |

- 수집한 시세 → `gifticons` 테이블(M5에서 추가)에 저장
- 교환 비율 = `도매가 / 센트당 운영 단가` → 자동 계산
- 도매가 변동 시 교환 가격 자동 갱신
- 초기 런칭 시 3~5종 기프티콘으로 시작, 점진 확대

### 6.6 실패 처리

| 상황 | 대응 |
|------|------|
| 개별 상품 요청 실패 | 3회 재시도 (exponential backoff: 5s → 15s → 45s). 실패 시 skip, 다음 주기에 재시도 |
| IP 차단 감지 (403/429) | 즉시 해당 크롤링 세션 중단. 30분 대기 후 재시도 |
| 전체 크롤러 장애 | Sentry 알림. 수동 확인 후 재시작 |
| 쿠팡 HTML 구조 변경 | scraper selector 업데이트 필요. Sentry에서 파싱 에러 급증으로 감지 |

---

## 7. 마일스톤

### 원칙
- **MVP = P0 + P1 전부** (11개 기능, 무제한 무료)
- 한 번에 하나만 → 완료 시 Git 커밋 → 다음
- 3번 실패 → Git 롤백 → 범위 축소 재시도
- 각 마일스톤 시작 전 STEP 3 (주석달기) 수행

---

### M1. 기반 구축 (6주)

서버 + DB + 크롤링 + 인증 + 알림. Flutter는 M2에서 시작.

#### 의존성 맵

```
M1-1 (스캐폴딩+DB) ──→ M1-3 (모델) ──┬→ M1-5 (상품 API) ──→ M1-6 (크롤링)
                                       │                           ↓
M1-2 (에러+공통) ─────→ M1-4 (인증) ──┘                     M1-8 (알림+푸시)
                                                                  ↑
                                       M1-7 (보안) ──────────────┘
```

#### M1-1. 스캐폴딩 + DB 마이그레이션 (~3일)
- [ ] `server/` Rust 프로젝트 생성
- [ ] Cargo.toml 의존성 추가
- [ ] config.rs — 환경변수 (DATABASE_URL, JWT_SECRET, COUPANG_API_KEY 등)
- [ ] db/mod.rs — PgPool 초기화
- [ ] `migrations/001_initial_schema.sql` — 23개 테이블 + 인덱스 + 파티셔닝 (subscriptions 제거, roulette_results 추가)
- [ ] `migrations/002_seed_data.sql` — shopping_malls (2), categories (18)
- [ ] 각 migration에 대응하는 **down migration** 작성 (`sqlx migrate revert` 지원)
- [ ] SQLx 마이그레이션 실행 + `sqlx prepare` 검증

**DoD:** `cargo build` 성공 + `sqlx migrate run` 완료 + 23개 테이블 생성 확인

#### M1-2. 에러 처리 + 공통 (~2일)
- [ ] error.rs — `AppError` (thiserror + IntoResponse). 에러 코드 체계: `AUTH_001`, `PRODUCT_001` 등
- [ ] API 응답 포맷: `{ "ok": bool, "data": T, "error": { "code": string, "message": string }? }`
- [ ] pagination.rs — Cursor 기반 페이지네이션: `{ "data": [], "cursor": "next_id", "has_more": bool }`
- [ ] cache.rs — moka 캐시 초기화
- [ ] tracing + sentry 초기화

**DoD:** 에러 응답 + 페이지네이션 + 캐시가 동작하는 /health 엔드포인트

#### M1-3. DB 모델 (~3일)
- [ ] user.rs — users (subscription_tier 제거), user_devices
- [ ] product.rs — products, shopping_malls, categories
- [ ] price_history.rs
- [ ] alert.rs — price_alerts, category_alerts, keyword_alerts
- [ ] notification.rs
- [ ] point.rs — user_points, point_transactions
- [ ] reward.rs — referrals, daily_checkins, roulette_results
- [ ] event.rs — events, event_participations
- [ ] card_discount.rs, ai_prediction.rs, popular_search.rs
> **참고:** point_transactions 모델에 신규 transaction_type 반영: `roulette_checkin`, `roulette_event`, `gifticon_exchange`, `referral_welcome`
- [ ] security.rs — api_access_logs, blocked_ips

**DoD:** 모든 모델 `cargo build` 통과 + SQLx 컴파일타임 검증 성공

#### M1-4. 인증 API (~4일)
- [ ] POST `/api/v1/auth/kakao` — 카카오 로그인
- [ ] POST `/api/v1/auth/google` — 구글 로그인
- [ ] POST `/api/v1/auth/apple` — 애플 로그인
- [ ] JWT Access(30분) + Refresh(7일) 토큰 발급/갱신
- [ ] auth.rs 미들웨어 — Authorization Bearer 검증
- [ ] 추천 코드 자동 생성 (UUID 기반 8자리)
- [ ] 단위 테스트: 토큰 발급/검증/만료

**DoD:** 소셜 로그인 → JWT 발급 → 인증 필요 API 호출 흐름 검증 (통합 테스트)

#### M1-5. 상품 + 가격 API (~4일)
- [ ] GET `/api/v1/products/:id` — 상품 상세 (moka 캐시 5분)
- [ ] GET `/api/v1/products/search?q=&cursor=&limit=` — 검색 (cursor 페이지네이션)
- [ ] POST `/api/v1/products/url` — URL로 상품 추가
- [ ] GET `/api/v1/products/:id/prices?from=&to=` — 가격 이력
- [ ] GET `/api/v1/products/:id/prices/daily` — 요일별 집계
- [ ] GET `/api/v1/products/popular` — 인기 검색어 (moka 캐시 10분)

**DoD:** 상품 CRUD + 가격 이력 API 작동 + 통합 테스트

#### M1-6. 크롤링 파이프라인 (~5일)
- [ ] coupang.rs — 쿠팡파트너스 API (searchItems, 딥링크)
- [ ] 가격 수집: reqwest + scraper + UA 로테이션 + 랜덤 딜레이(3~10초)
- [ ] scheduler.rs — 6시간 크론 (0 */6 * * *)
- [ ] 초기 상품 확보: 카테고리별 Top 100 (~1,800개)
- [ ] 가격 변동 감지 → products 갱신 (current_price, price_trend, days_since_lowest 등)
- [ ] price_history INSERT
- [ ] 실패 처리: 3회 재시도 + exponential backoff

**DoD:** 크론 1회 실행 → 1,800개 상품 가격 수집 완료 + price_history 기록 확인

#### M1-7. 보안 미들웨어 (~2일)
- [ ] rate_limit.rs — tower-governor (IP별 60req/min, 검색 10req/min)
- [ ] bot_guard.rs — blocked_ips 조회 (moka 캐시 5분) + UA 블랙리스트
- [ ] api_access_logs INSERT (비동기, 요청 흐름 미차단)
- [ ] Rate limit 응답 헤더: `X-RateLimit-Remaining`, `Retry-After`

**DoD:** 429 응답 정상 반환 + blocked IP 요청 거부 확인

#### M1-8. 알림 + 푸시 (~5일)
- [ ] CRUD `/api/v1/alerts/price`
- [ ] CRUD `/api/v1/alerts/category`
- [ ] CRUD `/api/v1/alerts/keyword`
- [ ] alert_service.rs — 가격 변동 시 활성 알림 조건 평가:
  - ① `target_price`: 현재가 ≤ 사용자 지정가
  - ② `below_average`: 현재가 < 30일 이동평균
  - ③ `near_lowest`: 현재가 ≤ 역대 최저가 × 1.05 (+5% 이내)
  - ④ `all_time_low`: 현재가 < 역대 최저가 (갱신)
- [ ] notification_service.rs — 알림 생성 + 푸시 발송
- [ ] push/apns.rs — a2 (P8 키)
- [ ] push/fcm.rs — fcm HTTP v1
- [ ] 단위 테스트: 알림 조건 평가 로직

**DoD:** 가격 변동 → 알림 조건 매칭 → 푸시 발송 → notifications 테이블 기록 (E2E)

---

### M2. MVP 앱 개발 — P0+P1 (10주)

Flutter 앱 + P0(3개) + P1(8개) = **11개 기능 모두 구현**.
구독 화면 없음. 모든 기능 무료/무제한.

#### M2-1. Flutter 스캐폴딩 (~3일)
- [ ] GoRouter 21개 화면 경로
- [ ] Riverpod 프로바이더 구조
- [ ] dio + JWT 인터셉터 + Cursor 페이지네이션 헬퍼
- [ ] freezed 모델 + build_runner
- [ ] 테마 (라이트/다크)
- [ ] Sentry Flutter 초기화

#### M2-2. 인증 + 온보딩 (~3일)
- [ ] AUTH_LOGIN, AUTH_SIGNUP, ONBOARDING

#### M2-3. 홈 (~5일)
- [ ] HOME — 인기검색어 스크롤 + 상품 카드 그리드 + 필터/정렬
- [ ] product_card.dart, filter_bar.dart, sort_selector.dart

#### M2-4. 검색 (~3일)
- [ ] SEARCH + SEARCH_RESULT (무한 스크롤, cursor)

#### M2-5. 상품 상세 (~7일)
- [ ] PRODUCT_DETAIL — 가격 그래프(fl_chart) + 가격하락확률 게이지 + 요일별 차트
- [ ] 카드 할인가 섹션
- [ ] 단가 계산 표시
- [ ] 하단 CTA ("N원 싸게 구매하기")
- [ ] AI 예측 섹션 → **"곧 출시 예정" 플레이스홀더** (M5에서 실제 데이터로 교체)

#### M2-6. 알림 체계 (~7일)
- [ ] ALERT_CENTER (5탭)
- [ ] ALERT_SETTING (4단계 프리셋 + % 기반)
- [ ] CATEGORY_ALERT — 패시브 알림 등록/관리
- [ ] KEYWORD_ALERT — 키워드 핫딜

#### M2-7. 즐겨찾기 (~2일)
- [ ] FAVORITES + 7일 미니차트

#### M2-8. 마이페이지 + 설정 (~3일)
- [ ] MY_PAGE (프로필, 포인트 위젯, 메뉴)
- [ ] SETTINGS (알림 ON/OFF, 테마)

#### M2-9. 웹 대응 (~5일)
- [ ] WEB_LANDING
- [ ] 웹 GNB + 카테고리 사이드바
- [ ] 반응형 그리드 (2열/3~4열)

#### M2-10. 테스트 (~5일)
- [ ] Widget 테스트 (핵심 화면)
- [ ] Provider 단위 테스트
- [ ] API 연동 통합 테스트

**M2 DoD:** P0+P1 전 기능 동작 + Android/iOS/Web 빌드 성공 + 핵심 플로우 테스트 통과

---

### M3. 베타 출시 (2주)

- [ ] CI/CD 구성 (GitHub Actions: build + test + lint)
- [ ] 전체 기능 QA
- [ ] 성능: API <200ms, 앱 콜드스타트 <3초
- [ ] 쿠팡파트너스 딥링크 + 클릭 트래킹 검증
- [ ] pg_dump 일일 백업 크론 설정
- [ ] TestFlight + Google Play 내부 테스트 배포
- [ ] 피드백 수집 + 크리티컬 버그 수정

**M3 DoD:** 10명+ 베타 테스터 피드백 수집 + 크리티컬 버그 0건

---

### M4. 정식 출시 (2주)

- [ ] App Store 심사 제출
- [ ] Google Play 출시
- [ ] 웹 정식 배포 (도메인 + HTTPS)
- [ ] 쿠팡파트너스 커미션 정산 확인
- [ ] SHARE_PREVIEW — 카카오톡/SNS 공유
- [ ] **회원 탈퇴 API** — soft delete (deleted_at 설정) + 관련 데이터 비활성화
- [ ] **데이터 익명화 크론** — 탈퇴 후 1년 경과 사용자 개인정보 익명화/삭제 (개인정보보호법)

**M4 DoD:** 양대 스토어 출시 완료 + 웹 접속 가능 + 첫 커미션 발생 + 탈퇴 API 동작

---

### M5. 차별화 확장 — P2 (8주)

#### M5-1. 센트(¢) 보상 + 기프티콘 (~2주)
- [ ] 센트(¢) 잔액 관리 API (`GET /api/v1/rewards/balance`)
- [ ] 기프티콘 목록 + 동적 가격 API (`GET /api/v1/gifticons`)
- [ ] 기프티콘 교환 API (`POST /api/v1/rewards/gifticon/exchange`)
- [ ] 기프티콘 시세 수집 또는 수동 관리 운영 도구
- [ ] REWARDS 화면 (센트 잔액 + 기프티콘 교환 + 거래 이력)

#### M5-2. 출석체크 룰렛 (~1주)
- [ ] 출석체크 API (`POST /api/v1/checkin`, `GET /api/v1/checkin/status`)
- [ ] 10일 연속 출석 → 룰렛 기회 부여 로직
- [ ] 룰렛 API (`POST /api/v1/roulette/spin`) — 확률형, 당첨 시 1¢
- [ ] 월 최대 3회 룰렛 제한
- [ ] DAILY_CHECKIN 화면 (캘린더 + 룰렛 UI)

#### M5-3. 친구 초대 (~1주)
- [ ] 추천 코드 공유 API + 가입 시 보상 처리 (초대자 3¢ 확정, 피초대자 1¢)
- [ ] REFERRAL 화면 (코드 공유 + 초대 현황)

#### M5-4. 이벤트/퀴즈 룰렛 (~1주)
- [ ] 이벤트 CRUD API
- [ ] 참여 완료 → 룰렛 기회 획득 → 확률형 룰렛으로 0~2¢ 지급
- [ ] EVENT 화면 (이벤트 목록 + 퀴즈 + 룰렛)

#### M5-5. AI 가격 예측 (~2주)
- [ ] AI 가격 예측 ("지금 사세요/기다리세요") — 무료 제공
- [ ] PRODUCT_DETAIL에 예측 섹션 활성화

#### M5-6. 추가 기능 (~1주)
- [ ] 판매 속도 급증 선제 알림
- [ ] N일만에 최저가 배지
- [ ] 다중 쇼핑몰 비교 (네이버 API 연동)
- [ ] 카카오톡 알림 채널
- [ ] 절약 금액 대시보드

**M5 DoD:** 센트 적립/교환 E2E 동작 + 룰렛 확률 정상 + AI 예측 표시 + 전 P2 기능 QA 통과

---

## 8. 트레이드오프 기록

| # | 주제 | 선택 | 근거 | 리스크 |
|---|------|------|------|--------|
| 1 | 상태관리 | **Riverpod** | BLoC 보일러플레이트 과다. 1인 개발에 적합 | 커뮤니티 규모 |
| 2 | 라우팅 | **GoRouter** | Flutter 공식. 웹 딥링크 네이티브 지원 | - |
| 3 | HTTP (Flutter) | **dio** | 인터셉터(JWT), 요청 취소 지원 | - |
| 4 | 인증 | **JWT 자체 발급** | Firebase Auth 의존성 제거. Access+Refresh 패턴 | 직접 구현 |
| 5 | 크롤링 | **서버 내장** | 별도 프로세스 과잉. Semaphore로 동시성 제한 | API 영향 가능 |
| 6 | 푸시 | **자체 (a2+fcm)** | Firebase 의존성 제거. 세밀한 제어 | APNs 키 관리 |
| 7 | 차트 | **fl_chart** | MIT 무료. 줌/스크롤 지원 | 커스터마이징 한계 |
| 8 | 캐싱 | **moka (인메모리)** | Redis 사용 안 함. 단일 서버에 적합 | 서버 재시작 시 소실 |
| 9 | 수익 | **커미션+광고** | 구독 없음. 무료 개방으로 사용자 극대화 | 커미션 의존도 높음 |

---

## 9. API 설계 규칙

### 공통 규칙
- **프리픽스:** `/api/v1/`
- **인증:** `Authorization: Bearer <JWT>`
- **페이지네이션:** Cursor 기반 `?cursor=<id>&limit=20`
- **응답 포맷:**

```json
// 성공
{ "ok": true, "data": { ... } }

// 목록 (cursor)
{ "ok": true, "data": [...], "cursor": "next_id_or_null", "has_more": true }

// 에러
{ "ok": false, "error": { "code": "AUTH_001", "message": "토큰이 만료되었습니다" } }
```

### 에러 코드 체계

| 프리픽스 | 범위 | 예시 |
|---------|------|------|
| AUTH_ | 인증/인가 | AUTH_001 토큰 만료, AUTH_002 권한 없음 |
| PRODUCT_ | 상품 | PRODUCT_001 상품 없음, PRODUCT_002 잘못된 URL |
| ALERT_ | 알림 | ALERT_001 알림 없음, ALERT_002 조건 오류 |
| RATE_ | 제한 | RATE_001 요청 초과 |
| SYS_ | 시스템 | SYS_001 내부 오류, SYS_002 DB 오류 |

### Rate Limit 응답 헤더

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1709312400
Retry-After: 30  (429 응답 시)
```

---

## 10. 테스트 전략

| 레이어 | 범위 | 도구 | 목표 커버리지 |
|--------|------|------|-------------|
| **Rust 단위** | services, 알림 평가, 캐시 | `#[cfg(test)]` | 70%+ |
| **Rust 통합** | API 엔드포인트 (실제 테스트 DB) | `#[tokio::test]` | 핵심 API 100% |
| **Flutter Widget** | 핵심 화면 렌더링 | `flutter_test` | 주요 화면 |
| **Flutter Provider** | 상태 변경 로직 | `riverpod test` | 60%+ |
| **E2E** | 수동 QA (M3) | 체크리스트 기반 | 전 기능 |

### 환경별 DB 분리

| 환경 | DB 이름 | 용도 | .env 전환 |
|------|---------|------|----------|
| **dev** | `gapttuk_dev` | 로컬 개발. 테스트 데이터 자유 생성/삭제 | `DATABASE_URL=...gapttuk_dev` |
| **test** | `gapttuk_test` | 자동 테스트 전용. 트랜잭션 롤백으로 격리 | 테스트 코드에서 자동 전환 |
| **prod** | `gapttuk` | 실서비스 운영. pg_dump 백업 대상 | `DATABASE_URL=...gapttuk` |

- `.env.dev`, `.env.prod` 분리. 서버 시작 시 `--env` 플래그 또는 `APP_ENV` 환경변수로 전환
- 모든 `.env*` 파일은 `.gitignore` 처리

### 테스트 DB
- `gapttuk_test` 별도 DB 사용
- 각 통합 테스트는 트랜잭션 내 실행 → 롤백 (테스트 간 격리)

---

## 11. 배포/운영

| 항목 | 설정 |
|------|------|
| **서버** | 로컬 머신 (집/사무실) |
| **프로세스** | systemd 서비스 (auto-restart) |
| **DB 백업** | pg_dump 일일 크론 → `backups/` 디렉토리. 7일 보관 후 순환 |
| **모니터링** | Sentry (에러 트래킹) + /health 엔드포인트 |
| **로그** | tracing → stdout JSON → journald |
| **HTTPS** | Cloudflare (무료 SSL) 또는 Let's Encrypt |
| **CI/CD** | GitHub Actions (M3 전에 구성). cargo test + flutter test + build |

### pg_dump 백업 크론

```bash
# /etc/cron.d/gapttuk-backup
0 3 * * * postgres pg_dump gapttuk | gzip > /home/user/backups/gapttuk_$(date +\%Y\%m\%d).sql.gz
# 7일 이전 삭제
0 4 * * * find /home/user/backups/ -name "*.sql.gz" -mtime +7 -delete
```

---

## 12. 실행 순서

```
현재 위치: STEP 2 (plan.md 리뷰 중) ← 여기
    │
    ├─ (병렬) M0 사전 준비: 쿠팡파트너스 신청, 소셜 로그인 앱 등록, Apple 가입
    │
    ▼
STEP 3: M1-1 주석달기 → 리뷰 → 반복
    │
    ▼
STEP 4: M1-1 구현 → 커밋 → M1-2 → ... → M1-8 → M1 완료
    │
    ▼
M2 주석 → 구현 → M3 → M4 → M5
```

---

> **plan.md v0.3 승인됨 (2026-03-01).**
> **현재 단계: STEP 3 — M1-1 주석달기 진행 중.**
> 주석 파일: `documents/m1-1-annotations.md`
> **아직 구현하지 마.**
