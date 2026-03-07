-- Factory AI — 자동차 공장 MES 스키마 (14 테이블)

PRAGMA foreign_keys = ON;

-- ========== 마스터 테이블 (5) ==========

CREATE TABLE IF NOT EXISTS PRODUCTION_LINES (
    line_id       INTEGER PRIMARY KEY,
    line_name     TEXT NOT NULL,
    line_type     TEXT NOT NULL,          -- BODY / PAINT / ASSEMBLY / ENGINE / QC
    capacity_per_hour INTEGER DEFAULT 30
);

INSERT INTO PRODUCTION_LINES VALUES (1, '차체1라인', 'BODY', 30);
INSERT INTO PRODUCTION_LINES VALUES (2, '도장1라인', 'PAINT', 25);
INSERT INTO PRODUCTION_LINES VALUES (3, '조립1라인', 'ASSEMBLY', 20);
INSERT INTO PRODUCTION_LINES VALUES (4, '엔진1라인', 'ENGINE', 35);
INSERT INTO PRODUCTION_LINES VALUES (5, '검사1라인', 'QC', 40);

CREATE TABLE IF NOT EXISTS PRODUCTS (
    product_code  TEXT PRIMARY KEY,       -- DN8 / CN7 / NX4 / GN7 / NE1
    product_name  TEXT NOT NULL,          -- 소나타 / 아반떼 / 투싼 / 그랜저 / 아이오닉5
    model         TEXT NOT NULL,
    category      TEXT DEFAULT 'SEDAN',   -- SEDAN / SUV / EV
    cycle_time    REAL DEFAULT 60.0
);

INSERT INTO PRODUCTS VALUES ('DN8', '소나타', '소나타 DN8', 'SEDAN', 55.0);
INSERT INTO PRODUCTS VALUES ('CN7', '아반떼', '아반떼 CN7', 'SEDAN', 50.0);
INSERT INTO PRODUCTS VALUES ('NX4', '투싼', '투싼 NX4', 'SUV', 65.0);
INSERT INTO PRODUCTS VALUES ('GN7', '그랜저', '그랜저 GN7', 'SEDAN', 70.0);
INSERT INTO PRODUCTS VALUES ('NE1', '아이오닉5', '아이오닉5 NE1', 'EV', 75.0);

CREATE TABLE IF NOT EXISTS EQUIPMENT (
    equip_id      INTEGER PRIMARY KEY,
    equip_name    TEXT NOT NULL,
    equip_type    TEXT NOT NULL,          -- ROBOT / PRESS / SPRAY / CONVEYOR / TESTER
    line_id       INTEGER REFERENCES PRODUCTION_LINES(line_id),
    install_date  TEXT,
    status        TEXT DEFAULT 'RUNNING'  -- RUNNING / STOPPED / MAINTENANCE
);

