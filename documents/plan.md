# PullCents 구현 계획 (plan.md)

> **상태: DRAFT v0.1**
> 작성일: 2026-03-01 | 갱신: 2026-03-01
> 근거 문서: prd.md v0.3 | schema-design.md v0.3 | ui-architecture.md v0.2 | tech-stack-research.md
> **이 문서는 STEP 2 계획 단계입니다. 아직 구현하지 마.**

---

## ⛔️ DO NOT TOUCH

- `documents/` — 설계 문서. plan.md를 제외한 파일은 수정하지 않는다
- `scripts/doc_cross_check.py` — 교차 검증 스크립트
- `.claude/` — AI 설정 및 메모리

---

## 1. 프로젝트 구조

```
pullcents/
├── documents/                    # 설계 문서 (기존)
├── scripts/                      # 유틸리티 스크립트 (기존)
│
├── server/                       # Rust 백엔드 (Axum)
│   ├── Cargo.toml
│   ├── .env                      # DB_URL, API 키 등 (gitignore)
│   ├── sqlx-data.json            # SQLx 오프라인 모드 캐시
│   ├── migrations/               # SQLx 마이그레이션
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_seed_data.sql
│   │   └── ...
│   ├── src/
│   │   ├── main.rs               # 진입점: Axum 서버 + graceful shutdown
│   │   ├── config.rs             # 환경변수 파싱 (envy 또는 dotenvy)
│   │   ├── error.rs              # 통합 에러 타입 (thiserror)
│   │   ├── db/
│   │   │   ├── mod.rs            # PgPool 초기화
│   │   │   └── models/           # SQLx 모델 (FromRow)
│   │   │       ├── user.rs
│   │   │       ├── product.rs
│   │   │       ├── price_history.rs
│   │   │       ├── alert.rs      # price_alerts + category_alerts + keyword_alerts
│   │   │       ├── notification.rs
│   │   │       ├── point.rs      # user_points + point_transactions
│   │   │       ├── reward.rs     # referrals + daily_checkins
│   │   │       ├── event.rs      # events + event_participations
│   │   │       ├── card_discount.rs
│   │   │       ├── ai_prediction.rs
│   │   │       └── mod.rs
│   │   ├── api/
│   │   │   ├── mod.rs            # Router 조합
│   │   │   ├── middleware/
│   │   │   │   ├── auth.rs       # JWT 검증 미들웨어
│   │   │   │   ├── rate_limit.rs # tower-governor
│   │   │   │   └── bot_guard.rs  # blocked_ips 조회 + UA 필터
│   │   │   └── routes/
│   │   │       ├── auth.rs       # POST /auth/login, /auth/signup
│   │   │       ├── products.rs   # GET /products/:id, /products/search
│   │   │       ├── prices.rs     # GET /products/:id/history
│   │   │       ├── alerts.rs     # CRUD /alerts/price, /alerts/category, /alerts/keyword
│   │   │       ├── favorites.rs  # CRUD /favorites
│   │   │       ├── notifications.rs
│   │   │       ├── points.rs     # GET /points, /points/transactions
│   │   │       ├── rewards.rs    # POST /checkin, GET /referrals
│   │   │       ├── events.rs     # GET /events, POST /events/:id/participate
│   │   │       └── health.rs     # GET /health
│   │   ├── services/
│   │   │   ├── auth_service.rs   # 소셜 로그인 (카카오/구글/애플)
│   │   │   ├── product_service.rs
│   │   │   ├── price_service.rs  # 가격 이력 집계, 통계 계산
│   │   │   ├── alert_service.rs  # 알림 평가 + 발송 트리거
│   │   │   ├── notification_service.rs
│   │   │   ├── point_service.rs  # 포인트 적립/차감 트랜잭션
│   │   │   └── prediction_service.rs
│   │   ├── crawlers/
│   │   │   ├── mod.rs
│   │   │   ├── coupang.rs        # 쿠팡파트너스 API + reqwest
│   │   │   ├── naver.rs          # 네이버 검색 API (lprice/hprice)
│   │   │   └── scheduler.rs     # tokio-cron-scheduler 기반 주기 실행
│   │   └── push/
│   │       ├── mod.rs
│   │       ├── apns.rs           # a2 크레이트 (iOS)
│   │       └── fcm.rs            # fcm 크레이트 (Android)
│   └── tests/
│       ├── api/                  # 통합 테스트
│       └── services/             # 서비스 단위 테스트
│
├── app/                          # Flutter 프론트엔드 (Android + iOS + Web)
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── main.dart             # 진입점 + 라우터 설정
│   │   ├── config/
│   │   │   ├── routes.dart       # GoRouter 경로 정의
│   │   │   ├── theme.dart        # 라이트/다크 테마
│   │   │   └── constants.dart    # API URL, 제한값 등
│   │   ├── models/               # 데이터 모델 (freezed)
│   │   │   ├── user.dart
│   │   │   ├── product.dart
│   │   │   ├── price_history.dart
│   │   │   ├── alert.dart
│   │   │   ├── notification.dart
│   │   │   └── point.dart
│   │   ├── providers/            # Riverpod 상태관리
│   │   │   ├── auth_provider.dart
│   │   │   ├── product_provider.dart
│   │   │   ├── alert_provider.dart
│   │   │   ├── favorites_provider.dart
│   │   │   └── notification_provider.dart
│   │   ├── services/             # API 호출 (dio)
│   │   │   ├── api_client.dart   # dio 인스턴스 + 인터셉터
│   │   │   ├── auth_service.dart
│   │   │   ├── product_service.dart
│   │   │   └── alert_service.dart
│   │   ├── screens/              # 22개 화면 (ui-architecture.md 기반)
│   │   │   ├── home/
│   │   │   │   ├── home_screen.dart
│   │   │   │   └── widgets/     # 인기검색어, 상품카드, 필터바
│   │   │   ├── product/
│   │   │   │   ├── product_detail_screen.dart
│   │   │   │   └── widgets/     # 가격 차트, AI 예측, 카드 할인
│   │   │   ├── search/
│   │   │   │   ├── search_screen.dart
│   │   │   │   └── search_result_screen.dart
│   │   │   ├── alert/
│   │   │   │   ├── alert_center_screen.dart
│   │   │   │   ├── alert_setting_screen.dart
│   │   │   │   ├── keyword_alert_screen.dart
│   │   │   │   └── category_alert_screen.dart
│   │   │   ├── favorites/
│   │   │   │   └── favorites_screen.dart
│   │   │   ├── rewards/
│   │   │   │   ├── rewards_screen.dart
│   │   │   │   ├── referral_screen.dart
│   │   │   │   └── daily_checkin_screen.dart
│   │   │   ├── auth/
│   │   │   │   ├── login_screen.dart
│   │   │   │   └── signup_screen.dart
│   │   │   ├── profile/
│   │   │   │   ├── my_page_screen.dart
│   │   │   │   ├── subscription_screen.dart
│   │   │   │   └── settings_screen.dart
│   │   │   ├── event/
│   │   │   │   └── event_screen.dart
│   │   │   ├── onboarding/
│   │   │   │   └── onboarding_screen.dart
│   │   │   └── web/
│   │   │       ├── web_landing_screen.dart
│   │   │       └── share_preview_screen.dart
│   │   └── widgets/              # 공용 위젯
│   │       ├── product_card.dart
│   │       ├── price_chart.dart  # fl_chart 래퍼
│   │       ├── filter_bar.dart
│   │       ├── sort_selector.dart
│   │       └── loading_indicator.dart
│   └── test/
│
└── .github/                      # (추후) CI/CD
```

