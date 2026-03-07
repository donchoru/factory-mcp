"""생산 도구 (3개) — 일별 생산, 제품별, 달성률."""

from tools import query, to_json


def register(mcp):
    """mcp 인스턴스에 생산 도구 3개 등록."""

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
        return to_json(query(sql, tuple(params)))

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
        return to_json(query(sql, tuple(params)))

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
        return to_json(query(sql, tuple(params)))
