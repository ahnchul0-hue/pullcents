#!/usr/bin/env python3
"""
PullCents 문서 교차 검증 스크립트 v2
- PRD ↔ Schema ↔ UI Architecture ↔ Tech Stack 간 누락/불일치 탐지
- 아직 구현하지 마. 설계 문서 검증용.
"""
import re
from pathlib import Path
from collections import defaultdict

DOCS_DIR = Path(__file__).parent.parent / "documents"

def read_file(name):
    return (DOCS_DIR / name).read_text(encoding="utf-8")

# ─────────────────────────────────────────────
# 1. 파서
# ─────────────────────────────────────────────

def parse_schema_summary_tables(text):
    """테이블 총괄 섹션에서 테이블명만 추출 (그룹 행만)"""
    tables = set()
    in_summary = False
    for line in text.split("\n"):
        if "테이블 총괄" in line:
            in_summary = True
            continue
        if in_summary and line.startswith("---"):
            break
        if in_summary and line.startswith("| **"):
            # "| **핵심** | users, user_devices | 설명 |" 에서 2번째 컬럼 추출
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                col2 = parts[2]  # "users, user_devices"
                for t in col2.split(","):
                    t = t.strip()
                    # 순수 테이블명만 (영문 소문자 + 언더스코어)
                    if re.match(r'^[a-z_]+$', t):
                        tables.add(t)
    return tables

def parse_schema_detail_tables(text):
    """### 2-N. 테이블명 패턴으로 상세 테이블 추출"""
    tables = set()
    for m in re.finditer(r"### 2-\d+\.\s+(\w+)", text):
        name = m.group(1)
        if name not in ("나머지",):
            tables.add(name)
    return tables

def parse_schema_remainder_tables(text):
    """나머지 테이블 섹션에서 추출"""
    tables = set()
    in_remainder = False
    for line in text.split("\n"):
        if "나머지 테이블" in line:
            in_remainder = True
            continue
        if in_remainder and line.startswith("---"):
            break
        if in_remainder:
            m = re.match(r"- \*\*(\w+)\*\*", line)
            if m:
                tables.add(m.group(1))
    return tables

def parse_er_tables(text):
    """ER 다이어그램에서 테이블명 추출"""
    tables = set()
    in_er = False
    for line in text.split("\n"):
        if "erDiagram" in line:
            in_er = True
            continue
        if in_er and line.strip() == "```":
            break
        if in_er:
            # "users ||--o{ user_devices" 등에서 테이블명
            for m in re.findall(r'\b([a-z][a-z_]+)\b', line):
                if m not in ("referrer",):
                    tables.add(m)
    return tables

def parse_ui_screens(text):
    """UI 화면 목록 테이블에서 화면 ID 추출"""
    screens = set()
    # "| N | `SCREEN_ID` | 화면명 |" 패턴
    for m in re.finditer(r'\|\s*\d+\s*\|\s*`(\w+)`', text):
        screens.add(m.group(1))
    return screens

def parse_prd_features(text):
    """PRD에서 P0~P3 기능명 추출"""
    features = defaultdict(list)
    current_p = None
    for line in text.split("\n"):
        if re.match(r"### P\d", line):
            m = re.match(r"### (P\d)", line)
            if m:
                current_p = m.group(1)
        elif line.startswith("### ") or line.startswith("## "):
            current_p = None  # P 섹션 종료
        elif current_p and line.startswith("| **"):
            m = re.match(r"\|\s*\*\*([^*]+)\*\*\s*\|", line)
            if m:
                features[current_p].append(m.group(1))
    return features

