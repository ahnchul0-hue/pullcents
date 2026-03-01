# PullCents 기술스택 비교 리서치

> **[DRAFT] v0.2** — 최종 기술 선택은 인간이 검토 후 확정
> 작성일: 2026-03-01 | 갱신: 2026-03-01
> 원칙: "기술스택은 최대한 단순하게" (0.instuments.md)
> 상태: 리서치 단계 — 아직 구현하지 마
> **확정 방향: Flutter + Rust + PostgreSQL (로컬) + 자체 푸시**

---

## 확정 사항

| 레이어 | 선택 | 비고 |
|--------|------|------|
| **모바일 앱** | Flutter (Dart) | Android + iOS + 웹 |
| **백엔드** | Rust | 고성능, 단일 바이너리 |
| **데이터베이스** | PostgreSQL 17.9 (로컬) | 이미 설치됨 (localhost:5432) |
| **푸시 알림** | 자체 시스템 | APNs 직접 + FCM HTTP API 직접 호출 |
| **배포** | 로컬 바이너리 + systemd | Docker 없이 시작 |

---

## 1. Rust 백엔드 프레임워크

### 후보 비교

| 기준 | Actix Web | Axum | Rocket |
|------|-----------|------|--------|
| **성능** | 최고 (10-15% 빠름) | Actix 근접, 메모리 효율 최고 | 3위 |
| **생태계** | 성숙, crate 풍부 | crates.io DL 23M (Actix 5.8M), 가장 활발 | 성장 중이나 상대적 소규모 |
| **학습 곡선** | 중간~높음 (Actor 모델) | 낮음~중간 (직관적 라우터) | 가장 낮음 (매크로 기반) |
| **PostgreSQL** | SQLx/Diesel 가능 | SQLx와 최적 궁합 | 내장 DB 풀 |
| **비동기** | Tokio 기반 커스텀 런타임 | Tokio 네이티브 (Tokio 팀 개발) | 0.5부터 비동기 |
| **미들웨어** | 자체 시스템 | Tower 생태계 전체 활용 | 자체 Fairing |
| **2026 활발함** | 활발하나 성장 둔화 | 가장 활발, v0.8.8 (2026.01) | 유지보수 수준 |

### 추천: **Axum**

- Tokio 팀이 직접 개발 → Tokio 생태계와 완벽 호환
- Tower 미들웨어 재사용 (인증, 로깅, 압축, 레이트리밋)
- crates.io DL이 Actix의 4배 → 2026년 Rust 웹 프레임워크 사실상 표준
- SQLx와 조합이 가장 잘 문서화됨 (realworld-axum-sqlx 등)
- Actix 대비 10-15% 느리지만 가격 알림 앱에서 무의미한 차이

---

## 2. Rust PostgreSQL 클라이언트

### 후보 비교

| 기준 | SQLx | Diesel | SeaORM |
|------|------|--------|--------|
| **PostgreSQL 17** | 지원 (비동기 네이티브) | 지원 (동기, diesel-async 별도) | 지원 (SQLx 기반) |
| **마이그레이션** | sqlx-cli 내장 | diesel_cli 내장 (가장 성숙) | sea-orm-cli 내장 |
| **타입 안전성** | 컴파일 타임 SQL 검증 (매크로) | 컴파일 타임 DSL 검증 (가장 강력) | 런타임 수준 |
| **비동기** | 네이티브 async | 동기 기본 (async 추가 의존성) | 네이티브 async |
| **학습 곡선** | 낮음 (SQL 직접 작성) | 높음 (Diesel DSL 학습) | 중간 (ActiveRecord) |
| **Axum 궁합** | 최적 (같은 Tokio 생태계) | 가능하나 async 어댑터 필요 | 가능 |
| **쿼리 방식** | 순수 SQL + 컴파일타임 체크 | Rust DSL (query builder) | ORM + raw SQL |

### 추천: **SQLx**

- 순수 SQL 작성 + `query!` 매크로로 컴파일 타임에 PostgreSQL과 타입/컬럼 검증
- DSL 학습 비용 없이 타입 안전성 확보
- Axum과 같은 Tokio 생태계, 네이티브 async
- 커넥션 풀링 내장 (PgPool)
- 가격 알림 앱은 간단한 CRUD + 집계 쿼리 → ORM보다 직접 SQL이 효율적

---

## 3. Flutter 차트 라이브러리

### 후보 비교