---

## 2. 라이브러리 버전 (확정 후 고정)

### 2.1 Rust (server/Cargo.toml)

| 크레이트 | 용도 | 확인할 최신 버전 |
|----------|------|-----------------|
| axum | HTTP 프레임워크 | 0.8.x |
| tokio | 비동기 런타임 | 1.x |
| sqlx | DB (PostgreSQL) | 0.8.x |
| serde / serde_json | 직렬화 | 1.x |
| jsonwebtoken | JWT 인증 | 9.x |
| reqwest | HTTP 클라이언트 (크롤링) | 0.12.x |
| scraper | HTML 파싱 | 0.22.x |
| tower-governor | Rate Limiting | 0.6.x |
| tokio-cron-scheduler | 스케줄러 | 0.13.x |
| a2 | APNs 푸시 | 0.10.x |
| fcm | FCM 푸시 | 0.9.x |
| dotenvy | .env 로딩 | 0.15.x |
| thiserror | 에러 타입 | 2.x |
| tracing | 로깅 | 0.1.x |
| uuid | ID 생성 | 1.x |
| chrono | 날짜/시간 | 0.4.x |

### 2.2 Flutter (app/pubspec.yaml)

| 패키지 | 용도 | 확인할 최신 버전 |
|--------|------|-----------------|
| flutter_riverpod | 상태관리 | 2.x |
| go_router | 라우팅 | 14.x |
| dio | HTTP 클라이언트 | 5.x |
| fl_chart | 가격 차트 | 0.70.x |
| freezed / json_serializable | 모델 코드 생성 | 2.x / 6.x |
| flutter_secure_storage | 토큰 저장 | 9.x |
| firebase_messaging | FCM 수신 (Android) | 15.x |
| cached_network_image | 이미지 캐싱 | 3.x |
| shimmer | 로딩 스켈레톤 | 3.x |
| intl | 국제화 (숫자 포맷) | 0.19.x |

