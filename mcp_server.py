"""Factory AI — MCP 서버 (FastMCP, Streamable HTTP :8501).

15개 MCP 도구: 생산(3) + 불량(4) + 설비(4) + 기타(4)
Open WebUI에서 LLM이 직접 도구를 선택/호출.
"""

import json

from fastmcp import FastMCP
from db.connection import query

mcp = FastMCP("Factory AI")


def _json(rows: list[dict]) -> str:
    """결과를 JSON 문자열로 변환. 100행 초과 시 truncate."""
    if len(rows) > 100:
        rows = rows[:100] + [{"_truncated": f"총 {len(rows)}행 중 100행만 표시"}]
    return json.dumps(rows, ensure_ascii=False)


# ===================== 생산 (3개) =====================


@mcp.tool()
def get_daily_production_summary(
    date_start: str,
    date_end: str,
    line_type: str = "",
) -> str:
    """일별 라인별 생산 현황 조회 — 생산량, 불량수, 불량률.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터 (BODY/PAINT/ASSEMBLY/ENGINE/QC). 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        wo.order_date AS 날짜,
        pline.line_type AS 라인,
        pline.line_name AS 라인명,
        SUM(pl.produced_qty) AS 생산량,
        SUM(pl.defect_qty) AS 불량수,
        ROUND(SUM(pl.defect_qty) * 100.0 / NULLIF(SUM(pl.produced_qty), 0), 2) AS 불량률
    FROM PRODUCTION_LOG pl
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += " GROUP BY wo.order_date, pline.line_type, pline.line_name ORDER BY wo.order_date, pline.line_type"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_production_by_product(
    date_start: str,
    date_end: str,
    product_code: str = "",
    line_type: str = "",
) -> str:
    """제품별 생산량 조회 — 제품코드, 라인, 생산량, 불량률.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        product_code: 제품코드 필터 (DN8/CN7/NX4/GN7/NE1). 빈 문자열이면 전체.
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        p.product_code AS 제품코드,
        p.product_name AS 제품명,
        pline.line_type AS 라인,
        SUM(pl.produced_qty) AS 생산량,
        SUM(pl.defect_qty) AS 불량수,
        ROUND(SUM(pl.defect_qty) * 100.0 / NULLIF(SUM(pl.produced_qty), 0), 2) AS 불량률
    FROM PRODUCTION_LOG pl
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTS p ON wo.product_code = p.product_code
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if product_code:
        sql += " AND p.product_code = ?"
        params.append(product_code.upper())
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += " GROUP BY p.product_code, p.product_name, pline.line_type ORDER BY 생산량 DESC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_achievement_rate(
    date_start: str,
    date_end: str,
    line_type: str = "",
) -> str:
    """라인별 목표 대비 달성률 조회.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        pline.line_type AS 라인,
        pline.line_name AS 라인명,
        SUM(wo.target_qty) AS 목표수량,
        SUM(pl.produced_qty) AS 생산수량,
        ROUND(SUM(pl.produced_qty) * 100.0 / NULLIF(SUM(wo.target_qty), 0), 2) AS 달성률
    FROM PRODUCTION_LOG pl
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += " GROUP BY pline.line_type, pline.line_name ORDER BY 달성률 DESC"
    return _json(query(sql, tuple(params)))


# ===================== 불량 (4개) =====================


@mcp.tool()
def get_defect_summary(
    date_start: str,
    date_end: str,
    line_type: str = "",
    product_code: str = "",
) -> str:
    """라인별 불량 요약 — 생산량, 불량수, 불량률, 불량건수.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
        product_code: 제품코드 필터. 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        pline.line_type AS 라인,
        pline.line_name AS 라인명,
        SUM(pl.produced_qty) AS 생산량,
        SUM(pl.defect_qty) AS 불량수,
        ROUND(SUM(pl.defect_qty) * 100.0 / NULLIF(SUM(pl.produced_qty), 0), 2) AS 불량률,
        COUNT(DISTINCT dr.defect_id) AS 불량건수
    FROM PRODUCTION_LOG pl
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    LEFT JOIN DEFECT_RECORDS dr ON dr.log_id = pl.log_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    if product_code:
        sql += " AND wo.product_code = ?"
        params.append(product_code.upper())
    sql += " GROUP BY pline.line_type, pline.line_name ORDER BY 불량률 DESC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_defect_by_type(
    date_start: str,
    date_end: str,
    line_type: str = "",
) -> str:
    """불량 유형별 집계 — APPEARANCE/DIMENSION/FUNCTION/PAINT/WELD 분류.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        dr.defect_type AS 불량유형,
        dr.severity AS 심각도,
        COUNT(*) AS 건수,
        ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0), 2) AS 비율
    FROM DEFECT_RECORDS dr
    JOIN PRODUCTION_LOG pl ON dr.log_id = pl.log_id
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += " GROUP BY dr.defect_type, dr.severity ORDER BY 건수 DESC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_defect_by_cause(
    date_start: str,
    date_end: str,
    line_type: str = "",
    top_n: int = 10,
) -> str:
    """불량 원인 TOP N — 원인별 건수와 비율.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
        top_n: 상위 N개. 기본 10.
    """
    sql = """
    SELECT
        dr.cause AS 불량원인,
        dr.defect_type AS 불량유형,
        COUNT(*) AS 건수,
        ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0), 2) AS 비율
    FROM DEFECT_RECORDS dr
    JOIN PRODUCTION_LOG pl ON dr.log_id = pl.log_id
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE wo.order_date BETWEEN ? AND ?
      AND dr.cause IS NOT NULL
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += f" GROUP BY dr.cause, dr.defect_type ORDER BY 건수 DESC LIMIT {int(top_n)}"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_defect_trend(
    date_start: str,
    date_end: str,
    group_by: str = "day",
    line_type: str = "",
) -> str:
    """불량률 추이 — 일별/주별/월별 불량률 변화.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        group_by: 그룹 단위 (day/week/month). 기본 day.
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
    """
    if group_by == "week":
        date_expr = "strftime('%Y-W%W', wo.order_date)"
    elif group_by == "month":
        date_expr = "strftime('%Y-%m', wo.order_date)"
    else:
        date_expr = "wo.order_date"

    sql = f"""
    SELECT
        {date_expr} AS 기간,
        SUM(pl.produced_qty) AS 생산량,
        SUM(pl.defect_qty) AS 불량수,
        ROUND(SUM(pl.defect_qty) * 100.0 / NULLIF(SUM(pl.produced_qty), 0), 2) AS 불량률
    FROM PRODUCTION_LOG pl
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += f" GROUP BY {date_expr} ORDER BY 기간"
    return _json(query(sql, tuple(params)))


# ===================== 설비 (4개) =====================


@mcp.tool()
def get_defect_by_equipment(
    date_start: str,
    date_end: str,
    line_type: str = "",
) -> str:
    """설비별 불량 현황 — 어떤 설비에서 불량이 많이 발생하는지.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        e.equip_id AS 설비ID,
        e.equip_name AS 설비명,
        e.equip_type AS 설비유형,
        pline.line_type AS 라인,
        COUNT(*) AS 불량건수,
        GROUP_CONCAT(DISTINCT dr.defect_type) AS 불량유형목록
    FROM DEFECT_RECORDS dr
    JOIN EQUIPMENT e ON dr.equip_id = e.equip_id
    JOIN PRODUCTION_LINES pline ON e.line_id = pline.line_id
    JOIN PRODUCTION_LOG pl ON dr.log_id = pl.log_id
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += " GROUP BY e.equip_id, e.equip_name, e.equip_type, pline.line_type ORDER BY 불량건수 DESC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_equipment_downtime(
    date_start: str,
    date_end: str,
    line_type: str = "",
    reason_code: str = "",
) -> str:
    """설비 비가동 현황 — 사유별 발생횟수와 비가동 시간.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
        reason_code: 사유코드 필터 (BREAKDOWN/MATERIAL/MOLD_CHANGE/PM/EMERGENCY). 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        e.equip_name AS 설비명,
        e.equip_type AS 설비유형,
        pline.line_type AS 라인,
        ed.reason_code AS 사유코드,
        ed.reason_detail AS 사유상세,
        COUNT(*) AS 발생횟수,
        ROUND(SUM(
            (julianday(COALESCE(ed.end_time, datetime('now'))) - julianday(ed.start_time)) * 24
        ), 2) AS 비가동시간_h
    FROM EQUIPMENT_DOWNTIME ed
    JOIN EQUIPMENT e ON ed.equip_id = e.equip_id
    JOIN PRODUCTION_LINES pline ON e.line_id = pline.line_id
    WHERE date(ed.start_time) BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    if reason_code:
        sql += " AND ed.reason_code = ?"
        params.append(reason_code.upper())
    sql += " GROUP BY e.equip_name, e.equip_type, pline.line_type, ed.reason_code, ed.reason_detail ORDER BY 비가동시간_h DESC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_maintenance_history(
    date_start: str = "",
    date_end: str = "",
    equip_id: int = 0,
    top_n: int = 20,
) -> str:
    """설비 정비 이력 조회.

    Args:
        date_start: 시작일 (YYYY-MM-DD). 빈 문자열이면 전체.
        date_end: 종료일 (YYYY-MM-DD). 빈 문자열이면 전체.
        equip_id: 설비 ID. 0이면 전체.
        top_n: 최대 조회 건수. 기본 20.
    """
    sql = """
    SELECT
        mh.maint_date AS 정비일,
        e.equip_name AS 설비명,
        e.equip_type AS 설비유형,
        pline.line_type AS 라인,
        mh.maint_type AS 정비유형,
        mh.description AS 정비내용,
        mh.cost AS 비용
    FROM MAINTENANCE_HISTORY mh
    JOIN EQUIPMENT e ON mh.equip_id = e.equip_id
    JOIN PRODUCTION_LINES pline ON e.line_id = pline.line_id
    WHERE 1=1
    """
    params = []
    if equip_id:
        sql += " AND mh.equip_id = ?"
        params.append(equip_id)
    if date_start:
        sql += " AND mh.maint_date >= ?"
        params.append(date_start)
    if date_end:
        sql += " AND mh.maint_date <= ?"
        params.append(date_end)
    sql += f" ORDER BY mh.maint_date DESC LIMIT {int(top_n)}"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_process_params_anomaly(
    date_start: str,
    date_end: str,
    equip_id: int = 0,
) -> str:
    """공정 파라미터 이상치 조회 — 상한/하한 초과 측정값.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        equip_id: 설비 ID. 0이면 전체.
    """
    sql = """
    SELECT
        e.equip_name AS 설비명,
        pp.param_name AS 파라미터,
        pp.param_value AS 측정값,
        pp.lower_limit AS 하한,
        pp.upper_limit AS 상한,
        CASE
            WHEN pp.param_value > pp.upper_limit THEN '상한초과'
            WHEN pp.param_value < pp.lower_limit THEN '하한미달'
        END AS 이상유형,
        date(pl.start_time) AS 측정일
    FROM PROCESS_PARAMS pp
    JOIN EQUIPMENT e ON pp.equip_id = e.equip_id
    JOIN PRODUCTION_LOG pl ON pp.log_id = pl.log_id
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    WHERE wo.order_date BETWEEN ? AND ?
      AND (pp.param_value > pp.upper_limit OR pp.param_value < pp.lower_limit)
    """
    params = [date_start, date_end]
    if equip_id:
        sql += " AND pp.equip_id = ?"
        params.append(equip_id)
    sql += " ORDER BY 측정일 DESC"
    return _json(query(sql, tuple(params)))


# ===================== 기타 (4개) =====================


@mcp.tool()
def get_quality_inspections(
    date_start: str,
    date_end: str,
    inspection_type: str = "",
    result: str = "",
) -> str:
    """품질 검사 현황 — 검사유형/결과별 집계.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        inspection_type: 검사 유형 (INLINE/FINAL/AUDIT). 빈 문자열이면 전체.
        result: 검사 결과 (PASS/FAIL/CONDITIONAL). 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        qi.inspection_type AS 검사유형,
        qi.result AS 검사결과,
        COUNT(*) AS 건수,
        ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0), 2) AS 비율
    FROM QUALITY_INSPECTIONS qi
    JOIN PRODUCTION_LOG pl ON qi.log_id = pl.log_id
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if inspection_type:
        sql += " AND qi.inspection_type = ?"
        params.append(inspection_type.upper())
    if result:
        sql += " AND qi.result = ?"
        params.append(result.upper())
    sql += " GROUP BY qi.inspection_type, qi.result ORDER BY 건수 DESC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_material_yield(
    date_start: str,
    date_end: str,
    product_code: str = "",
) -> str:
    """자재 수율 — 계획 대비 실투입 비율.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        product_code: 제품코드 필터. 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        mu.material_code AS 자재코드,
        mu.material_name AS 자재명,
        p.product_name AS 제품명,
        SUM(mu.planned_qty) AS 계획수량,
        SUM(mu.actual_qty) AS 실투입,
        ROUND(SUM(mu.planned_qty) * 100.0 / NULLIF(SUM(mu.actual_qty), 0), 2) AS 수율
    FROM MATERIAL_USAGE mu
    JOIN WORK_ORDERS wo ON mu.wo_id = wo.wo_id
    JOIN PRODUCTS p ON wo.product_code = p.product_code
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if product_code:
        sql += " AND p.product_code = ?"
        params.append(product_code.upper())
    sql += " GROUP BY mu.material_code, mu.material_name, p.product_name ORDER BY 수율 ASC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_worker_performance(
    date_start: str,
    date_end: str,
    line_type: str = "",
) -> str:
    """작업자별 실적 — 생산량, 불량수, 불량률, 작업건수.

    Args:
        date_start: 시작일 (YYYY-MM-DD)
        date_end: 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
    """
    sql = """
    SELECT
        w.worker_name AS 작업자,
        w.skill_level AS 숙련도,
        pline.line_type AS 라인,
        SUM(pl.produced_qty) AS 생산량,
        SUM(pl.defect_qty) AS 불량수,
        ROUND(SUM(pl.defect_qty) * 100.0 / NULLIF(SUM(pl.produced_qty), 0), 2) AS 불량률,
        COUNT(DISTINCT wo.wo_id) AS 작업건수
    FROM PRODUCTION_LOG pl
    JOIN WORKERS w ON pl.worker_id = w.worker_id
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE wo.order_date BETWEEN ? AND ?
    """
    params = [date_start, date_end]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += " GROUP BY w.worker_name, w.skill_level, pline.line_type ORDER BY 생산량 DESC"
    return _json(query(sql, tuple(params)))


@mcp.tool()
def get_period_comparison(
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
    line_type: str = "",
) -> str:
    """두 기간 비교 — 라인별 생산량과 불량률 변화.

    Args:
        period_a_start: A기간 시작일 (YYYY-MM-DD)
        period_a_end: A기간 종료일 (YYYY-MM-DD)
        period_b_start: B기간 시작일 (YYYY-MM-DD)
        period_b_end: B기간 종료일 (YYYY-MM-DD)
        line_type: 라인 타입 필터. 빈 문자열이면 전체.
    """
    # period_comparison은 CASE WHEN으로 기간을 나누므로 파라미터를 여러 번 사용
    sql = """
    SELECT
        pline.line_type AS 라인,
        pline.line_name AS 라인명,
        SUM(CASE WHEN wo.order_date BETWEEN ? AND ? THEN pl.produced_qty ELSE 0 END) AS A기간_생산량,
        SUM(CASE WHEN wo.order_date BETWEEN ? AND ? THEN pl.produced_qty ELSE 0 END) AS B기간_생산량,
        ROUND(SUM(CASE WHEN wo.order_date BETWEEN ? AND ? THEN pl.defect_qty ELSE 0 END) * 100.0
            / NULLIF(SUM(CASE WHEN wo.order_date BETWEEN ? AND ? THEN pl.produced_qty ELSE 0 END), 0), 2) AS A기간_불량률,
        ROUND(SUM(CASE WHEN wo.order_date BETWEEN ? AND ? THEN pl.defect_qty ELSE 0 END) * 100.0
            / NULLIF(SUM(CASE WHEN wo.order_date BETWEEN ? AND ? THEN pl.produced_qty ELSE 0 END), 0), 2) AS B기간_불량률
    FROM PRODUCTION_LOG pl
    JOIN WORK_ORDERS wo ON pl.wo_id = wo.wo_id
    JOIN PRODUCTION_LINES pline ON wo.line_id = pline.line_id
    WHERE (wo.order_date BETWEEN ? AND ? OR wo.order_date BETWEEN ? AND ?)
    """
    params = [
        period_a_start, period_a_end,  # A 생산량
        period_b_start, period_b_end,  # B 생산량
        period_a_start, period_a_end,  # A 불량
        period_a_start, period_a_end,  # A 생산(분모)
        period_b_start, period_b_end,  # B 불량
        period_b_start, period_b_end,  # B 생산(분모)
        period_a_start, period_a_end,  # WHERE A
        period_b_start, period_b_end,  # WHERE B
    ]
    if line_type:
        sql += " AND pline.line_type = ?"
        params.append(line_type.upper())
    sql += " GROUP BY pline.line_type, pline.line_name ORDER BY pline.line_type"
    return _json(query(sql, tuple(params)))


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8501)
