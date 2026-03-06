-- Factory AI — Oracle 스키마 (참고용)
-- SQLite schema.sql을 Oracle 문법으로 변환

CREATE TABLE production_lines (
    line_id       VARCHAR2(20) PRIMARY KEY,
    line_name     VARCHAR2(100) NOT NULL,
    vehicle_type  VARCHAR2(50) NOT NULL,
    capacity_per_shift NUMBER NOT NULL,
    status        VARCHAR2(20) DEFAULT 'ACTIVE'
);

INSERT INTO production_lines VALUES ('LINE-1', '1라인 (세단)', 'SEDAN', 120, 'ACTIVE');
INSERT INTO production_lines VALUES ('LINE-2', '2라인 (SUV)', 'SUV', 80, 'ACTIVE');
INSERT INTO production_lines VALUES ('LINE-3', '3라인 (EV)', 'EV', 60, 'ACTIVE');

CREATE TABLE models (
    model_id          VARCHAR2(20) PRIMARY KEY,
    model_name        VARCHAR2(100) NOT NULL,
    line_id           VARCHAR2(20) NOT NULL REFERENCES production_lines(line_id),
    target_per_shift  NUMBER NOT NULL
);

INSERT INTO models VALUES ('SONATA', '소나타', 'LINE-1', 120);
INSERT INTO models VALUES ('TUCSON', '투싼', 'LINE-2', 45);
INSERT INTO models VALUES ('GV70', 'GV70', 'LINE-2', 35);
INSERT INTO models VALUES ('IONIQ6', '아이오닉6', 'LINE-3', 60);

CREATE TABLE shifts (
    shift_id    VARCHAR2(20) PRIMARY KEY,
    shift_name  VARCHAR2(50) NOT NULL,
    start_time  VARCHAR2(10) NOT NULL,
    end_time    VARCHAR2(10) NOT NULL
);

INSERT INTO shifts VALUES ('DAY', '주간', '06:00', '14:00');
INSERT INTO shifts VALUES ('NIGHT', '야간', '14:00', '22:00');
INSERT INTO shifts VALUES ('MIDNIGHT', '심야', '22:00', '06:00');

CREATE SEQUENCE daily_production_seq START WITH 1;
CREATE TABLE daily_production (
    id                NUMBER DEFAULT daily_production_seq.NEXTVAL PRIMARY KEY,
    production_date   VARCHAR2(10) NOT NULL,
    line_id           VARCHAR2(20) NOT NULL REFERENCES production_lines(line_id),
    model_id          VARCHAR2(20) NOT NULL REFERENCES models(model_id),
    shift_id          VARCHAR2(20) NOT NULL REFERENCES shifts(shift_id),
    planned_qty       NUMBER NOT NULL,
    actual_qty        NUMBER NOT NULL,
    defect_qty        NUMBER DEFAULT 0,
    achievement_rate  NUMBER,
    note              VARCHAR2(500)
);

CREATE INDEX idx_prod_date ON daily_production(production_date);
CREATE INDEX idx_prod_line ON daily_production(line_id);
CREATE INDEX idx_prod_model ON daily_production(model_id);

CREATE SEQUENCE defects_seq START WITH 1;
CREATE TABLE defects (
    id                NUMBER DEFAULT defects_seq.NEXTVAL PRIMARY KEY,
    production_date   VARCHAR2(10) NOT NULL,
    line_id           VARCHAR2(20) NOT NULL REFERENCES production_lines(line_id),
    model_id          VARCHAR2(20) NOT NULL REFERENCES models(model_id),
    shift_id          VARCHAR2(20) NOT NULL REFERENCES shifts(shift_id),
    defect_type       VARCHAR2(50) NOT NULL,
    defect_count      NUMBER NOT NULL,
    description       VARCHAR2(500)
);

CREATE INDEX idx_defect_date ON defects(production_date);
CREATE INDEX idx_defect_line ON defects(line_id);

CREATE SEQUENCE downtime_seq START WITH 1;
CREATE TABLE downtime (
    id                NUMBER DEFAULT downtime_seq.NEXTVAL PRIMARY KEY,
    line_id           VARCHAR2(20) NOT NULL REFERENCES production_lines(line_id),
    start_datetime    VARCHAR2(20) NOT NULL,
    end_datetime      VARCHAR2(20) NOT NULL,
    duration_minutes  NUMBER NOT NULL,
    reason_type       VARCHAR2(50) NOT NULL,
    description       VARCHAR2(500)
);

CREATE INDEX idx_downtime_line ON downtime(line_id);

COMMIT;