> **주의**: 구현 직전에 `cargo search` / `pub.dev` 에서 실제 최신 버전 확인 후 확정할 것.

---

## 3. 마일스톤

### 마일스톤 원칙
- **한 번에 하나만** — 마일스톤 완료 → Git 커밋 → 다음 마일스톤
- **3번 실패 → Git 롤백 → 범위 축소 재시도**
- 각 마일스톤 시작 전 STEP 3 (주석달기) 수행

---

### M1. 기반 구축 (목표: 4주)

서버 프로젝트 생성 + DB 마이그레이션 + 핵심 CRUD API + 크롤링 파이프라인.
플러터 프로젝트는 M2에서 시작.

#### M1-1. 프로젝트 스캐폴딩 + DB 마이그레이션
- [ ] `server/` Rust 프로젝트 생성 (`cargo init`)
- [ ] Cargo.toml 의존성 추가
- [ ] config.rs — DATABASE_URL, JWT_SECRET 등 환경변수
- [ ] db/mod.rs — PgPool 초기화
- [ ] `migrations/001_initial_schema.sql` — 23개 테이블 + 인덱스 + 파티셔닝
- [ ] `migrations/002_seed_data.sql` — shopping_malls (쿠팡, 네이버쇼핑), categories (18개)
- [ ] SQLx 마이그레이션 실행 검증

**파일:** `server/Cargo.toml`, `server/src/main.rs`, `server/src/config.rs`, `server/src/db/mod.rs`, `server/migrations/*`

#### M1-2. 에러 처리 + 공통 구조
- [ ] error.rs — `AppError` 통합 에러 (thiserror + IntoResponse)
- [ ] API 응답 포맷 통일: `{ "ok": bool, "data": T, "error": string? }`
- [ ] tracing 로깅 설정 (stdout JSON)

**파일:** `server/src/error.rs`, `server/src/main.rs`

#### M1-3. DB 모델 (SQLx FromRow)
- [ ] user.rs — users, user_devices
- [ ] product.rs — products, shopping_malls, categories
- [ ] price_history.rs — price_history
- [ ] alert.rs — price_alerts, category_alerts, keyword_alerts
- [ ] notification.rs — notifications
- [ ] point.rs — user_points, point_transactions
- [ ] reward.rs — referrals, daily_checkins
- [ ] event.rs — events, event_participations
- [ ] card_discount.rs — card_discounts
- [ ] ai_prediction.rs — ai_predictions
- [ ] popular_search.rs — popular_searches
- [ ] security.rs — api_access_logs, blocked_ips

**파일:** `server/src/db/models/*.rs`

#### M1-4. 인증 API
- [ ] POST `/api/auth/kakao` — 카카오 소셜 로그인
- [ ] POST `/api/auth/google` — 구글 소셜 로그인
- [ ] POST `/api/auth/apple` — 애플 소셜 로그인
- [ ] JWT 발급 + 갱신 로직
- [ ] auth.rs 미들웨어 — Authorization 헤더 검증
- [ ] 추천 코드 자동 생성 (가입 시)

**파일:** `server/src/api/routes/auth.rs`, `server/src/api/middleware/auth.rs`, `server/src/services/auth_service.rs`