| 기준 | fl_chart | syncfusion_flutter_charts | community_charts_flutter |
|------|----------|--------------------------|--------------------------|
| **시계열 라인 차트** | 지원 | 지원 (30+ 차트 타입) | 지원 |
| **인터랙티브** | 줌/스크롤 지원 (2025.04 추가) | 네이티브 (trackball, crosshair) | 기본 수준 |
| **커스터마이징** | 매우 높음 (선언적 API) | 높음 (엔터프라이즈급) | 중간 |
| **Area 차트** | 지원 | 지원 | 지원 |
| **라이선스** | MIT (완전 무료) | 상업 라이선스 (매출 $1M 미만 무료) | Apache 2.0 |
| **유지보수** | 활발 (2025년 다수 릴리즈) | 활발 (상업 제품) | 거의 없음 (Google 포기 후 포크) |

### 추천: **fl_chart**

- MIT 라이선스 — 라이선스 걱정 없음
- 2025.04 줌/스크롤 추가 — 가격 추이 그래프 핵심 인터랙션 해결
- 선언적 API로 Flutter와 자연스러운 통합
- Line + Area + 터치 인터랙션 모두 충족
- 경량, 활발한 유지보수

---

## 4. 자체 푸시 알림 시스템

### Android에서 FCM 없이 푸시가 가능한가?

**가능하지만 실용적이지 않다.**

| 방식 | 앱 종료 시 작동 | 배터리 | 구현 난이도 |
|------|---------------|--------|-----------|
| FCM HTTP API 직접 호출 | 작동 | 최소 | 중간 |
| APNs 직접 (iOS) | 작동 | 최소 | 중간 |
| WebSocket | 앱 살아있을 때만 | 높음 | 중간 |
| UnifiedPush | 작동 (별도 앱 필요) | 중간 | 높음 |

### 추천: 하이브리드 자체 시스템

```
[PullCents 자체 푸시 아키텍처]

Rust 서버 (Axum)
    ├── iOS:  APNs 직접 연동 (a2 crate) ──→ iOS 기기
    ├── Android: FCM HTTP v1 API 직접 호출 (fcm crate) ──→ Android 기기
    └── 웹:  Web Push (VAPID) ──→ 브라우저

앱 포그라운드: WebSocket/SSE로 실시간 가격 업데이트
```

**핵심 포인트:**
- Firebase Console/SDK를 거치지 않고 **Rust에서 직접 FCM HTTP v1 API 호출** → "자체 푸시"의 실용적 형태
- iOS는 APNs가 유일한 공식 방법 → `a2` crate로 직접 연동
- 알림 스케줄링, 타겟팅, 로직 모두 Rust 서버에서 자체 관리
- 사용자 토큰만 관리하면 되므로 데이터가 Firebase에 노출되지 않음

**Rust 라이브러리:**
- `a2` — 비동기 APNs 클라이언트
- `fcm` — FCM HTTP v1 API 비동기 클라이언트

---

## 5. Flutter ↔ Rust 통신

| 방식 | 장점 | 단점 | 적합도 |
|------|------|------|--------|
| **REST API (JSON)** | 가장 단순, 디버깅 쉬움, 웹 호환 | 타입 안전성 수동 | **가장 적합** |
| gRPC | 타입 안전, 고성능 | 웹 호환 복잡 | 과도함 |
| GraphQL | 유연한 쿼리 | 서버 구현 복잡 | 불필요 |

- flutter_rust_bridge(FFI) 불필요 — Rust가 별도 서버로 동작하므로 HTTP API로 통신
- Flutter에서 `http` 또는 `dio` 패키지 사용
- 쿠팡파트너스 딥링크: 서버에서 변환 후 `url_launcher`로 쿠팡 앱/브라우저 오픈

---

## 6. 가격 크롤링 (Rust 기반)

### 도구 비교

| 도구 | 용도 | 장점 | 단점 |
|------|------|------|------|
| **reqwest + scraper** | 정적 HTML 파싱 | 가볍고 빠름, 비동기 | JS 렌더링 불가 |
| **rust-headless-chrome** | JS 렌더링 필요 시 | 동적 콘텐츠 처리 | 리소스 소모 큼 |
| **spider** | 대규모 크롤링 | 200-1000x 빠름 | 단순 작업엔 과도 |

### 추천: **reqwest + scraper** (기본) + headless Chrome (필요 시)