INSERT INTO EQUIPMENT VALUES (1,  '차체 용접로봇 A',   'ROBOT',    1, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (2,  '차체 용접로봇 B',   'ROBOT',    1, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (3,  '차체 프레스 1호',   'PRESS',    1, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (4,  '차체 컨베이어',     'CONVEYOR', 1, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (5,  '도장 스프레이건 A', 'SPRAY',    2, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (6,  '도장 스프레이건 B', 'SPRAY',    2, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (7,  '도장 건조로',       'CONVEYOR', 2, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (8,  '도장 로봇',         'ROBOT',    2, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (9,  '조립 로봇 A',       'ROBOT',    3, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (10, '조립 로봇 B',       'ROBOT',    3, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (11, '조립 컨베이어',     'CONVEYOR', 3, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (12, '체결 토크건',       'ROBOT',    3, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (13, '엔진 가공기 1호',   'PRESS',    4, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (14, '엔진 가공기 2호',   'PRESS',    4, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (15, '엔진 조립로봇',     'ROBOT',    4, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (16, '엔진 테스트기',     'TESTER',   4, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (17, '외관검사기',         'TESTER',   5, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (18, '기능검사기',         'TESTER',   5, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (19, '누수검사기',         'TESTER',   5, '2023-01-15', 'RUNNING');
INSERT INTO EQUIPMENT VALUES (20, '최종검사 로봇',     'ROBOT',    5, '2023-01-15', 'RUNNING');

CREATE TABLE IF NOT EXISTS WORKERS (
    worker_id     INTEGER PRIMARY KEY,
    worker_name   TEXT NOT NULL,
    department    TEXT,
    skill_level   TEXT DEFAULT 'MIDDLE',  -- JUNIOR / MIDDLE / SENIOR
    line_id       INTEGER REFERENCES PRODUCTION_LINES(line_id)
);

-- 30명 작업자는 seed.py에서 INSERT

CREATE TABLE IF NOT EXISTS SHIFTS (
    shift_id      INTEGER PRIMARY KEY,
    shift_name    TEXT NOT NULL,          -- 주간 / 야간 / 잔업
    start_time    TEXT NOT NULL,
    end_time      TEXT NOT NULL
);

INSERT INTO SHIFTS VALUES (1, '주간', '06:00', '14:00');
INSERT INTO SHIFTS VALUES (2, '야간', '14:00', '22:00');
INSERT INTO SHIFTS VALUES (3, '잔업', '22:00', '06:00');

-- ========== 트랜잭션 테이블 (5) ==========

CREATE TABLE IF NOT EXISTS WORK_ORDERS (
    wo_id         INTEGER PRIMARY KEY,
    product_code  TEXT REFERENCES PRODUCTS(product_code),
    target_qty    INTEGER NOT NULL,
    line_id       INTEGER REFERENCES PRODUCTION_LINES(line_id),
    shift_id      INTEGER REFERENCES SHIFTS(shift_id),
    order_date    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS PRODUCTION_LOG (
    log_id        INTEGER PRIMARY KEY,
    wo_id         INTEGER REFERENCES WORK_ORDERS(wo_id),
    produced_qty  INTEGER NOT NULL,
    defect_qty    INTEGER DEFAULT 0,
    start_time    TEXT NOT NULL,
    end_time      TEXT,
    worker_id     INTEGER REFERENCES WORKERS(worker_id)
);

CREATE TABLE IF NOT EXISTS DEFECT_RECORDS (
    defect_id     INTEGER PRIMARY KEY,
    log_id        INTEGER REFERENCES PRODUCTION_LOG(log_id),
    equip_id      INTEGER REFERENCES EQUIPMENT(equip_id),
    defect_type   TEXT NOT NULL,          -- APPEARANCE / DIMENSION / FUNCTION / PAINT / WELD
    defect_code   TEXT NOT NULL,
    severity      TEXT DEFAULT 'MINOR',   -- MINOR / MAJOR / CRITICAL
    cause         TEXT,
    detected_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS EQUIPMENT_DOWNTIME (
    downtime_id       INTEGER PRIMARY KEY,
    equip_id          INTEGER REFERENCES EQUIPMENT(equip_id),
    reason_code       TEXT NOT NULL,      -- BREAKDOWN / MATERIAL / MOLD_CHANGE / PM / EMERGENCY
    reason_detail     TEXT,
    start_time        TEXT NOT NULL,
    end_time          TEXT,
    repair_worker_id  INTEGER REFERENCES WORKERS(worker_id)
);

CREATE TABLE IF NOT EXISTS QUALITY_INSPECTIONS (
    inspection_id     INTEGER PRIMARY KEY,
    log_id            INTEGER REFERENCES PRODUCTION_LOG(log_id),
    inspector_id      INTEGER REFERENCES WORKERS(worker_id),
    inspection_type   TEXT NOT NULL,      -- INLINE / FINAL / AUDIT
    result            TEXT NOT NULL,      -- PASS / FAIL / CONDITIONAL
    details           TEXT
);

-- ========== 분석 테이블 (4) ==========

CREATE TABLE IF NOT EXISTS PROCESS_PARAMS (
    param_id      INTEGER PRIMARY KEY,
    log_id        INTEGER REFERENCES PRODUCTION_LOG(log_id),
    equip_id      INTEGER REFERENCES EQUIPMENT(equip_id),
    param_name    TEXT NOT NULL,          -- TEMPERATURE / PRESSURE / SPEED
    param_value   REAL NOT NULL,
    upper_limit   REAL,
    lower_limit   REAL
);

CREATE TABLE IF NOT EXISTS MATERIAL_USAGE (
    usage_id      INTEGER PRIMARY KEY,
    wo_id         INTEGER REFERENCES WORK_ORDERS(wo_id),
    material_code TEXT NOT NULL,
    material_name TEXT NOT NULL,
    planned_qty   REAL NOT NULL,
    actual_qty    REAL NOT NULL,
    unit          TEXT DEFAULT 'EA'
);

CREATE TABLE IF NOT EXISTS MAINTENANCE_HISTORY (
    maint_id      INTEGER PRIMARY KEY,
    equip_id      INTEGER REFERENCES EQUIPMENT(equip_id),
    maint_type    TEXT NOT NULL,          -- PREVENTIVE / CORRECTIVE / EMERGENCY
    description   TEXT,
    cost          REAL DEFAULT 0,
    maint_date    TEXT NOT NULL,
    technician_id INTEGER REFERENCES WORKERS(worker_id)
);

CREATE TABLE IF NOT EXISTS DAILY_PRODUCTION_SUMMARY (
    summary_id       INTEGER PRIMARY KEY,
    line_id          INTEGER REFERENCES PRODUCTION_LINES(line_id),
    production_date  TEXT NOT NULL,
    total_produced   INTEGER DEFAULT 0,
    total_defect     INTEGER DEFAULT 0,
    operating_hours  REAL DEFAULT 0,
    downtime_hours   REAL DEFAULT 0
);

-- ========== 인덱스 ==========

CREATE INDEX IF NOT EXISTS idx_wo_date ON WORK_ORDERS(order_date);
CREATE INDEX IF NOT EXISTS idx_wo_line ON WORK_ORDERS(line_id);
CREATE INDEX IF NOT EXISTS idx_log_wo ON PRODUCTION_LOG(wo_id);
CREATE INDEX IF NOT EXISTS idx_defect_log ON DEFECT_RECORDS(log_id);
CREATE INDEX IF NOT EXISTS idx_defect_type ON DEFECT_RECORDS(defect_type);
CREATE INDEX IF NOT EXISTS idx_downtime_equip ON EQUIPMENT_DOWNTIME(equip_id);
CREATE INDEX IF NOT EXISTS idx_params_log ON PROCESS_PARAMS(log_id);
CREATE INDEX IF NOT EXISTS idx_material_wo ON MATERIAL_USAGE(wo_id);
CREATE INDEX IF NOT EXISTS idx_maint_equip ON MAINTENANCE_HISTORY(equip_id);
CREATE INDEX IF NOT EXISTS idx_summary_date ON DAILY_PRODUCTION_SUMMARY(production_date);
CREATE INDEX IF NOT EXISTS idx_summary_line ON DAILY_PRODUCTION_SUMMARY(line_id);