#### M1-5. 상품 + 가격 API
- [ ] GET `/api/products/:id` — 상품 상세 (현재가, 최저/최고/평균, 트렌드)
- [ ] GET `/api/products/search?q=` — 키워드 검색
- [ ] POST `/api/products/url` — URL로 상품 추가
- [ ] GET `/api/products/:id/prices` — 가격 이력 (기간 필터)
- [ ] GET `/api/products/:id/prices/daily` — 요일별 집계

**파일:** `server/src/api/routes/products.rs`, `server/src/api/routes/prices.rs`, `server/src/services/product_service.rs`, `server/src/services/price_service.rs`

#### M1-6. 쿠팡 크롤링 파이프라인
- [ ] coupang.rs — 쿠팡파트너스 API 연동 (상품 검색, 딥링크)
- [ ] 가격 수집 로직 (reqwest + scraper)
- [ ] scheduler.rs — 크론 스케줄 등록 (매 N시간 가격 수집)
- [ ] 가격 변동 감지 → products 테이블 갱신 (current_price, price_trend 등)
- [ ] price_history INSERT

**파일:** `server/src/crawlers/coupang.rs`, `server/src/crawlers/scheduler.rs`

#### M1-7. 보안 미들웨어
- [ ] rate_limit.rs — tower-governor (IP별 60req/min, 검색 10req/min)
- [ ] bot_guard.rs — blocked_ips 테이블 조회 (인메모리 캐시 병행)
- [ ] api_access_logs INSERT 미들웨어

**파일:** `server/src/api/middleware/rate_limit.rs`, `server/src/api/middleware/bot_guard.rs`

#### M1-8. 기본 알림 + 푸시
- [ ] CRUD `/api/alerts/price` — 가격 알림 설정
- [ ] alert_service.rs — 가격 변동 시 활성 알림 평가
- [ ] notification_service.rs — 알림 생성 + 푸시 발송 트리거
- [ ] push/apns.rs — iOS 푸시 (a2)
- [ ] push/fcm.rs — Android 푸시 (fcm)

**파일:** `server/src/api/routes/alerts.rs`, `server/src/services/alert_service.rs`, `server/src/services/notification_service.rs`, `server/src/push/*.rs`

---

### M2. MVP 앱 개발 (목표: 8주)

Flutter 프로젝트 생성 + P0 핵심 화면 + 서버 API 연동.

#### M2-1. Flutter 프로젝트 + 공통 구조
- [ ] `app/` Flutter 프로젝트 생성
- [ ] pubspec.yaml 의존성 추가
- [ ] GoRouter 라우팅 (22 화면 경로 정의)
- [ ] Riverpod 프로바이더 구조
- [ ] dio API 클라이언트 (JWT 인터셉터)
- [ ] 테마 설정 (라이트/다크)
- [ ] freezed 모델 코드 생성 설정

#### M2-2. 인증 화면
- [ ] AUTH_LOGIN — 소셜 로그인 (카카오/구글/애플 버튼)
- [ ] AUTH_SIGNUP — 회원가입 (추천 코드 입력 포함)
- [ ] ONBOARDING — 최초 실행 소개 슬라이드

#### M2-3. 홈 화면
- [ ] HOME — 인기검색어 스크롤, 상품 카드 그리드, 필터/정렬
- [ ] product_card.dart — 공용 상품 카드 (이미지, 가격, 트렌드 아이콘, 배지)
- [ ] filter_bar.dart — 4종 필터 (품절임박/역대최저/하락추세/만원이하)
- [ ] sort_selector.dart — 4종 정렬

#### M2-4. 검색
- [ ] SEARCH — 키워드/URL 입력, 인기검색어, 최근검색
- [ ] SEARCH_RESULT — 결과 리스트 + 필터/정렬 + 무한 스크롤

#### M2-5. 상품 상세
- [ ] PRODUCT_DETAIL — 가격 그래프 (fl_chart), 상품 정보, 알림 설정 CTA
- [ ] price_chart.dart — fl_chart 래퍼 (줌/스크롤, 기간 선택)
- [ ] 하단 CTA — "N원 싸게 구매하기" 쿠팡파트너스 딥링크

#### M2-6. 알림 + 즐겨찾기
- [ ] ALERT_CENTER — 5탭 (가격/카테고리/키워드/보상/이벤트)
- [ ] ALERT_SETTING — 4단계 프리셋 (지정가/평균이하/최저근접/역대최저)
- [ ] FAVORITES — 즐겨찾기 목록 + 7일 추이 미니차트

