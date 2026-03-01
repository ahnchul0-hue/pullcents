# PullCents 기술스택 비교 리서치

> **[DRAFT] 초안 문서** — 최종 기술 선택은 인간이 검토 후 확정
> 작성일: 2026-03-01
> 원칙: "기술스택은 최대한 단순하게" (0.instuments.md)
> 상태: 리서치 단계 — 아직 구현하지 마

---

## 목차
1. [모바일 프레임워크](#1-모바일-프레임워크)
2. [백엔드 프레임워크](#2-백엔드-프레임워크)
3. [ORM / 쿼리빌더](#3-orm--쿼리빌더)
4. [차트 라이브러리 (모바일)](#4-차트-라이브러리-모바일)
5. [푸시 알림 서비스](#5-푸시-알림-서비스)
6. [가격 크롤링/스크래핑](#6-가격-크롤링스크래핑)
7. [배포/인프라](#7-배포인프라)
8. [종합 추천 스택](#8-종합-추천-스택)

---

## 1. 모바일 프레임워크

### 후보 비교

| 기준 | React Native (bare) | Expo (React Native) | Flutter |
|---|---|---|---|
| **언어** | JavaScript/TypeScript | JavaScript/TypeScript | Dart |
| **렌더링** | 네이티브 UI 컴포넌트 | 네이티브 UI 컴포넌트 | Skia/Impeller 자체 렌더링 |
| **성능** | New Architecture (JSI, Fabric, TurboModules) 적용으로 크게 개선. Hermes V1 기본 엔진 (RN 0.84, 2026.02) | RN과 동일 (SDK 55부터 New Architecture 전용) | Dart → ARM 네이티브 코드 컴파일. 픽셀 단위 제어 |
| **생태계/커뮤니티** | npm 생태계 전체 활용. 미국 시장 채용 6:1 우위 | npm + Expo 전용 라이브러리. 공식 RN 시작 방법으로 권장 | pub.dev 생태계. 글로벌 시장점유율 ~46% |
| **학습 곡선** | React 경험 있으면 낮음 | React 경험 있으면 매우 낮음 (가장 쉬움) | Dart 학습 필요. 위젯 시스템 별도 학습 |
| **푸시 알림** | react-native-firebase, expo-notifications | expo-notifications (FCM/APNs 자동 처리) | firebase_messaging 패키지 |
| **차트 라이브러리** | Victory Native, gifted-charts, wagmi-charts 등 다수 | 동일 (RN 라이브러리 호환) | fl_chart, Syncfusion 등 |
| **딥링크/웹뷰** | react-native-webview + Linking API | 동일 (Expo Router v7 딥링크 지원) | webview_flutter + url_launcher |
| **빌드/배포** | Xcode/Android Studio 필요 | EAS Build (클라우드 빌드, 로컬 미설치 가능) | Xcode/Android Studio 필요 |
| **OTA 업데이트** | CodePush (MS 지원 종료 예정) | EAS Update (공식, 바이트코드 디핑으로 75% 크기 감소) | 불가 (네이티브 컴파일) |
| **웹 지원** | react-native-web (제한적) | Expo Router로 웹 지원 | Flutter Web (성능 이슈 존재) |

### 쿠팡파트너스 호환성

쿠팡파트너스 커미션 적립은 **어필리에이트 링크를 통한 쿠팡 앱/웹 이동**으로 이루어짐. 구현 방식:
- **WebView**: 쿠팡파트너스 링크를 WebView로 열거나 외부 브라우저/쿠팡 앱으로 리다이렉트
- **딥링크**: 쿠팡 앱이 설치된 경우 앱으로 직접 이동 (Linking API)
- React Native / Expo 모두 `react-native-webview` + `Linking` API로 구현 가능
- Flutter도 `webview_flutter` + `url_launcher`로 동일하게 가능
- 세 프레임워크 모두 쿠팡파트너스 딥링크 호환에 문제 없음

### 추천: Expo (React Native)

**이유:**
1. **단순성 원칙**: EAS Build/Update로 빌드 파이프라인이 가장 단순. 로컬에 Xcode/Android Studio 없이도 iOS/Android 빌드 가능
2. **푸시 알림**: expo-notifications가 FCM(Android) + APNs(iOS) 모두 추상화. 가장 적은 설정 코드
3. **OTA 업데이트**: 가격 알림 앱 특성상 빠른 버그 수정/UI 업데이트가 중요. EAS Update로 앱스토어 심사 없이 즉시 배포
4. **JavaScript/TypeScript**: 백엔드(Node.js)와 동일 언어로 풀스택 TypeScript 가능
5. **2026년 현재 Expo가 공식 RN 시작 방법**: New Architecture 전용, Hermes V1 기본, Expo Router v7
6. **생태계**: npm 생태계 전체 활용 가능. 차트, 웹뷰, 딥링크 라이브러리 풍부

**단점/리스크:**
- Expo에서 지원하지 않는 네이티브 모듈이 필요할 경우 eject 또는 config plugin 작성 필요 (현재는 대부분 커버)
- Flutter 대비 커스텀 애니메이션/UI 자유도가 낮을 수 있음 (가격 알림 앱에서는 문제 아님)

---

## 2. 백엔드 프레임워크

### 후보 비교

| 기준 | Next.js (API Routes) | NestJS | Fastify |
|---|---|---|---|
| **언어** | TypeScript (기본 지원) | TypeScript (기본, 데코레이터 기반) | TypeScript (지원, 필수는 아님) |
| **아키텍처** | 페이지 기반 + API Routes/Server Actions | MVC + 모듈/DI (Angular 스타일) | 플러그인 기반, 미니멀 |
| **성능** | Serverless Function 기반 (콜드스타트 존재) | Express 또는 Fastify 어댑터 위에서 동작 | 30K-76K req/s. Express 대비 30-40% 높은 처리량 |
| **크롤링/스케줄링** | API Routes에서 가능하나 long-running task에 부적합 (서버리스 타임아웃) | @nestjs/schedule (데코레이터로 cron 설정), @nestjs/bull (Redis 큐) 공식 지원 | fastify-cron, bullmq 플러그인 사용 가능 |
| **확장성** | 서버리스 auto-scale (Vercel 배포 시). 복잡한 백엔드 로직에는 부족 | 마이크로서비스 패턴 공식 지원. 대규모 팀/복잡한 앱에 적합 | 플러그인으로 확장. 중소규모에 적합 |
| **배포** | Vercel 원클릭 배포 | Docker/PM2. Railway, Fly.io 등 | Docker/PM2. 어디서든 배포 가능 |
| **학습 곡선** | React 경험 있으면 낮음 | 높음 (DI, 데코레이터, 모듈 패턴) | 낮음 (Express와 유사) |
| **프론트엔드 포함** | React SSR/SSG 포함 (풀스택) | 백엔드 전용 | 백엔드 전용 |

### 추천: Fastify

**이유:**
1. **단순성 원칙**: 가격 알림 앱 백엔드는 REST API + 크롤링 스케줄러 + 푸시 알림 발송이 핵심. NestJS의 DI/모듈 패턴은 과도한 추상화
2. **성능**: 가격 크롤링 요청이 많은 앱 특성상 높은 처리량이 유리
3. **TypeScript 지원**: 타입 안전한 라우트 정의 가능. JSON Schema 기반 자동 검증/직렬화
4. **long-running task**: Next.js API Routes와 달리 서버리스 타임아웃 없이 크롤링/스케줄링 가능
5. **플러그인 생태계**: bullmq, fastify-cron 등으로 필요한 기능만 추가
6. **배포 유연성**: Docker로 어디든 배포 가능 (Railway, Fly.io, AWS 등)

**단점/리스크:**
- NestJS 대비 구조화 가이드라인이 적음 (프로젝트 커지면 자체 아키텍처 규칙 필요)
- 생태계가 Express/NestJS보다 작음 (주요 기능은 커버)

**대안 고려:**
- 향후 프로젝트 규모가 커지면 Fastify를 NestJS 어댑터로 사용하는 마이그레이션 가능
- 웹 프론트엔드가 필요해지면 별도 Next.js 프론트 + Fastify API 구성 가능

---

## 3. ORM / 쿼리빌더

> 참고: 1-1.build_db.md에서 Prisma, Drizzle, Knex.js 3가지를 후보로 언급

### 후보 비교

| 기준 | Prisma | Drizzle | Knex.js |
|---|---|---|---|
| **접근 방식** | Schema-first (`.prisma` 파일에서 생성) | Code-first (TypeScript로 스키마 정의) | SQL 쿼리빌더 (ORM 아님) |
| **타입 안전성** | 매우 높음 (자동 생성된 타입) | 매우 높음 (TypeScript 네이티브) | 낮음 (수동 타입 정의 필요) |
| **PostgreSQL 호환** | 완벽 지원 | 완벽 지원 (identity column 등 최신 기능) | 완벽 지원 |
| **마이그레이션** | `prisma migrate` (자동 SQL 생성) | `drizzle-kit generate` + `push` | `knex migrate:make` (수동 SQL 작성) |
| **성능** | Rust 쿼리 엔진 사용. 서버리스에서 콜드스타트 이슈 | prepared statement로 raw pg 대비 1.15x 빠름. 번들 ~7.4KB | raw SQL에 가까운 성능 |
| **SQL 친화도** | 자체 쿼리 언어 (SQL과 다름) | SQL과 매우 유사한 문법 | SQL 쿼리빌더 (SQL 거의 그대로) |
| **번들 크기** | 큼 (Rust 엔진 바이너리 포함) | 매우 작음 (~7.4KB) | 작음 |
| **커뮤니티/생태계** | 가장 큼 (오래됨, 문서 풍부) | 빠르게 성장 중 (2023~ 급부상) | 안정적이나 정체 |
| **학습 곡선** | 중간 (Prisma Schema 언어 학습) | 낮음 (SQL 알면 바로 사용) | 낮음 (SQL 기반) |
| **관계 처리** | include/select로 편리 | relational query API 제공 | 수동 join 작성 |
| **서버리스 호환** | 콜드스타트 이슈 있음 (개선 중) | 최적 (최소 번들, 제로 콜드스타트) | 양호 |

### 추천: Drizzle

**이유:**
1. **단순성 원칙**: TypeScript로 스키마를 직접 정의. 별도 스키마 언어 없음. SQL을 아는 개발자에게 가장 직관적
2. **성능**: prepared statement 기반으로 raw pg보다 빠른 벤치마크. 번들 크기 7.4KB로 최소
3. **타입 안전성**: TypeScript 네이티브로 `any`/`unknown` 없이 완전한 타입 추론 (프로젝트 규칙 준수)
4. **PostgreSQL 최신 기능**: identity column, 최신 PostgreSQL 17 기능 지원
5. **마이그레이션**: `drizzle-kit generate`로 자동 SQL 생성 + `push`로 적용. Prisma만큼 편리
6. **2025-2026 트렌드**: NestJS + Drizzle, Fastify + Drizzle 조합이 새로운 표준으로 부상
7. **향후 확장**: Neon, Supabase 등 서버리스 PostgreSQL 호스팅으로 마이그레이션 시 최적

**단점/리스크:**
- Prisma 대비 생태계/문서가 작음 (빠르게 개선 중)
- Prisma Studio 같은 GUI 도구 없음 (drizzle-studio 개발 중)

---

## 4. 차트 라이브러리 (모바일)

> 가격 추이 그래프가 핵심 기능. 시계열 데이터 + 인터랙티브 + 커스터마이징이 중요

### Expo(React Native) 기준 후보 비교

| 기준 | react-native-gifted-charts | Victory Native | react-native-wagmi-charts |
|---|---|---|---|
| **차트 유형** | Line, Bar, Area, Pie, Donut, Stacked Bar | Line, Bar, Pie, Scatter, Candlestick 등 | Line, Candlestick (2종만) |
| **시계열 지원** | 날짜 X축, 스크롤 가능 | 날짜 X축, 커서/툴팁 지원 | 날짜 X축, 인터랙티브 커서 |
| **인터랙티브** | 터치 + 스크롤 + 포인터 | 커서, 라벨, 툴팁, 햅틱 피드백 | 커서 + 가격 표시 (주식 차트 특화) |
| **커스터마이징** | 높음 (그라디언트, 3D, 애니메이션) | 매우 높음 (테마, 컴포넌트 조합) | 중간 (미니멀 디자인) |
| **성능** | react-native-svg 기반 | Skia + Reanimated 기반 (고성능) | Reanimated + Gesture Handler |
| **번들 크기** | 중간 | 큼 (Skia 의존) | 작음 (가벼움) |
| **유지보수** | 활발 (2025년 업데이트) | 활발 (NearForm 관리) | 비교적 정체 |
| **GitHub Stars** | 2.5K+ | 10K+ (Victory 전체) | 2K+ |
| **가격 차트 적합도** | 높음 | 높음 | 매우 높음 (원래 주식 차트 목적) |

### 추천: react-native-gifted-charts

**이유:**
1. **단순성 원칙**: API가 직관적이고 학습 곡선이 낮음. 빠른 통합 가능
2. **가격 추이 그래프에 적합**: Line/Area 차트 + 스크롤 + 날짜 X축 + 포인터(터치 시 값 표시) 기능 기본 제공
3. **커스터마이징**: 그라디언트 배경, 영역 채우기, 점선 기준선 등 가격 차트에 필요한 시각 요소 풍부
4. **의존성 최소**: react-native-svg만 peer dependency (Victory는 Skia + Reanimated + Gesture Handler 필요)
5. **활발한 유지보수**: 2025년 기준 최신 React Native 버전 호환 확인
6. **확장성**: 향후 Bar 차트(카테고리별 비교), Pie 차트(지출 분석) 등 다양한 차트 유형으로 확장 가능

**대안:**
- 고성능/복잡한 인터랙션이 필요해지면 Victory Native로 마이그레이션 고려
- 단순 라인 차트만 필요한 MVP 단계에서는 wagmi-charts도 좋은 선택

---

## 5. 푸시 알림 서비스

### 후보 비교

| 기준 | Firebase Cloud Messaging (FCM) | OneSignal | AWS SNS |
|---|---|---|---|
| **무료 티어** | 완전 무료 (무제한 메시지) | 무료: 10,000 구독자, 무제한 메시지 | 무료: 월 100만 모바일 푸시 (12개월) |
| **iOS/Android** | 모두 지원 (APNs 프록시 포함) | 모두 지원 | 모두 지원 (설정 복잡) |
| **Expo 통합** | expo-notifications에 내장 지원 | onesignal-expo-plugin 존재 | 별도 네이티브 설정 필요 |
| **스케줄링** | 콘솔에서 예약 가능 | 콘솔 + API로 예약 가능 | EventBridge + Lambda 필요 |
| **타겟팅** | 토픽, 조건, 기기 그룹 | 세그먼트, 태그, 행동 기반 (매우 강력) | 토픽, 필터 정책 |
| **분석** | Firebase Analytics 연동 | 자체 분석 대시보드 | CloudWatch 연동 |
| **인앱 메시지** | Firebase In-App Messaging | 인앱 메시지 + 이메일 + SMS | 미지원 (별도 서비스) |
| **설정 난이도** | 중간 (Firebase 프로젝트 설정) | 낮음 (가장 쉬움) | 높음 (AWS 인프라 지식 필요) |
| **추가 기능** | Remote Config, A/B Testing, Analytics | 자동화 워크플로, A/B 테스트 | SMS, 이메일, HTTP 엔드포인트 |

### 추천: Firebase Cloud Messaging (FCM)

**이유:**
1. **단순성 원칙**: Expo의 expo-notifications가 FCM(Android) + APNs(iOS) 모두 추상화. 추가 SDK 불필요
2. **완전 무료**: 메시지 수 무제한. 스타트업 초기 비용 절감
3. **Expo 공식 지원**: Expo 문서에서 FCM 설정 가이드를 공식 제공. 검증된 안정성
4. **Firebase 생태계**: Analytics, Remote Config, Crashlytics 등 무료 도구와 자연스러운 연동
5. **Android 최적 지원**: 쿠팡 앱 사용자는 Android 비율이 높을 것으로 예상. FCM은 Android 네이티브 지원

**단점/리스크:**
- Google 종속성
- OneSignal 대비 세그먼트/자동화 기능이 제한적 (서버에서 직접 구현 가능)
- iOS에서는 APNs를 거치므로 약간의 지연 가능 (실무에서 무시 가능 수준)

**향후 고려:**
- 사용자 세그먼트 기반 고급 타겟팅이 필요해지면 OneSignal 검토
- Expo Push Notification Service를 중간 프록시로 활용하면 FCM/APNs 직접 관리 불필요

---

## 6. 가격 크롤링/스크래핑

### 6-1. 쿠팡 상품 가격 수집 방법

| 방법 | 설명 | 장점 | 단점 |
|---|---|---|---|
| **쿠팡파트너스 API** | 공식 API (developers.coupangcorp.com) | 합법적, 안정적, 어필리에이트 링크 자동 생성 | **시간당 10회 쿼터 제한**, 가격 필터링 미지원, 검색 API만 제공 (개별 상품 가격 조회 API 없음) |
| **웹 스크래핑** | 쿠팡 상품 페이지 직접 크롤링 | 개별 상품 가격/재고 정보 수집 가능 | 쿠팡 봇 감지 + 차단 위험, robots.txt/ToS 위반 가능성, IP 차단 리스크 |
| **하이브리드** | 파트너스 API(검색/링크) + 스크래핑(가격 추적) | 두 방법의 장점 결합 | 복잡도 증가, 스크래핑 리스크 존재 |

**현실적 접근:**
- 쿠팡파트너스 API만으로는 **실시간 가격 추적 불가** (시간당 10회 제한, 개별 상품 가격 API 없음)
- 경쟁사(폴센트, 로우차트 등)도 **웹 스크래핑 + 파트너스 API 병행**으로 추정
- 스크래핑 시 Puppeteer/Playwright로 동적 렌더링 후 가격 추출
- **User-Agent 로테이션, 프록시, 요청 간격 조절**로 차단 회피 필요
- 법적 리스크: 공개 데이터 수집은 대체로 허용되나, 쿠팡 ToS 확인 필요

### 6-2. 스크래핑 기술 스택

| 도구 | 용도 | 비고 |
|---|---|---|
| **Playwright** | 헤드리스 브라우저 기반 크롤링 | 동적 렌더링 페이지 지원, TypeScript 네이티브 |
| **Cheerio** | HTML 파싱 (정적 페이지) | 가벼움, 빠름. 동적 렌더링 불가 |
| **쿠팡파트너스 API** | 상품 검색 + 어필리에이트 링크 생성 | HMAC 인증, Node.js SDK 없음 (직접 구현) |

### 6-3. 스케줄링 비교

| 기준 | node-cron | BullMQ (Bull Queue) | pg_cron |
|---|---|---|---|
| **의존성** | 없음 (Node.js만) | Redis 필요 | PostgreSQL 확장 |
| **신뢰성** | 낮음 (프로세스 종료 시 유실) | 높음 (Redis에 작업 영속화, 자동 재시도) | 높음 (DB 내장, 크래시 후 복구) |
| **분산 처리** | 불가 (단일 프로세스) | 가능 (멀티 워커, 멀티 서버) | 불가 (DB 서버 내에서만) |
| **모니터링** | 없음 (직접 구현) | Bull Board UI, 작업 상태 추적 | cron.job_run_details 테이블 |
| **작업 유형** | 시간 기반 cron만 | cron + 지연 + 반복 + 우선순위 큐 | 시간 기반 cron + SQL 실행 |
| **적합한 용도** | 간단한 주기적 작업 | 크롤링 큐, 알림 발송 큐, 실패 재시도 | DB 유지보수, 통계 집계 |
| **설정 복잡도** | 매우 낮음 | 중간 (Redis 설정 필요) | 낮음 (PostgreSQL 확장 활성화) |

### 추천: BullMQ + pg_cron 병행

**이유:**
1. **BullMQ**: 가격 크롤링은 **실패 가능성이 높은 작업** (네트워크 오류, 봇 차단 등). BullMQ의 자동 재시도, 지수 백오프, 작업 영속화가 필수
2. **BullMQ**: 수만 개 상품 가격을 주기적으로 크롤링하려면 **큐 기반 분산 처리** 필요. 워커 수 조절로 스케일링
3. **pg_cron**: DB 수준의 작업 (가격 통계 집계, 오래된 데이터 정리, 일별 최저가 갱신)에 적합. 별도 애플리케이션 서버 불필요
4. **역할 분리**: BullMQ = 애플리케이션 레벨 작업 (크롤링, 알림 발송), pg_cron = DB 레벨 작업 (집계, 정리)

**단점/리스크:**
- BullMQ는 Redis 의존 (추가 인프라 비용). Railway/Fly.io에서 Redis 호스팅 가능
- pg_cron은 PostgreSQL 확장 설치 필요 (`shared_preload_libraries` 설정)

**MVP 단계 대안:**
- 초기에는 **node-cron으로 시작** → 상품 수/트래픽 증가 시 BullMQ로 마이그레이션
- pg_cron은 프로덕션 단계에서 도입

---

## 7. 배포/인프라

### 후보 비교

| 기준 | Vercel | Railway | Fly.io | AWS (EC2/ECS) |
|---|---|---|---|---|
| **무료 티어** | Hobby: 무료 (100GB BW, 100K 함수 호출) | Hobby: $5/월 ($5 크레딧 포함) | 소규모 사용 ~$5/월 면제 | 12개월 프리티어 (t2.micro) |
| **PostgreSQL** | 미지원 (외부 연동 필요) | 내장 지원 (원클릭) | Fly Postgres (볼륨 기반) | RDS ($15+/월) |
| **Redis** | 미지원 | 내장 지원 (원클릭) | Upstash 연동 | ElastiCache ($15+/월) |
| **서버 유형** | Serverless (함수 기반) | 컨테이너 (long-running) | 컨테이너 (edge) | 컨테이너/VM (완전 제어) |
| **long-running 작업** | 불가 (함수 타임아웃 10s-300s) | 가능 | 가능 | 가능 |
| **배포 방식** | Git push → 자동 배포 | Git push → 자동 배포 | flyctl deploy (Dockerfile) | ECS/Docker 수동 또는 CI/CD |
| **스케일링** | 자동 (서버리스) | 수동/자동 | 자동 (머신 수 조절) | 완전 커스텀 |
| **월 예상 비용** | $0-20 (프론트만) | $5-15 (앱+DB+Redis) | $5-20 (앱+DB) | $30+ (최소 구성) |
| **한국 리전** | 엣지 CDN (서울 팝) | 미국 서부/동부 | 도쿄 (NRT) | 서울 (ap-northeast-2) |
| **DX (개발자 경험)** | 최고 (프론트엔드) | 높음 (풀스택) | 중간 | 낮음 (학습 곡선 높음) |

### 추천: Railway

**이유:**
1. **단순성 원칙**: PostgreSQL + Redis + Node.js 서버를 **하나의 대시보드**에서 관리. 원클릭 설정
2. **long-running 지원**: Fastify 서버 + BullMQ 워커가 지속 실행. Vercel의 서버리스 타임아웃 문제 없음
3. **비용 효율**: 월 $5-15로 앱 서버 + PostgreSQL + Redis 운영 가능. AWS 대비 50-70% 절감
4. **배포 편의**: Git push → 자동 빌드/배포. Dockerfile 또는 Nixpacks 자동 감지
5. **통합 환경**: 환경변수, 로그, 메트릭스가 통합 대시보드에서 관리

**단점/리스크:**
- 한국 리전 없음 (미국 서부/동부). 한국 사용자 대상이므로 **레이턴시 고려 필요**
- 대규모 트래픽 시 AWS 대비 비용 경쟁력 감소
- Railway 자체의 안정성/지속성 리스크 (스타트업)

**레이턴시 완화 방안:**
- API 서버는 Railway (미국), 모바일 앱에서 캐싱 적극 활용
- 향후 트래픽 증가 시 AWS 서울 리전 or Fly.io 도쿄 리전으로 마이그레이션
- 또는 초기부터 **Fly.io (도쿄 리전)** 선택으로 아시아 레이턴시 최소화도 대안

**대안:**
- 레이턴시가 중요하다면 **Fly.io (도쿄 리전)** 우선 고려
- 프로덕션 규모 확장 시 **AWS 서울 리전** 검토

---

## 8. 종합 추천 스택

| 레이어 | 추천 | 차선 |
|---|---|---|
| **모바일 앱** | Expo (React Native) | Flutter |
| **백엔드 API** | Fastify | NestJS |
| **ORM** | Drizzle | Prisma |
| **데이터베이스** | PostgreSQL 17.9 (확정) | - |
| **차트** | react-native-gifted-charts | Victory Native |
| **푸시 알림** | Firebase Cloud Messaging (via expo-notifications) | OneSignal |
| **크롤링** | Playwright + Cheerio + 쿠팡파트너스 API | - |
| **작업 큐** | BullMQ (Redis) + pg_cron | node-cron (MVP) |
| **배포** | Railway (또는 Fly.io) | AWS |

### 스택 다이어그램 (텍스트)

```
[모바일 앱 - Expo/React Native]
    │
    │  REST API (HTTPS)
    ▼
[백엔드 - Fastify + TypeScript]
    │          │           │
    │          │           │
    ▼          ▼           ▼
[PostgreSQL] [Redis]   [Firebase]
 (Drizzle)  (BullMQ)   (FCM/APNs)
    │
    │  pg_cron (집계/정리)
    │
    ▼
[가격 크롤러 - Playwright/Cheerio]
    │
    │  쿠팡파트너스 API (어필리에이트 링크)
    ▼
[쿠팡 상품 페이지]
```

### 핵심 장점

1. **풀스택 TypeScript**: Expo + Fastify + Drizzle 모두 TypeScript. 타입 공유 가능, `any`/`unknown` 금지 원칙 준수
2. **단순성**: 각 레이어에서 가장 단순한 선택. 불필요한 추상화 최소
3. **비용 효율**: Railway에서 월 $5-15로 전체 백엔드 운영 가능
4. **확장 경로**: Fastify→NestJS, Railway→AWS, node-cron→BullMQ 등 점진적 마이그레이션 가능

---

## 참고 자료

### 모바일 프레임워크
- [Flutter vs React Native: Complete 2025 Framework Comparison Guide](https://www.thedroidsonroids.com/blog/flutter-vs-react-native-comparison)
- [Flutter vs. React Native: Which Framework to Choose in 2026?](https://webandcrafts.com/blog/flutter-vs-react-native)
- [Flutter vs React Native in 2026 - Pagepro](https://pagepro.co/blog/react-native-vs-flutter-which-is-better-for-cross-platform-app/)
- [React Native 0.84 - Hermes V1 by Default](https://reactnative.dev/blog/2026/02/11/react-native-0.84)
- [Expo SDK 55 - Expo Changelog](https://expo.dev/changelog/sdk-55)

### 백엔드 프레임워크
- [Express.js vs Fastify vs NestJS for Backend Development 2026](https://www.index.dev/skill-vs-skill/backend-nestjs-vs-expressjs-vs-fastify)
- [NestJS vs Fastify - Better Stack](https://betterstack.com/community/guides/scaling-nodejs/nestjs-vs-fastify/)
- [Best TypeScript Backend Frameworks in 2026 - Encore](https://encore.dev/articles/best-typescript-backend-frameworks)

### ORM / 쿼리빌더
- [Drizzle vs Prisma: Which TypeScript ORM Should You Use in 2026?](https://www.bytebase.com/blog/drizzle-vs-prisma/)
- [Node.js ORMs in 2025: Prisma, Drizzle, TypeORM, and Beyond](https://thedataguy.pro/blog/2025/12/nodejs-orm-comparison-2025/)
- [Drizzle ORM PostgreSQL Best Practices Guide 2025](https://gist.github.com/productdevbook/7c9ce3bbeb96b3fabc3c7c2aa2abc717)
- [Drizzle ORM - Benchmarks](https://orm.drizzle.team/benchmarks)

### 차트 라이브러리
- [Top 10 React Native Chart Libraries for 2025 - LogRocket](https://blog.logrocket.com/top-react-native-chart-libraries/)
- [Top 9 React Native Chart Libraries for Data Visualization in 2025](https://blog.openreplay.com/react-native-chart-libraries-2025/)
- [react-native-gifted-charts - Gifted Charts](https://gifted-charts.web.app/)

### 푸시 알림
- [Firebase Cloud Messaging vs OneSignal 2026](https://ably.com/compare/fcm-vs-onesignal)
- [Amazon SNS vs Firebase Cloud Messaging 2026](https://ably.com/compare/amazon-sns-vs-fcm)
- [Expo Push Notifications Overview](https://docs.expo.dev/push-notifications/overview/)

### 크롤링/스케줄링
- [쿠팡파트너스 API - Coupang Open API](https://developers.coupangcorp.com/hc/en-us)
- [Schedulers in Node: A Comparison - Better Stack](https://betterstack.com/community/guides/scaling-nodejs/best-nodejs-schedulers/)
- [pg_cron - GitHub](https://github.com/citusdata/pg_cron)
- [BullMQ - GitHub](https://github.com/OptimalBits/bull)

### 배포/인프라
- [Railway vs Vercel - Railway Docs](https://docs.railway.com/platform/compare-to-vercel)
- [Railway vs Fly - Railway Docs](https://docs.railway.com/platform/compare-to-fly)
- [Vercel Alternatives 2026 - DigitalOcean](https://www.digitalocean.com/resources/articles/vercel-alternatives)
