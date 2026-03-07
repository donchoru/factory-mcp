"""불량 도구 (4개) — 불량 요약, 유형별, 원인별, 추이."""

from tools import query, to_json, log_call


def register(mcp):
    """mcp 인스턴스에 불량 도구 4개 등록."""

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
        log_call("get_defect_summary", date_start=date_start, date_end=date_end, line_type=line_type, product_code=product_code)
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
        return to_json(query(sql, tuple(params)))

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
        return to_json(query(sql, tuple(params)))

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
        return to_json(query(sql, tuple(params)))

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
        return to_json(query(sql, tuple(params)))