#### M2-7. 마이페이지 + 설정
- [ ] MY_PAGE — 프로필, 구독 상태, 포인트 위젯, 메뉴 그룹
- [ ] SETTINGS — 알림 ON/OFF, 테마, 언어
- [ ] SUBSCRIPTION — 프리미엄 플랜 비교 + 구독 버튼

#### M2-8. 웹 대응
- [ ] WEB_LANDING — 비로그인 랜딩 (서비스 소개 + 앱 다운로드)
- [ ] 웹 GNB 레이아웃 (상단 메뉴)
- [ ] 카테고리 좌측 사이드바 (웹 전용)
- [ ] 반응형 그리드 (2열 앱 / 3~4열 웹)

---

### M3. 베타 출시 (목표: 2주)

- [ ] 전체 기능 QA
- [ ] 성능 프로파일링 (API 응답시간 <200ms)
- [ ] 쿠팡파트너스 연동 검증 (딥링크, 클릭 트래킹)
- [ ] 클로즈드 베타 배포 (TestFlight + Google Play 내부 테스트)
- [ ] 사용자 피드백 수집 + 크리티컬 버그 수정

---

### M4. 정식 출시 + P1 (목표: 4주)

#### M4-1. P1 기능 추가
- [ ] CATEGORY_ALERT — 카테고리 패시브 알림 등록/관리
- [ ] KEYWORD_ALERT — 키워드 핫딜 추적
- [ ] % 기반 글로벌 알림 설정
- [ ] 가격하락확률 게이지 (5단계 시각화)
- [ ] 요일별 가격 차트
- [ ] 단가 계산 (1정당, 100ml당)
- [ ] 카드 할인가 비교

#### M4-2. 스토어 출시
- [ ] App Store 심사 제출
- [ ] Google Play 출시
- [ ] 웹 정식 배포

---

### M5. 차별화 확장 — P2 (목표: 8주)

#### M5-1. AI + 보상
- [ ] AI 가격 예측 (Hopper 모델) — 프리미엄 전용
- [ ] 포인트/보상 시스템 (적립/사용)
- [ ] 출석체크 + 연속 보너스
- [ ] 친구 초대 (추천 코드)
- [ ] 이벤트/퀴즈

#### M5-2. 확장 기능
- [ ] 다중 쇼핑몰 비교 (네이버 검색 API lprice)
- [ ] 판매 속도 급증 선제 알림
- [ ] N일만에 최저가 배지
- [ ] 카카오톡 알림 채널
- [ ] 절약 금액 대시보드

---

## 4. 트레이드오프 기록

### 4.1 상태관리: Riverpod vs BLoC
- **선택: Riverpod**
- 근거: BLoC는 보일러플레이트 과다. Riverpod은 코드 생성 + 자동 캐싱 + 간결한 API. 1인 개발에 적합.
- 리스크: BLoC 대비 커뮤니티 규모는 작지만, Flutter 공식 추천 수준.

### 4.2 라우팅: GoRouter vs auto_route
- **선택: GoRouter**
- 근거: Flutter 팀 공식 패키지. 웹 딥링크 네이티브 지원. 코드 생성 없이 선언적 라우팅.

### 4.3 HTTP: dio vs http
- **선택: dio**
- 근거: 인터셉터 (JWT 자동 첨부, 토큰 갱신), 요청 취소, FormData 지원. http는 인터셉터 없음.

### 4.4 인증: JWT 자체 발급 vs OAuth2 서비스
- **선택: JWT 자체 발급**
- 근거: 소셜 로그인으로 사용자 확인 → 자체 JWT 발급. Firebase Auth 의존성 제거. Access + Refresh 토큰 패턴.
- 리스크: 토큰 관리 직접 구현 필요하나, 표준 패턴이므로 복잡도 낮음.

### 4.5 크롤링: 서버 내장 vs 별도 워커
- **선택: 서버 내장 (tokio-cron-scheduler)**
- 근거: MVP에서 별도 프로세스 운영은 과잉. Tokio 태스크로 백그라운드 실행. 규모 커지면 분리 가능.
- 리스크: 크롤링 부하가 API 응답에 영향 줄 수 있음 → Tokio 태스크 우선순위 조절 또는 셈머포어로 동시성 제한.