- 쿠팡파트너스 API 우선 활용 (합법적, 안정적)
- API 한계(시간당 10회) 보완으로 reqwest + scraper 병행
- JS 렌더링 필요한 경우에만 headless Chrome

---

## 7. 작업 스케줄링 (Rust 기반)

| 도구 | 유형 | 장점 | 단점 |
|------|------|------|------|
| **tokio-cron-scheduler** | 인프로세스 cron | Tokio 네이티브, PG 저장 옵션 | 프로세스 재시작 시 리셋 |
| **pg_cron** | PostgreSQL 확장 | DB 레벨 스케줄링 | SQL 함수만 실행 |
| **pgmq** | PostgreSQL 메시지 큐 | Rust로 작성된 PG 확장 | pgrx 빌드 필요 |

### 추천: **tokio-cron-scheduler**

- Axum 서버 프로세스 안에서 바로 실행
- Redis 추가 인프라 불필요 → "로컬 우선, 단순하게" 원칙
- PostgreSQL에 작업 상태 저장 옵션 있음

---

## 8. 배포/인프라 (로컬 우선)

### 현재 구조

```
[로컬 배포]

PostgreSQL 17.9 (localhost:5432, 이미 설치)
    │
cargo build --release → 단일 바이너리 (~10-30MB)
    │
systemd 서비스로 자동 시작/재시작
```

### 향후 클라우드 전환 옵션

| 서비스 | 비용 | 장점 |
|--------|------|------|
| Fly.io | $5-20/월 | Rust 바이너리 직접 배포, 도쿄 리전 |
| AWS Lightsail | $3.50~/월 | VPS 스타일, 서울 리전 |
| Railway | $5-15/월 | Docker 기반, PG 내장 |

### 방향: Docker 없이 직접 실행 → 향후 Docker Compose 전환

- Rust 바이너리의 장점: 런타임 의존성 없음, 단일 파일 배포
- 개발 중: `cargo watch -x run` (핫 리로드)
- 클라우드 전환 시점에 Dockerfile 작성

---

## 9. 종합 확정 스택

| 레이어 | 선택 | 이유 |
|--------|------|------|
| **모바일 앱** | **Flutter** | Android + iOS + 웹, Dart 자체 렌더링 |
| **백엔드** | **Axum** (Rust) | Tokio 네이티브, Tower 미들웨어, 커뮤니티 1위 |
| **DB 클라이언트** | **SQLx** | 컴파일타임 SQL 검증, Axum과 최적 궁합 |
| **데이터베이스** | **PostgreSQL 17.9** | 이미 설치됨, 로컬 |
| **차트** | **fl_chart** | MIT, 줌/스크롤, Flutter 네이티브 |
| **푸시 알림** | **APNs 직접 (a2) + FCM HTTP API (fcm)** | 자체 제어, Firebase SDK 불필요 |
| **앱-서버 통신** | **REST API (JSON)** | 가장 단순, 웹 호환 |
| **크롤링** | **reqwest + scraper** + 쿠팡파트너스 API | 경량, API 우선 |
| **스케줄링** | **tokio-cron-scheduler** | 인프로세스, Redis 불필요 |
| **배포** | **단일 바이너리 + systemd** | 로컬 우선, 의존성 제로 |

### 스택 다이어그램

```
[Flutter App (Dart)]
    │
    │  REST API (HTTPS/JSON)
    ▼
[Axum Server (Rust)]
    ├── SQLx ──→ PostgreSQL 17.9 (localhost)
    ├── a2 ──→ APNs (iOS 푸시)
    ├── fcm ──→ FCM HTTP API (Android 푸시)
    ├── Web Push (VAPID) ──→ 브라우저 푸시
    ├── tokio-cron-scheduler ──→ 가격 크롤링 스케줄
    └── reqwest + scraper ──→ 쿠팡 가격 수집
         + 쿠팡파트너스 API ──→ 딥링크 생성
```

### 핵심 장점

1. **성능**: Rust 단일 바이너리, 메모리 효율, 높은 동시성
2. **단순성**: 외부 서비스 최소화 (Redis 없음, Firebase SDK 없음)
3. **로컬 우선**: PostgreSQL + Rust 바이너리만으로 전체 백엔드 운영
4. **안전성**: Rust 컴파일러 + SQLx 컴파일타임 검증으로 런타임 에러 최소화
5. **배포 간결**: 단일 실행 파일 + systemd = 프로덕션 준비 완료
