#!/usr/bin/env python3
"""
M1-1 주석(annotations) 교차 검증 스크립트

검증 대상:
1. schema-design.md ↔ m1-1-annotations.md 테이블/컬럼 일치 여부
2. plan.md ↔ m1-1-annotations.md 라이브러리/DB명 일치 여부
3. 인덱스 개수 및 누락 여부
4. 브랜드명 일관성 (PullCents 잔존 여부)
5. 파티셔닝 테이블 정합성
"""

import re
from pathlib import Path

DOCS = Path(__file__).parent.parent / "documents"

def load(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")

# ── 1. 테이블 수 검증 ──
def check_table_count():
    schema = load("schema-design.md")
    annot = load("m1-1-annotations.md")

    # schema-design.md 에서 선언한 테이블 수
    schema_declared = re.search(r"테이블 총괄\s*\((\d+)개\)", schema)
    schema_count = int(schema_declared.group(1)) if schema_declared else 0

    # annotations 에서 실제 기술된 테이블 (①~㉓)
    annot_tables = re.findall(r"####\s*[①-㉓㊀-㊿]\s+(\w+)", annot)

    print(f"\n{'='*60}")
    print("1. 테이블 수 검증")
    print(f"{'='*60}")
    print(f"  schema-design.md 선언: {schema_count}개")
    print(f"  m1-1-annotations.md 기술: {len(annot_tables)}개")

    if schema_count == len(annot_tables):
        print(f"  ✅ 일치")
    else:
        print(f"  ❌ 불일치! ({schema_count} vs {len(annot_tables)})")

    return annot_tables

# ── 2. 테이블명 매칭 ──
def check_table_names(annot_tables: list):
    schema = load("schema-design.md")

    # schema-design.md 에서 ### 2-N. 테이블명 패턴 추출
    schema_tables_raw = re.findall(r"###\s*2-\d+\.\s*(\w+)", schema)
    # "나머지 테이블" 같은 요약 섹션 제외
    schema_tables = [t for t in schema_tables_raw if t not in ("나머지")]

    # schema 에서 "나머지 테이블 (v0.1과 동일)" 에 언급된 테이블
    remainder_section = re.search(r"나머지 테이블.*?\n(.*?)(?:\n---|\Z)", schema, re.S)
    if remainder_section:
        extra = re.findall(r"\*\*(\w+)\*\*", remainder_section.group(1))
        schema_tables.extend(extra)

    schema_set = set(schema_tables)
    annot_set = set(annot_tables)

    print(f"\n{'='*60}")
    print("2. 테이블명 매칭")
    print(f"{'='*60}")

    # schema에 있는데 annotations에 없는 테이블
    missing_in_annot = schema_set - annot_set
    if missing_in_annot:
        print(f"  ⚠️  schema에 있지만 annotations에 없음: {missing_in_annot}")
    else:
        print(f"  ✅ schema의 모든 테이블이 annotations에 존재")

    # annotations에 있는데 schema에 없는 테이블
    extra_in_annot = annot_set - schema_set
    if extra_in_annot:
        print(f"  ⚠️  annotations에 있지만 schema에 없음: {extra_in_annot}")

# ── 3. 인덱스 수 검증 ──
def check_index_count():
    schema = load("schema-design.md")
    annot = load("m1-1-annotations.md")

    schema_indexes = re.findall(r"idx_\w+", schema)
    annot_indexes = re.findall(r"idx_\w+", annot)

    schema_idx_set = set(schema_indexes)
    annot_idx_set = set(annot_indexes)

    print(f"\n{'='*60}")
    print("3. 인덱스 검증")
    print(f"{'='*60}")
    print(f"  schema-design.md 인덱스: {len(schema_idx_set)}개")
    print(f"  m1-1-annotations.md 인덱스: {len(annot_idx_set)}개")

    missing = schema_idx_set - annot_idx_set
    if missing:
        print(f"  ❌ annotations에 누락된 인덱스: {missing}")
    else:
        print(f"  ✅ 모든 인덱스 일치")

    extra = annot_idx_set - schema_idx_set
    if extra:
        print(f"  ⚠️  annotations에만 있는 인덱스: {extra}")

# ── 4. 라이브러리 버전 정합성 ──
def check_libraries():
    plan = load("plan.md")
    annot = load("m1-1-annotations.md")

    print(f"\n{'='*60}")
    print("4. 라이브러리 버전 정합성")
    print(f"{'='*60}")

    libs_plan = {
        "axum": r"axum.*?(\d+\.\d+)",
        "tokio": r"tokio.*?(\d+\.x)",
        "sqlx": r"sqlx.*?(\d+\.\d+)",
        "moka": r"moka.*?(\d+\.\d+)",
        "sentry": r"sentry.*?(\d+\.\d+)",
        "dotenvy": r"dotenvy.*?(\d+\.\d+)",
        "thiserror": r"thiserror.*?(\d+\.x)",
        "tracing": r"tracing\s.*?(\d+\.\d+)",
    }

    for lib, pattern in libs_plan.items():
        plan_match = re.search(pattern, plan)
        annot_match = re.search(pattern, annot)
        plan_ver = plan_match.group(1) if plan_match else "NOT FOUND"
        annot_ver = annot_match.group(1) if annot_match else "NOT FOUND"

        status = "✅" if plan_ver == annot_ver else "❌"
        print(f"  {status} {lib}: plan={plan_ver}, annot={annot_ver}")

# ── 5. DB명 일관성 ──
def check_db_names():
    annot = load("m1-1-annotations.md")
    plan = load("plan.md")

    print(f"\n{'='*60}")
    print("5. DB명 일관성 (gapttuk)")
    print(f"{'='*60}")

    # pullcents 잔존 검사
    for name, doc in [("plan.md", plan), ("m1-1-annotations.md", annot)]:
        pullcents_refs = re.findall(r"pullcents", doc, re.I)
        if pullcents_refs:
            print(f"  ❌ {name}: 'pullcents' 잔존 {len(pullcents_refs)}건")
        else:
            print(f"  ✅ {name}: 'pullcents' 잔존 없음")

    # gapttuk 사용 확인
    for name, doc in [("plan.md", plan), ("m1-1-annotations.md", annot)]:
        gapttuk_refs = re.findall(r"gapttuk", doc)
        print(f"  📌 {name}: 'gapttuk' {len(gapttuk_refs)}건 사용 중")

# ── 6. 브랜드명 일관성 (전 문서) ──
def check_brand_consistency():
    print(f"\n{'='*60}")
    print("6. 브랜드명 일관성 (전체 documents/)")
    print(f"{'='*60}")

    for f in sorted(DOCS.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        pc_count = len(re.findall(r"PullCents", content))
        pc_lower = len(re.findall(r"pullcents", content, re.I)) - pc_count
        gt_count = len(re.findall(r"값뚝", content))

        issues = []
        if pc_count > 0:
            issues.append(f"PullCents={pc_count}")
        if pc_lower > 0:
            issues.append(f"pullcents(소문자)={pc_lower}")

        if issues:
            print(f"  ❌ {f.name}: {', '.join(issues)} 잔존 (값뚝={gt_count})")
        else:
            status = f"값뚝={gt_count}" if gt_count > 0 else "참조 없음"
            print(f"  ✅ {f.name}: OK ({status})")

# ── 7. 파티셔닝 테이블 정합성 ──
def check_partitioning():
    schema = load("schema-design.md")
    annot = load("m1-1-annotations.md")

    print(f"\n{'='*60}")
    print("7. 파티셔닝 테이블 정합성")
    print(f"{'='*60}")

    partition_tables = ["price_history", "api_access_logs"]
    for table in partition_tables:
        in_schema = f"{table}" in schema and "파티셔닝" in schema
        in_annot = f"{table}" in annot and "파티셔닝" in annot

        # 복합 PK 언급 확인
        composite_pk = re.search(rf"{table}.*?PK\s*=\s*\(id,\s*\w+\)", annot, re.S)

        print(f"  {'✅' if in_schema and in_annot else '❌'} {table}: "
              f"schema={'O' if in_schema else 'X'}, "
              f"annot={'O' if in_annot else 'X'}, "
              f"복합PK={'O' if composite_pk else 'X'}")

# ── 8. plan.md M1-1 체크리스트 vs annotations 섹션 매핑 ──
def check_plan_coverage():
    plan = load("plan.md")
    annot = load("m1-1-annotations.md")

    print(f"\n{'='*60}")
    print("8. plan.md M1-1 체크리스트 커버리지")
    print(f"{'='*60}")

    m1_1_items = [
        ("server/ Rust 프로젝트 생성", "Cargo.toml"),
        ("Cargo.toml 의존성", "dependencies"),
        ("config.rs", "config.rs"),
        ("db/mod.rs", "PgPool"),
        ("migrations/001_initial_schema.sql", "001_initial_schema"),
        ("migrations/002_seed_data.sql", "002_seed_data"),
        ("down migration", "down"),
        ("SQLx 마이그레이션 실행", "sqlx migrate"),
    ]

    for desc, keyword in m1_1_items:
        found = keyword.lower() in annot.lower()
        print(f"  {'✅' if found else '❌'} {desc}: {'커버됨' if found else '누락!'}")

# ── 9. 컬럼 상세 검증 (주요 테이블) ──
def check_column_details():
    schema = load("schema-design.md")
    annot = load("m1-1-annotations.md")

    print(f"\n{'='*60}")
    print("9. 주요 테이블 컬럼 상세 검증")
    print(f"{'='*60}")

    # users 테이블 주요 컬럼
    users_cols = [
        "email", "nickname", "auth_provider", "auth_provider_id",
        "point_balance", "referral_code", "referred_by",
        "created_at", "updated_at", "deleted_at"
    ]
    missing_user = [c for c in users_cols if c not in annot]
    print(f"  users: {'✅ 전체 일치' if not missing_user else '❌ 누락: ' + str(missing_user)}")

    # products 테이블 주요 컬럼
    products_cols = [
        "shopping_mall_id", "category_id", "external_product_id",
        "current_price", "lowest_price", "highest_price", "average_price",
        "price_trend", "days_since_lowest", "buy_timing_score", "sales_velocity"
    ]
    missing_prod = [c for c in products_cols if c not in annot]
    print(f"  products: {'✅ 전체 일치' if not missing_prod else '❌ 누락: ' + str(missing_prod)}")

    # notifications 테이블 주요 컬럼
    notif_cols = [
        "notification_type", "reference_id", "reference_type",
        "title", "body", "deep_link", "is_read"
    ]
    missing_notif = [c for c in notif_cols if c not in annot]
    print(f"  notifications: {'✅ 전체 일치' if not missing_notif else '❌ 누락: ' + str(missing_notif)}")

# ── 10. DoD 항목 검증 ──
def check_dod():
    annot = load("m1-1-annotations.md")

    print(f"\n{'='*60}")
    print("10. DoD (Definition of Done) 검증")
    print(f"{'='*60}")

    dod_items = [
        "cargo build",
        "sqlx migrate run",
        "sqlx migrate revert",
        "seed data",
        "/health",
        "파티셔닝",
        ".env.example",
        "Git 커밋",
    ]

    for item in dod_items:
        found = item.lower() in annot.lower()
        print(f"  {'✅' if found else '❌'} {item}")

# ── 실행 ──
if __name__ == "__main__":
    print("=" * 60)
    print("  M1-1 주석 교차 검증 리포트")
    print("  값뚝 (gapttuk) Project")
    print("=" * 60)

    tables = check_table_count()
    check_table_names(tables)
    check_index_count()
    check_libraries()
    check_db_names()
    check_brand_consistency()
    check_partitioning()
    check_plan_coverage()
    check_column_details()
    check_dod()

    print(f"\n{'='*60}")
    print("  검증 완료")
    print("=" * 60)
