"""60일치 자동차 생산 시뮬레이션 데이터 생성.

기간: 2026-01-05 ~ 2026-03-05
핵심 시나리오: 도장 라인 2주차부터 불량률 급등 (스프레이건 노즐 마모)
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "factory.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# ===== 마스터 데이터 =====

LINES = [
    (1, "차체1라인", "BODY", 30),
    (2, "도장1라인", "PAINT", 25),
    (3, "조립1라인", "ASSEMBLY", 20),
    (4, "엔진1라인", "ENGINE", 35),
    (5, "검사1라인", "QC", 40),
]

PRODUCTS = [
    ("DN8", "소나타", "소나타 DN8", "SEDAN", 55.0),
    ("CN7", "아반떼", "아반떼 CN7", "SEDAN", 50.0),
    ("NX4", "투싼", "투싼 NX4", "SUV", 65.0),
    ("GN7", "그랜저", "그랜저 GN7", "SEDAN", 70.0),
    ("NE1", "아이오닉5", "아이오닉5 NE1", "EV", 75.0),
]

EQUIPMENT_DATA = [
    (1, "차체 용접로봇 A", "ROBOT", 1),
    (2, "차체 용접로봇 B", "ROBOT", 1),
    (3, "차체 프레스 1호", "PRESS", 1),
    (4, "차체 컨베이어", "CONVEYOR", 1),
    (5, "도장 스프레이건 A", "SPRAY", 2),
    (6, "도장 스프레이건 B", "SPRAY", 2),
    (7, "도장 건조로", "CONVEYOR", 2),
    (8, "도장 로봇", "ROBOT", 2),
    (9, "조립 로봇 A", "ROBOT", 3),
    (10, "조립 로봇 B", "ROBOT", 3),
    (11, "조립 컨베이어", "CONVEYOR", 3),
    (12, "체결 토크건", "ROBOT", 3),
    (13, "엔진 가공기 1호", "PRESS", 4),
    (14, "엔진 가공기 2호", "PRESS", 4),
    (15, "엔진 조립로봇", "ROBOT", 4),
    (16, "엔진 테스트기", "TESTER", 4),
    (17, "외관검사기", "TESTER", 5),
    (18, "기능검사기", "TESTER", 5),
    (19, "누수검사기", "TESTER", 5),
    (20, "최종검사 로봇", "ROBOT", 5),
]

SHIFTS_DATA = [
    (1, "주간", "06:00", "14:00"),
    (2, "야간", "14:00", "22:00"),
    (3, "잔업", "22:00", "06:00"),
]

WORKER_NAMES = [
    "김철수", "이영희", "박민수", "정수진", "최동욱",
    "한지은", "유재석", "강호동", "송혜교", "조인성",
    "이민호", "김태희", "박서준", "전지현", "이준기",
    "윤아", "차은우", "수지", "공유", "손예진",
    "김수현", "한효주", "이병헌", "전도연", "황정민",
    "마동석", "이정재", "임시완", "박보검", "김고은",
]

DEPARTMENTS = ["생산1팀", "생산2팀", "품질관리팀", "설비보전팀", "공정관리팀"]
SKILL_LEVELS = ["JUNIOR", "MIDDLE", "SENIOR"]

DEFECT_TYPES = {
    "APPEARANCE": ["APP-001", "APP-002", "APP-003"],
    "DIMENSION": ["DIM-001", "DIM-002"],
    "FUNCTION": ["FUN-001", "FUN-002"],
    "PAINT": ["PNT-001", "PNT-002", "PNT-003"],
    "WELD": ["WLD-001", "WLD-002"],
}

DEFECT_CAUSES = {
    "PAINT": ["스프레이건 노즐 마모", "도료 점도 불량", "건조로 온도 이탈", "먼지 유입", "도막 두께 불균일"],
    "WELD": ["용접 전류 이상", "전극 마모", "정렬 불량"],
    "APPEARANCE": ["스크래치", "덴트", "이물질 부착"],
    "DIMENSION": ["금형 마모", "클램핑 불량"],
    "FUNCTION": ["체결 토크 미달", "배선 불량"],
}

DOWNTIME_REASONS = {
    "BREAKDOWN": "설비 고장",
    "MATERIAL": "자재 부족",
    "MOLD_CHANGE": "금형 교체",
    "PM": "정기 보전",
    "EMERGENCY": "긴급 수리",
}

MATERIAL_MAP = {
    "DN8": [("STL-001", "냉연강판", "SHEET"), ("PNT-A01", "메탈릭 실버", "L")],
    "CN7": [("STL-002", "열연강판", "SHEET"), ("PNT-A02", "팬텀 블랙", "L")],
    "NX4": [("STL-003", "고장력강판", "SHEET"), ("PNT-A03", "아마존 그레이", "L")],
    "GN7": [("STL-001", "냉연강판", "SHEET"), ("PNT-A04", "문라이트 블루", "L")],
    "NE1": [("ALU-001", "알루미늄판", "SHEET"), ("PNT-A05", "디지털 그린", "L")],
}


def seed():
    """DB 초기화 + 60일 시드 데이터 생성."""
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"기존 DB 삭제: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")

    # 스키마 실행
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    print("스키마 생성 완료 (14 테이블)")

    c = conn.cursor()

    # 작업자 30명 INSERT
    for i, name in enumerate(WORKER_NAMES):
        line_id = (i % 5) + 1
        dept = DEPARTMENTS[i % 5]
        skill = SKILL_LEVELS[i % 3]
        c.execute(
            "INSERT INTO WORKERS VALUES (?,?,?,?,?)",
            (i + 1, name, dept, skill, line_id),
        )

    # ===== 60일치 트랜잭션 데이터 =====
    base_date = datetime(2026, 1, 5)
    wo_id = 1
    log_id = 1
    defect_id = 1
    downtime_id = 1
    inspection_id = 1
    param_id = 1
    usage_id = 1
    maint_id = 1
    summary_id = 1

    print("데이터 생성 중...")

    for day_offset in range(60):
        current_date = base_date + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        week_num = day_offset // 7

        for line_id, line_name, line_type, capacity in LINES:
            daily_produced = 0
            daily_defect = 0
            daily_operating = 0.0
            daily_downtime = 0.0

            for shift_id in [1, 2]:  # 주간, 야간
                product = random.choice(PRODUCTS)
                product_code = product[0]
                target_qty = random.randint(int(capacity * 6), int(capacity * 8))

                c.execute(
                    "INSERT INTO WORK_ORDERS VALUES (?,?,?,?,?,?)",
                    (wo_id, product_code, target_qty, line_id, shift_id, date_str),
                )

                # 자재 사용
                for mat_code, mat_name, mat_unit in MATERIAL_MAP.get(product_code, []):
                    planned = target_qty * random.uniform(1.0, 1.1)
                    actual = planned * random.uniform(0.95, 1.08)
                    c.execute(
                        "INSERT INTO MATERIAL_USAGE VALUES (?,?,?,?,?,?,?)",
                        (usage_id, wo_id, mat_code, mat_name, round(planned, 1), round(actual, 1), mat_unit),
                    )
                    usage_id += 1

                # 생산 실적 (교대당 2~3 로그)
                logs_per_shift = random.randint(2, 3)
                shift_start = current_date.replace(hour=6 if shift_id == 1 else 14)

                for log_idx in range(logs_per_shift):
                    # 해당 라인 작업자 선택
                    line_workers = [w + 1 for w in range(30) if (w % 5) + 1 == line_id]
                    worker_id = random.choice(line_workers) if line_workers else random.randint(1, 30)

                    produced = random.randint(
                        int(target_qty / logs_per_shift * 0.8),
                        int(target_qty / logs_per_shift * 1.1),
                    )

                    # ★ 도장 라인 2주차부터 불량률 급등 (데모 시나리오)
                    if line_type == "PAINT" and week_num >= 2:
                        defect_rate = random.uniform(0.03, 0.08)
                    elif line_type == "PAINT":
                        defect_rate = random.uniform(0.005, 0.02)
                    else:
                        defect_rate = random.uniform(0.005, 0.025)

                    defect_qty = max(0, int(produced * defect_rate))
                    start = shift_start + timedelta(hours=log_idx * 2.5)
                    end = start + timedelta(hours=random.uniform(2.0, 2.5))

                    c.execute(
                        "INSERT INTO PRODUCTION_LOG VALUES (?,?,?,?,?,?,?)",
                        (
                            log_id, wo_id, produced, defect_qty,
                            start.strftime("%Y-%m-%d %H:%M"),
                            end.strftime("%Y-%m-%d %H:%M"),
                            worker_id,
                        ),
                    )

                    daily_produced += produced
                    daily_defect += defect_qty
                    daily_operating += (end - start).total_seconds() / 3600

                    # 불량 상세
                    line_equips = [e[0] for e in EQUIPMENT_DATA if e[3] == line_id]
                    for _ in range(defect_qty):
                        if line_type == "PAINT":
                            dt = "PAINT"
                        elif line_type == "BODY":
                            dt = random.choice(["WELD", "APPEARANCE", "DIMENSION"])
                        else:
                            dt = random.choice(list(DEFECT_TYPES.keys()))

                        dc = random.choice(DEFECT_TYPES[dt])
                        severity = random.choices(
                            ["MINOR", "MAJOR", "CRITICAL"], weights=[60, 30, 10]
                        )[0]
                        cause = random.choice(DEFECT_CAUSES[dt])

                        # 도장 2주차 이후 노즐 마모 원인 60% 확률
                        if line_type == "PAINT" and week_num >= 2 and random.random() < 0.6:
                            cause = "스프레이건 노즐 마모"

                        c.execute(
                            "INSERT INTO DEFECT_RECORDS VALUES (?,?,?,?,?,?,?,?)",
                            (
                                defect_id, log_id,
                                random.choice(line_equips),
                                dt, dc, severity, cause,
                                (start + timedelta(minutes=random.randint(10, 140))).strftime("%Y-%m-%d %H:%M"),
                            ),
                        )
                        defect_id += 1

                    # 공정 파라미터
                    for equip_id_param in line_equips[:2]:
                        params = [
                            ("TEMPERATURE", 60.0, 55.0, 65.0),
                            ("PRESSURE", 5.0, 4.0, 6.0),
                            ("SPEED", 100.0, 80.0, 120.0),
                        ]
                        for pname, base_val, lower, upper in params:
                            if line_type == "PAINT" and pname == "TEMPERATURE" and week_num >= 2:
                                val = base_val + random.uniform(-8, 12)
                            else:
                                val = base_val + random.uniform(-3, 3)
                            c.execute(
                                "INSERT INTO PROCESS_PARAMS VALUES (?,?,?,?,?,?,?)",
                                (param_id, log_id, equip_id_param, pname, round(val, 1), upper, lower),
                            )
                            param_id += 1

                    # 품질 검사
                    inspector_id = random.randint(1, 30)
                    insp_type = random.choice(["INLINE", "FINAL", "AUDIT"])
                    result = "PASS" if defect_qty == 0 else random.choices(
                        ["PASS", "FAIL", "CONDITIONAL"], weights=[40, 40, 20]
                    )[0]
                    c.execute(
                        "INSERT INTO QUALITY_INSPECTIONS VALUES (?,?,?,?,?,?)",
                        (inspection_id, log_id, inspector_id, insp_type, result, None),
                    )
                    inspection_id += 1

                    log_id += 1

                wo_id += 1

            # 설비 비가동 (하루 30% 확률)
            if random.random() < 0.3:
                line_equips = [e[0] for e in EQUIPMENT_DATA if e[3] == line_id]
                equip = random.choice(line_equips)
                reason = random.choice(list(DOWNTIME_REASONS.keys()))
                dt_start = current_date.replace(hour=random.randint(6, 20))
                duration = random.uniform(0.5, 3.0)
                dt_end = dt_start + timedelta(hours=duration)
                daily_downtime += duration

                c.execute(
                    "INSERT INTO EQUIPMENT_DOWNTIME VALUES (?,?,?,?,?,?,?)",
                    (
                        downtime_id, equip, reason,
                        DOWNTIME_REASONS[reason],
                        dt_start.strftime("%Y-%m-%d %H:%M"),
                        dt_end.strftime("%Y-%m-%d %H:%M"),
                        random.randint(1, 30),
                    ),
                )
                downtime_id += 1

            # 정비 이력 (3~5일마다)
            if day_offset % random.randint(3, 5) == 0:
                line_equips = [e[0] for e in EQUIPMENT_DATA if e[3] == line_id]
                equip = random.choice(line_equips)
                maint_type = random.choice(["PREVENTIVE", "CORRECTIVE", "EMERGENCY"])
                descs = {
                    "PREVENTIVE": "정기 점검 및 윤활",
                    "CORRECTIVE": "부품 교체 수리",
                    "EMERGENCY": "긴급 고장 수리",
                }
                cost = random.uniform(50000, 500000)
                c.execute(
                    "INSERT INTO MAINTENANCE_HISTORY VALUES (?,?,?,?,?,?,?)",
                    (maint_id, equip, maint_type, descs[maint_type], round(cost), date_str, random.randint(1, 30)),
                )
                maint_id += 1

            # 일별 요약
            c.execute(
                "INSERT INTO DAILY_PRODUCTION_SUMMARY VALUES (?,?,?,?,?,?,?)",
                (
                    summary_id, line_id, date_str,
                    daily_produced, daily_defect,
                    round(daily_operating, 1), round(daily_downtime, 1),
                ),
            )
            summary_id += 1

    conn.commit()

    # 검증
    print("\n검증:")
    tables = [
        "PRODUCTION_LINES", "PRODUCTS", "EQUIPMENT", "WORKERS", "SHIFTS",
        "WORK_ORDERS", "PRODUCTION_LOG", "DEFECT_RECORDS",
        "EQUIPMENT_DOWNTIME", "QUALITY_INSPECTIONS",
        "PROCESS_PARAMS", "MATERIAL_USAGE", "MAINTENANCE_HISTORY",
        "DAILY_PRODUCTION_SUMMARY",
    ]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count}행")

    conn.close()

    print(f"\nDB 생성 완료: {DB_PATH}")
    print(f"기간: {base_date.strftime('%Y-%m-%d')} ~ {(base_date + timedelta(days=59)).strftime('%Y-%m-%d')}")
    print(f"작업지시: {wo_id - 1}건 | 생산실적: {log_id - 1}건 | 불량: {defect_id - 1}건")
    print(f"비가동: {downtime_id - 1}건 | 정비: {maint_id - 1}건")


if __name__ == "__main__":
    seed()