### 4.6 푸시: 자체 vs Firebase Cloud Messaging 전용
- **선택: 자체 시스템 (a2 + fcm 크레이트)**
- 근거: FCM 단독은 iOS에서 APNs 경유 필수. 직접 APNs/FCM 양쪽 관리하면 Firebase 의존성 제거 + 세밀한 제어.
- 리스크: APNs 인증서/키 관리 필요. P8 인증 키 사용으로 단순화.

### 4.7 가격 차트: fl_chart vs syncfusion
- **선택: fl_chart**
- 근거: MIT 라이선스 (무료). 줌/스크롤 지원. Syncfusion은 5개발자 이상 유료.
- 리스크: 커스터마이징 한계 시 직접 CustomPainter 구현 가능.

---

## 5. API 엔드포인트 설계 (M1~M2 범위)

### 인증
```
POST   /api/auth/kakao          # 카카오 로그인
POST   /api/auth/google         # 구글 로그인
POST   /api/auth/apple          # 애플 로그인
POST   /api/auth/refresh        # 토큰 갱신
DELETE /api/auth/logout         # 로그아웃 (디바이스 토큰 제거)
```

### 상품
```
GET    /api/products/:id                 # 상품 상세
GET    /api/products/search?q=&cat=&sort=&filter=  # 검색
POST   /api/products/url                 # URL로 상품 등록
GET    /api/products/:id/prices?from=&to=  # 가격 이력
GET    /api/products/:id/prices/daily    # 요일별 가격 집계
GET    /api/products/popular             # 인기 검색어
```

### 알림
```
GET    /api/alerts/price                 # 내 가격 알림 목록
POST   /api/alerts/price                 # 가격 알림 생성
PUT    /api/alerts/price/:id             # 수정
DELETE /api/alerts/price/:id             # 삭제
GET    /api/alerts/category              # 내 카테고리 알림 목록
POST   /api/alerts/category              # 카테고리 알림 생성
PUT    /api/alerts/category/:id          # 수정
DELETE /api/alerts/category/:id          # 삭제
GET    /api/alerts/keyword               # 키워드 알림 목록
POST   /api/alerts/keyword               # 키워드 알림 생성
DELETE /api/alerts/keyword/:id           # 삭제
```

### 즐겨찾기
```
GET    /api/favorites                    # 목록 (정렬: 추가순/가격/할인률)
POST   /api/favorites                    # 추가
DELETE /api/favorites/:product_id        # 삭제
```

### 알림 이력
```
GET    /api/notifications?tab=           # 알림 목록 (탭 필터)
PUT    /api/notifications/:id/read       # 읽음 처리
PUT    /api/notifications/read-all       # 전체 읽음
```

### 사용자
```
GET    /api/me                           # 내 정보
PUT    /api/me                           # 프로필 수정
POST   /api/me/devices                   # 디바이스 토큰 등록
DELETE /api/me                           # 회원 탈퇴 (soft delete)
```

### 포인트/보상
```
GET    /api/points                       # 잔액 + 요약
GET    /api/points/transactions?type=    # 거래 이력
POST   /api/checkin                      # 출석체크
GET    /api/referrals                    # 추천 현황
POST   /api/referrals/validate           # 추천 코드 확인
```

### 이벤트
```
GET    /api/events                       # 진행 중 이벤트
GET    /api/events/:id                   # 이벤트 상세
POST   /api/events/:id/participate       # 참여 (퀴즈 답변 등)
```

### 시스템
```
GET    /health                           # 헬스체크
GET    /api/categories                   # 카테고리 목록
```

---

## 6. 실행 순서 요약

```
현재 위치: STEP 2 (plan.md 초안 작성) ← 여기
    │
    ▼
STEP 2 반복: 인간 리뷰 → 인라인 메모 → AI 업데이트 (만족할 때까지)
    │
    ▼
STEP 3: M1-1 주석달기 ("migrations/001 에 주석으로 SQL 구조만 작성. 코드 쓰지 마")
    │
    ▼
STEP 4: M1-1 구현 → Git 커밋 → M1-2 주석 → 구현 → ... → M1 완료
    │
    ▼
M2 주석 → 구현 → ... → M5 까지 반복
```

---

> **다음 행동**: 이 plan.md를 리뷰하고, 인라인 메모로 피드백을 주세요.
> "메모 반영해서 업데이트해. 아직 구현하지 마."