def parse_tech_stack_final(text):
    """종합 확정 스택 테이블 추출"""
    stack = {}
    in_stack = False
    for line in text.split("\n"):
        if "종합 확정 스택" in line:
            in_stack = True
            continue
        if in_stack and line.startswith("###"):
            break
        if in_stack and line.startswith("| **"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                layer = parts[1].replace("**", "").strip()
                choice = parts[2].replace("**", "").strip()
                stack[layer] = choice
    return stack

def parse_prd_tech(text):
    """PRD 기술 인프라 섹션"""
    stack = {}
    in_tech = False
    for line in text.split("\n"):
        if "기술 인프라" in line:
            in_tech = True
            continue
        if in_tech and (line.startswith(">") or line.startswith("---")):
            break
        if in_tech and line.startswith("| **"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                layer = parts[1].replace("**", "").strip()
                choice = parts[2].replace("**", "").strip()
                stack[layer] = choice
    return stack

def parse_schema_feature_map(text):
    """스키마 기능 매핑 섹션"""
    features = set()
    in_map = False
    for line in text.split("\n"):
        if "신규 기능 → 스키마 매핑" in line:
            in_map = True
            continue
        if in_map and line.startswith("---"):
            break
        if in_map and line.startswith("| **"):
            m = re.match(r"\|\s*\*\*([^*]+)\*\*\s*\|", line)
            if m:
                features.add(m.group(1))
    return features

def parse_ui_priority(text):
    """부록 A MVP/v2 분류"""
    mvp, v2_only = [], []
    in_appendix = False
    for line in text.split("\n"):
        if "부록 A" in line:
            in_appendix = True
            continue
        if in_appendix and line.startswith("## "):
            break
        if in_appendix and re.match(r"\|\s*P\d", line):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                priority, feature, is_mvp, is_v2 = parts[1], parts[2], parts[3], parts[4]
                if is_mvp == "O":
                    mvp.append((priority, feature))
                elif is_v2 == "O":
                    v2_only.append((priority, feature))
    return mvp, v2_only


# ─────────────────────────────────────────────
# 2. 검증
# ─────────────────────────────────────────────

def main():
    schema = read_file("schema-design.md")
    ui = read_file("ui-architecture.md")
    prd = read_file("prd.md")
    tech = read_file("tech-stack-research.md")

    issues, warnings, info = [], [], []

    # ── A. 스키마 테이블 일관성 ──
    summary_tables = parse_schema_summary_tables(schema)
    detail_tables = parse_schema_detail_tables(schema)
    remainder_tables = parse_schema_remainder_tables(schema)
    er_tables = parse_er_tables(schema)
    all_schema_tables = detail_tables | remainder_tables

    stated_m = re.search(r"테이블 총괄\s*\((\d+)개\)", schema)
    stated = int(stated_m.group(1)) if stated_m else 0

    info.append(f"[스키마] 명시: {stated}개 | 총괄: {len(summary_tables)}개 | 상세: {len(detail_tables)}개 | 나머지: {len(remainder_tables)}개 | 합계: {len(all_schema_tables)}개")

    if stated != len(all_schema_tables):
        issues.append(f"[스키마] 명시 테이블 수({stated}) ≠ 실제({len(all_schema_tables)}): {sorted(all_schema_tables)}")

    missing_from_summary = all_schema_tables - summary_tables
    if missing_from_summary:
        warnings.append(f"[스키마] 상세/나머지에 있지만 총괄에 없음: {sorted(missing_from_summary)}")

    missing_from_detail = summary_tables - all_schema_tables
    if missing_from_detail:
        issues.append(f"[스키마] 총괄에 있지만 상세에 없음: {sorted(missing_from_detail)}")

    # ER 누락
    security_tables = {"api_access_logs", "blocked_ips"}
    misc_tables = {"popular_searches"}
    expected_er = all_schema_tables - security_tables - misc_tables
    er_missing = expected_er - er_tables
    if er_missing:
        warnings.append(f"[스키마] ER 다이어그램 누락 (비보안): {sorted(er_missing)}")

    # ── B. UI 화면 일관성 ──
    screens = parse_ui_screens(ui)
    stated_screens_m = re.search(r"총\s*(\d+)개\s*화면", ui)
    stated_screens = int(stated_screens_m.group(1)) if stated_screens_m else 0

    info.append(f"[UI] 명시: {stated_screens}개 | 파싱: {len(screens)}개 — {sorted(screens)}")

    if stated_screens != len(screens):
        issues.append(f"[UI] 명시 화면 수({stated_screens}) ≠ 파싱({len(screens)})")

    # ── C. PRD 기능 ↔ UI 화면 ──
    prd_features = parse_prd_features(prd)
    total_prd = sum(len(v) for v in prd_features.values())
    info.append(f"[PRD] P0={len(prd_features.get('P0',[]))} P1={len(prd_features.get('P1',[]))} P2={len(prd_features.get('P2',[]))} P3={len(prd_features.get('P3',[]))} 합계={total_prd}")

    feature_to_screen = {
        "가격 추적 그래프": "PRODUCT_DETAIL",
        "최저가 알림": "ALERT_SETTING",
        "상품 검색": "SEARCH",
        "카테고리 패시브 알림": "CATEGORY_ALERT",
        "키워드 자동 모니터링": "KEYWORD_ALERT",
        "가격하락확률 게이지": "PRODUCT_DETAIL",
        "요일별 가격 차트": "PRODUCT_DETAIL",
        "필터/정렬": "HOME",
    }
    for feat, scr in feature_to_screen.items():
        if scr not in screens:
            issues.append(f"[PRD→UI] '{feat}'의 화면 '{scr}'이 UI 파싱에서 누락됨")

    # ── D. 스키마 ↔ UI 매핑 ──
    table_to_screens = {
        "users": ["MY_PAGE"],
        "products": ["HOME"],
        "price_alerts": ["ALERT_SETTING"],
        "category_alerts": ["CATEGORY_ALERT"],
        "keyword_alerts": ["KEYWORD_ALERT"],
        "notifications": ["ALERT_CENTER"],
        "ai_predictions": ["PRODUCT_DETAIL"],
        "card_discounts": ["PRODUCT_DETAIL"],
        "user_points": ["REWARDS"],
        "referrals": ["REFERRAL"],
        "daily_checkins": ["DAILY_CHECKIN"],
        "events": ["EVENT"],
        "popular_searches": ["HOME"],
        "roulette_results": ["REWARDS"],
    }
    for table, expected in table_to_screens.items():
        for scr in expected:
            if scr not in screens:
                issues.append(f"[스키마→UI] '{table}' 테이블의 화면 '{scr}'이 UI 파싱에서 누락")

    # ── E. PRD 누락 기능 (스키마/UI에는 있음) ──
    prd_check = {
        "센트": "센트(¢) 보상 시스템",
        "출석": "출석체크",
        "추천 코드": "친구 초대/추천 보상",
        "카드 할인": "카드 할인가",
        "봇": "봇 차단/보안",
        "CAPTCHA": "CAPTCHA",
        "룰렛": "확률형 룰렛",
        "기프티콘": "기프티콘 교환",
    }
    prd_lower = prd.lower()
    for keyword, label in prd_check.items():
        if keyword.lower() not in prd_lower:
            if keyword.lower() in schema.lower() or keyword.lower() in ui.lower():
                issues.append(f"[PRD 누락] '{label}' — 스키마/UI에 있지만 PRD에 '{keyword}' 미언급")

    # PRD에 "이벤트" 있는지 (P3 이벤트/프로모션은 있지만 퀴즈/포인트 이벤트는?)
    if "퀴즈" not in prd and "quiz" not in prd.lower():
        if "퀴즈" in schema or "quiz" in schema.lower():
            warnings.append("[PRD] '퀴즈' — 스키마/UI에 있지만 PRD P0~P3에 명시적 언급 없음")

    # ── F. 기술스택 일관성 ──
    ts = parse_tech_stack_final(tech)
    prd_t = parse_prd_tech(prd)

    info.append(f"[기술] tech-stack: {len(ts)}항목 | PRD: {len(prd_t)}항목")

    # PRD에 보안 항목 없음
    if not any("보안" in k or "CAPTCHA" in k or "봇" in k for k in prd_t):
        if any("CAPTCHA" in k or "봇" in k for k in ts):
            warnings.append("[PRD↔기술] 봇 차단/CAPTCHA가 tech-stack에는 있지만 PRD 기술 인프라에 없음")

    # ── G. v0.1 참조 테이블 상세 컬럼 확인 ──
    v01_only = {"price_alerts", "keyword_alerts", "categories", "user_favorites", "shopping_malls"}
    for t in sorted(v01_only):
        has_detail = t in detail_tables
        if not has_detail:
            info.append(f"[스키마] '{t}' — v0.1 참조로 상세 컬럼 미기재 (의도적)")

    # ── H. MVP 범위 일관성 ──
    mvp_feats, v2_feats = parse_ui_priority(ui)
    info.append(f"[UI 부록A] MVP: {len(mvp_feats)}개 | v2 전용: {len(v2_feats)}개")

    # PRD P0 기능이 UI MVP에 있는지
    for p0_feat in prd_features.get("P0", []):
        found = any(p0_feat[:4] in f for _, f in mvp_feats)
        if not found:
            warnings.append(f"[MVP 범위] PRD P0 '{p0_feat}'이 UI 부록A MVP에 명시적 매칭 없음")

    # ── I. P3 향후 기능 미반영 확인 ──
    p3_future_check = {
        "AI 행동 학습": ("행동 학습", "P3 향후 기능"),
        "조건부 원클릭 구매": ("원클릭", "P3 향후 기능"),
    }
    for feat, (keyword, note) in p3_future_check.items():
        in_s = keyword in schema
        in_u = keyword in ui
        if not in_s and not in_u:
            info.append(f"[{note}] '{feat}' — 스키마/UI 미반영 (P3이므로 정상)")

    # ─────────────────────────────────────────────
    # 3. 출력
    # ─────────────────────────────────────────────
    print("=" * 70)
    print("  PullCents 문서 교차 검증 결과 (v2)")
    print("=" * 70)

    print(f"\n🔴 ISSUE (수정 필요): {len(issues)}건")
    print("-" * 60)
    for i, x in enumerate(issues, 1):
        print(f"  {i:2d}. {x}")

    print(f"\n🟡 WARNING (확인 필요): {len(warnings)}건")
    print("-" * 60)
    for i, x in enumerate(warnings, 1):
        print(f"  {i:2d}. {x}")

    print(f"\n🔵 INFO: {len(info)}건")
    print("-" * 60)
    for i, x in enumerate(info, 1):
        print(f"  {i:2d}. {x}")

    print("\n" + "=" * 70)
    if not issues:
        print("  ✅ 수정 필요 이슈 없음!")
    else:
        print(f"  ⚠️  {len(issues)}개 이슈 + {len(warnings)}개 경고")
    print("=" * 70)

    return len(issues)

if __name__ == "__main__":
    exit(main())
