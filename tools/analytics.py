"""분석 도구 (4개) — 품질검사, 자재수율, 작업자실적, 기간비교."""

from tools import query, to_json


def register(mcp):
    """mcp 인스턴스에 분석 도구 4개 등록."""

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
        return to_json(query(sql, tuple(params)))

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
        return to_json(query(sql, tuple(params)))

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
        return to_json(query(sql, tuple(params)))

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
            period_a_start, period_a_end,
            period_b_start, period_b_end,
            period_a_start, period_a_end,
            period_a_start, period_a_end,
            period_b_start, period_b_end,
            period_b_start, period_b_end,
            period_a_start, period_a_end,
            period_b_start, period_b_end,
        ]
        if line_type:
            sql += " AND pline.line_type = ?"
            params.append(line_type.upper())
        sql += " GROUP BY pline.line_type, pline.line_name ORDER BY pline.line_type"
        return to_json(query(sql, tuple(params)))
